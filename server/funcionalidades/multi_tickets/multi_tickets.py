import html
import aiohttp
import discord
import chat_exporter
import io
import re
from discord import ui, ButtonStyle, Embed
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import os
import json
from . import config as module_config
from config import config as global_config

# --- Funções de Contagem e Agendamento ---
def load_ticket_count(file_path: str, initial_number: int) -> int:
    try:
        with open(file_path, 'r') as f: return int(f.read().strip())
    except (FileNotFoundError, ValueError): return initial_number

def save_ticket_count(file_path: str, count: int):
    with open(file_path, 'w') as f: f.write(str(count))

def load_schedule():
    try:
        file_path = os.path.join(os.path.dirname(__file__), module_config.ARQUIVO_AGENDAMENTO)
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_schedule(data):
    file_path = os.path.join(os.path.dirname(__file__), module_config.ARQUIVO_AGENDAMENTO)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

async def _close_ticket_logic(interaction: discord.Interaction):
    channel = interaction.channel
    category_config = TicketActionsView()._get_category_config_from_channel(channel)
    if not category_config:
        return await interaction.response.send_message("❌ Erro: Não foi possível determinar a categoria deste ticket.", ephemeral=True)

    user_roles_ids = {role.id for role in interaction.user.roles}
    manager_ids = TicketActionsView()._get_manager_ids_for_category(category_config)
    is_manager = not user_roles_ids.isdisjoint(manager_ids)
    assumer_id = await TicketActionsView()._get_assumer_id(channel)
    is_assumer = (interaction.user.id == assumer_id)

    if not is_manager and not is_assumer:
        return await interaction.response.send_message("❌ Apenas quem assumiu o ticket ou um gerente pode fechá-lo.", ephemeral=True)

    await interaction.response.send_message("🔒 A arquivar o ticket, isto pode demorar um momento...", ephemeral=True)
    
    transcript_log_channel = interaction.guild.get_channel(module_config.ID_CANAL_LOGS_TICKETS)
    image_storage_channel = interaction.guild.get_channel(module_config.ID_CANAL_STORAGE_IMAGENS)

    if not transcript_log_channel or not image_storage_channel:
        error_msg = "❌ Erro de configuração: Um ou mais canais de log não foram encontrados."
        print(f"[{global_config.CONTEXTO}] ERRO CRÍTICO: {error_msg}")
        await interaction.followup.send(error_msg, ephemeral=True)
        return

    try:
        # 1. Mapear URL antigo -> nova URL, processando apenas imagens de utilizadores
        attachment_map = {}
        async with aiohttp.ClientSession() as session:
            async for message in channel.history(limit=None, oldest_first=True):
                if not message.author.bot and message.attachments:
                    for attachment in message.attachments:
                        if "image" in attachment.content_type:
                            try:
                                async with session.get(attachment.url) as response:
                                    if response.status == 200:
                                        data = io.BytesIO(await response.read())
                                        new_file = discord.File(data, filename=attachment.filename)
                                        msg = await image_storage_channel.send(file=new_file)
                                        attachment_map[attachment.url] = msg.attachments[0].url
                            except Exception as e:
                                print(f"[{global_config.CONTEXTO}] Falha ao reenviar anexo {attachment.filename}: {e}")

        # 2. Gerar o transcript HTML
        transcript_html = await chat_exporter.export(channel)

        if transcript_html:
            # 3. Substituir no HTML usando o nome do ficheiro como âncora
            for old_url, new_url in attachment_map.items():
                # Gera todas as variações possíveis do link
                url_variations = [
                    old_url,
                    html.escape(old_url),
                    old_url.replace("cdn.discordapp.com", "media.discordapp.net"),
                    html.escape(old_url.replace("cdn.discordapp.com", "media.discordapp.net"))
                ]
                print(f"[Transcript Replace] Substituindo URLs:\n  VARIATIONS: {url_variations}\n  NEW: {new_url}")
                for url in url_variations:
                    transcript_html = transcript_html.replace(url, new_url)

            # 4. Enviar o transcript final e corrigido
            final_transcript_file = discord.File(io.BytesIO(transcript_html.encode("utf-8")), filename=f"transcript-{channel.name}.html")
            topic_parts = channel.topic.split(" | ")
            autor_id = topic_parts[2].replace("ID do Autor: ", "")
            autor_mention = f"<@{autor_id}>"
            category_name_from_topic = re.search(r"Categoria: (.*?)(?: \||$)", channel.topic).group(1).strip()
            embed = Embed(title="📝 Transcript de Ticket Fechado", color=discord.Color.from_rgb(255, 170, 51))
            embed.add_field(name="Nome do Canal", value=f"`{channel.name}`", inline=False)
            embed.add_field(name="Aberto por", value=autor_mention, inline=True)
            embed.add_field(name="Fechado por", value=interaction.user.mention, inline=True)
            embed.add_field(name="Categoria", value=category_name_from_topic, inline=True)
            embed.timestamp = datetime.now()
            await transcript_log_channel.send(embed=embed, file=final_transcript_file)

    except Exception as e:
        print(f"[{global_config.CONTEXTO}] ERRO CRÍTICO ao gerar transcript: {e}")

    # 5. Apagar o canal do ticket
    await channel.delete(reason=f"Ticket fechado por {interaction.user.name}")


# --- LÓGICA CENTRALIZADA DE CRIAÇÃO DE TICKET ---
async def create_ticket_channel(interaction: discord.Interaction, category_name: str):
    print(f"[{global_config.CONTEXTO}] Tentando criar ticket para a categoria: '{category_name}'")
    await interaction.response.defer(ephemeral=True, thinking=True)

    guild = interaction.guild
    membro = interaction.user
    category_config = module_config.TICKET_CATEGORIAS.get(category_name)

    if not category_config:
        print(f"[{global_config.CONTEXTO}] ERRO: Configuração da categoria '{category_name}' não encontrada.")
        await interaction.followup.send("❌ Erro de configuração. Categoria não encontrada.", ephemeral=True)
        return

    ticket_category_channel = guild.get_channel(category_config["id_categoria_discord"])
    if ticket_category_channel:
        for channel in ticket_category_channel.text_channels:
            if channel.topic and f"ID do Autor: {membro.id}" in channel.topic and f"Categoria: {category_name}" in channel.topic:
                await interaction.followup.send(f"❌ Você já possui um ticket aberto em {channel.mention}.", ephemeral=True)
                return

    count_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), category_config.get("arquivo_contagem"))
    initial_num = category_config.get("numero_inicial", 1)
    ticket_number = load_ticket_count(count_file_path, initial_num)
    save_ticket_count(count_file_path, ticket_number + 1)

    name_parts = membro.display_name.split()
    first_name = name_parts[0] if name_parts else "usuario"
    membro_display_name = re.sub(r'[^a-z0-9-]', '', first_name.lower())
    
    prefix = "ticket"
    if category_name == "Agendamento de Fotos":
        prefix = "foto"
    elif category_name == "Roupas e Acessórios":
        prefix = "roupas"

    channel_name = f"{prefix}-{membro_display_name}-{ticket_number:04d}"

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        membro: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
    }
    for grupo in category_config.get("permissoes_cargos", []):
        perm_obj = discord.PermissionOverwrite(**grupo.get("permissoes", {}))
        for cargo_id in grupo.get("cargos", []):
            cargo = guild.get_role(cargo_id)
            if cargo: overwrites[cargo] = perm_obj

    try:
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=ticket_category_channel,
            overwrites=overwrites,
            topic=f"Ticket de {membro.mention} | Categoria: {category_name} | ID do Autor: {membro.id}"
        )
    except Exception as e:
        print(f"[{global_config.CONTEXTO}] ERRO ao criar canal de ticket: {e}")
        save_ticket_count(count_file_path, ticket_number)
        await interaction.followup.send("❌ Ocorreu um erro ao criar o canal. Contate um administrador.", ephemeral=True)
        return

    embed_to_send = None
    view_to_send = None
    files_to_send = []

    if category_name == "Agendamento de Fotos":
        embed_to_send = discord.Embed(
            title="🎫 Ticket de Fotografia Aberto",
            description=f"Olá {membro.mention}, este é seu espaço exclusivo para agendar seu ensaio!\n\nUse os botões abaixo para escolher **dia**, **horário** e **cidade**.\n✨ Nossa equipe irá confirmar seu atendimento em breve!",
            color=discord.Color.from_rgb(212, 16, 222)
        )
        embed_to_send.set_image(url=f"attachment://banner.png")
        embed_to_send.set_footer(text=f"ID do Autor: {membro.id}")
        view_to_send = FotoActionsView()
        files_to_send.append(discord.File(os.path.join(os.path.dirname(__file__), "banner.png")))
    elif category_name == "Roupas e Acessórios":
        embed_to_send = discord.Embed(
            title="🎫 Ticket de Roupas Personalizadas",
            description=f"Olá {membro.mention}, obrigado por abrir um ticket com a Jaguar Studio!\n\n"
                        f"👕 Nos conte como deseja sua peça exclusiva!\n"
                        f"📸 Envie referências ou fotos\n"
                        f"🎨 Detalhe cores, logos e estilo que preferir\n\n"
                        f"✨ Nossa equipe criativa irá atendê-lo em breve!",
            color=discord.Color.from_rgb(212, 16, 222)
        )
        embed_to_send.set_image(url=f"attachment://banner.png")
        view_to_send = RoupasActionsView()
        files_to_send.append(discord.File(os.path.join(os.path.dirname(__file__), "banner.png")))
    else:
        embed_to_send = Embed(title=f"🎫 Ticket - {category_name}", description=category_config["modelo_embed"], color=discord.Color.blue())
        embed_to_send.set_footer(text=f"Ticket aberto por {membro.display_name}")
        embed_to_send.timestamp = datetime.now()
        view_to_send = TicketActionsView()

    await ticket_channel.send(content=f"Bem-vindo, {membro.mention}!", embed=embed_to_send, view=view_to_send, files=files_to_send)
    await interaction.followup.send(f"✅ Seu ticket foi aberto com sucesso em {ticket_channel.mention}!", ephemeral=True)


# --- VIEWS DE AÇÕES NO TICKET (Assumir, Fechar, etc) ---
class TicketActionsView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    def _get_category_config_from_channel(self, channel: discord.TextChannel):
        if not channel.topic: return None
        match = re.search(r"Categoria: (.*?)(?: \||$)", channel.topic)
        if not match: return None
        category_name = match.group(1).strip()
        return module_config.TICKET_CATEGORIAS.get(category_name)
    def _get_all_staff_ids_for_category(self, category_config: dict):
        if not category_config: return set()
        all_staff_ids = set()
        for grupo in category_config.get("permissoes_cargos", []):
            for cargo_id in grupo.get("cargos", []):
                all_staff_ids.add(cargo_id)
        return all_staff_ids
    def _get_manager_ids_for_category(self, category_config: dict):
        if not category_config: return set()
        permissoes_grupos = category_config.get("permissoes_cargos", [])
        if not permissoes_grupos: return set()
        return set(permissoes_grupos[0].get("cargos", []))
    async def _get_assumer_id(self, channel: discord.TextChannel):
        async for message in channel.history(limit=25, oldest_first=False):
            if message.author.bot and message.content.startswith("✅ Este ticket foi assumido por"):
                if message.mentions: return message.mentions[0].id
        return None
    @ui.button(label="Assumir Ticket", style=ButtonStyle.primary, custom_id="assume_ticket", emoji="🙋")
    async def assume_ticket(self, interaction: discord.Interaction, button: ui.Button):
        category_config = self._get_category_config_from_channel(interaction.channel)
        staff_ids = self._get_all_staff_ids_for_category(category_config)
        user_roles_ids = {role.id for role in interaction.user.roles}
        if user_roles_ids.isdisjoint(staff_ids):
            return await interaction.response.send_message("❌ Você não tem permissão para interagir com tickets desta categoria.", ephemeral=True)
        await interaction.response.defer()
        channel = interaction.channel
        staff_member = interaction.user
        await channel.set_permissions(staff_member, send_messages=True, view_channel=True)
        try:
            name_parts = staff_member.display_name.split()
            first_name = name_parts[0] if name_parts else "atendente"
            staff_display_name = re.sub(r'[^a-z0-9-]', '', first_name.lower())
            ticket_number_str = channel.name.split('-')[-1]
            new_name = f"{staff_display_name}-{ticket_number_str}"
            await channel.edit(name=new_name)
        except Exception as e: print(f"ERRO AO RENOMEAR CANAL ASSUMIDO: {e}")
        button.disabled = True
        await interaction.message.edit(view=self)
        await channel.send(f"✅ Este ticket foi assumido por {staff_member.mention}.")
    @ui.button(label="Fechar Ticket", style=ButtonStyle.danger, custom_id="close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await _close_ticket_logic(interaction)


# --- VIEWS PARA TICKET DE FOTOS ---

class ServerModal(ui.Modal, title="Qual servidor?"):
    server_name = ui.TextInput(label="Nome do Servidor", placeholder="Ex: Jaguar City", required=True)

    def __init__(self, day, time):
        super().__init__()
        self.day = day
        self.time = time
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        schedule = load_schedule()
        user_id = str(interaction.user.id)
        
        if self.day not in schedule:
            schedule[self.day] = {}
        schedule[self.day][user_id] = {
            "time": self.time,
            "server": self.server_name.value,
            "channel_id": interaction.channel.id,
            "notified": False
        }
        
        embed_confirmacao = discord.Embed(
            title="✅ Reserva Confirmada!",
            color=discord.Color.green(),
            description="✨ Obrigado por escolher o Jaguar Studio!"
        )
        embed_confirmacao.add_field(name="📅 Dia:", value=f"{self.day.replace('-feira', '')}", inline=True)
        embed_confirmacao.add_field(name="⏰ Horário:", value=f"{self.time}", inline=True)
        embed_confirmacao.add_field(name="🏙️ Cidade:", value=f"{self.server_name.value}", inline=True)
        embed_confirmacao.set_footer(text="Jaguar Studio • Atendimento Premium")
        banner_path = os.path.join(os.path.dirname(__file__), "banner.png")
        
        if os.path.exists(banner_path):
            file = discord.File(banner_path, filename="banner.png")
            embed_confirmacao.set_thumbnail(url="attachment://banner.png")
            
            sent_message = await interaction.channel.send(embed=embed_confirmacao, file=file)
            schedule[self.day][user_id]["message_id"] = sent_message.id
        else:
            sent_message = await interaction.channel.send(embed=embed_confirmacao)
            schedule[self.day][user_id]["message_id"] = sent_message.id
        
        # Lógica para copiar a embed para o canal de agendamentos
        agendamentos_channel = interaction.guild.get_channel(module_config.ID_CANAL_AGENDAMENTOS)
        if agendamentos_channel:
            copied_embed = discord.Embed(
                title="Novo Agendamento Confirmado",
                color=discord.Color.from_rgb(212, 16, 222),
                description=f"Um novo ensaio foi agendado."
            )
            copied_embed.add_field(name="Membro", value=interaction.user.mention, inline=True)
            copied_embed.add_field(name="Data", value=self.day.replace('-feira', ''), inline=True)
            copied_embed.add_field(name="Horário", value=self.time, inline=True)
            copied_embed.add_field(name="Servidor", value=self.server_name.value, inline=False)
            copied_embed.add_field(name="Ticket", value=interaction.channel.mention, inline=False)
            copied_embed.set_footer(text=f"ID do Ticket: {interaction.channel.id}")
            
            sent_copied_message = await agendamentos_channel.send(embed=copied_embed)
            schedule[self.day][user_id]["schedule_message_id"] = sent_copied_message.id


        save_schedule(schedule)

        try:
            await interaction.message.delete()
        except Exception:
            pass
        
        await interaction.followup.send("✅ Seu horário foi agendado com sucesso!", ephemeral=True)


class TimeButton(ui.Button):
    def __init__(self, day: str, time: str, is_occupied: bool, **kwargs):
        super().__init__(label=f"{time} (ocupado)" if is_occupied else time,
                         style=ButtonStyle.red if is_occupied else ButtonStyle.green,
                         disabled=is_occupied,
                         custom_id=f"time_btn_{day}_{time.replace(':', '_')}",
                         **kwargs)
        self.day = day
        self.time = time

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ServerModal(self.day, self.time))


class DayButton(ui.Button):
    def __init__(self, day_name: str, **kwargs):
        super().__init__(label=day_name, style=ButtonStyle.primary, custom_id=f"day_btn_{day_name}", **kwargs)
        self.day_name = day_name
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=f"Você escolheu {self.day_name}. Agora escolha o horário:", view=TimeButtonsView(self.day_name))


class TimeButtonsView(ui.View):
    def __init__(self, day: str):
        super().__init__(timeout=180)
        self.day = day
        schedule = load_schedule()
        occupied_times = {data.get("time") for data in schedule.get(day, {}).values()}
        for hour in range(19, 24):
            time_str = f"{hour}:00"
            is_occupied = time_str in occupied_times
            self.add_item(TimeButton(day=day, time=time_str, is_occupied=is_occupied))


class DayButtonsView(ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        days = ["Terça-feira", "Quinta-feira", "Sábado", "Domingo"]
        for day in days:
            self.add_item(DayButton(day_name=day))


class FotoActionsView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @ui.button(label="Fechar Ticket", style=ButtonStyle.danger, custom_id="foto_fechar_ticket", emoji="❌")
    async def fechar_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await _close_ticket_logic(interaction)

    @ui.button(label="Ver Horários", style=ButtonStyle.primary, custom_id="foto_ver_horarios", emoji="🗓️")
    async def ver_horarios(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Escolha um dia:", view=DayButtonsView(), ephemeral=True)

    @ui.button(label="Notificar Cliente", style=ButtonStyle.success, custom_id="foto_notificar_cliente", emoji="🔔")
    async def notificar_cliente(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        channel_topic = interaction.channel.topic
        autor_id_match = re.search(r"ID do Autor: (\d+)", channel_topic)
        if autor_id_match:
            autor_id = int(autor_id_match.group(1))
            member = interaction.guild.get_member(autor_id)
            if member:
                try:
                    await member.send(f"🔔 Olá! Um membro da equipe te aguarda no seu ticket de fotografia: {interaction.channel.mention}")
                    await interaction.followup.send("✅ Cliente notificado com sucesso!", ephemeral=True)
                except discord.Forbidden:
                    await interaction.followup.send("❌ Não foi possível enviar a DM para o cliente. Ele pode ter as DMs desativadas.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Não foi possível encontrar o membro autor do ticket.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Não foi possível encontrar o ID do autor no tópico do canal.", ephemeral=True)

    @ui.button(label="Cancelar Reserva", style=ButtonStyle.red, custom_id="foto_cancelar_reserva", emoji="✖️")
    async def cancelar_reserva(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        user_id = str(interaction.user.id)
        schedule = load_schedule()
        
        found = False
        message_id = None
        schedule_message_id = None
        
        for day in schedule:
            if user_id in schedule[day]:
                message_id = schedule[day][user_id].get("message_id")
                schedule_message_id = schedule[day][user_id].get("schedule_message_id")
                del schedule[day][user_id]
                found = True
                break
        
        save_schedule(schedule)
        
        if found:
            # Tenta apagar a mensagem no canal de agendamentos
            if schedule_message_id:
                agendamentos_channel = interaction.guild.get_channel(module_config.ID_CANAL_AGENDAMENTOS)
                if agendamentos_channel:
                    try:
                        message_to_delete = await agendamentos_channel.fetch_message(schedule_message_id)
                        await message_to_delete.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass

            # Tenta apagar a mensagem no canal do ticket
            try:
                if message_id:
                    message_to_delete = await interaction.channel.fetch_message(message_id)
                    await message_to_delete.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

            await interaction.followup.send("✅ Sua reserva foi cancelada com sucesso!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Você não possui nenhuma reserva ativa para cancelar.", ephemeral=True)


class RoupasActionsView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @ui.button(label="Fechar Ticket", style=ButtonStyle.danger, custom_id="roupas_fechar_ticket", emoji="❌")
    async def fechar_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await _close_ticket_logic(interaction)

    @ui.button(label="Notificar Cliente", style=ButtonStyle.success, custom_id="roupas_notificar_cliente", emoji="🔔")
    async def notificar_cliente(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        channel_topic = interaction.channel.topic
        autor_id_match = re.search(r"ID do Autor: (\d+)", channel_topic)
        if autor_id_match:
            autor_id = int(autor_id_match.group(1))
            member = interaction.guild.get_member(autor_id)
            if member:
                try:
                    await member.send(f"🔔 Olá! Um membro da equipe te aguarda no seu ticket de roupas: {interaction.channel.mention}")
                    await interaction.followup.send("✅ Cliente notificado com sucesso!", ephemeral=True)
                except discord.Forbidden:
                    await interaction.followup.send("❌ Não foi possível enviar a DM para o cliente. Ele pode ter as DMs desativadas.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Não foi possível encontrar o membro autor do ticket.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Não foi possível encontrar o ID do autor no tópico do canal.", ephemeral=True)

# --- VIEWS E BOTÕES PARA TICKETS GENÉRICOS ---
class TicketButton(ui.Button):
    def __init__(self, category_name: str, **kwargs):
        super().__init__(label=f"Abrir Ticket", style=ButtonStyle.green, custom_id=f"ticket_btn_{category_name.replace(' ','_')}")
        self.category_name = category_name

    async def callback(self, interaction: discord.Interaction):
        print(f"[{global_config.CONTEXTO}] Botão de ticket clicado! Iniciando criação de canal para a categoria: {self.category_name}.")
        await create_ticket_channel(interaction, self.category_name)

class TicketButtonView(ui.View):
    def __init__(self, category_name: str):
        super().__init__(timeout=None)
        self.category_name = category_name
        self.add_item(TicketButton(category_name=category_name))

# Cog Principal e Comandos
class MultiTickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weekly_reset.start()
        self.check_ensaios_schedule.start()

    def cog_unload(self):
        self.weekly_reset.cancel()
        self.check_ensaios_schedule.cancel()

    @commands.hybrid_command(name="tickets-roupas", description="Envia o painel de tickets para roupas e acessórios.")
    @commands.has_permissions(administrator=True)
    async def tickets_roupas(self, ctx: commands.Context):
        print(f"[{global_config.CONTEXTO}] Comando !tickets-roupas foi executado.")
        if ctx.guild.id != global_config.ID_SERVIDOR: return

        category_name = "Roupas e Acessórios"
        category_config = module_config.TICKET_CATEGORIAS.get(category_name)
        if not category_config:
            print(f"[{global_config.CONTEXTO}] ERRO: Configuração para 'Roupas e Acessórios' não encontrada no config.py.")
            return

        embed_to_send = module_config.EMBED_TICKETS_ROUPAS
        files_to_send = []
        logo_filename = "icon.png"
        logo_path = os.path.join(os.path.dirname(__file__), logo_filename)
        if os.path.exists(logo_path):
            file_logo = discord.File(logo_path, filename=logo_filename)
            embed_to_send.set_thumbnail(url=f"attachment://{logo_filename}")
            files_to_send.append(file_logo)

        banner_filename = "banner.png"
        banner_path = os.path.join(os.path.dirname(__file__), banner_filename)
        if os.path.exists(banner_path):
            file_banner = discord.File(banner_path, filename=banner_filename)
            embed_to_send.set_image(url=f"attachment://{banner_filename}")
            files_to_send.append(file_banner)

        footer_icon_filename = "roupa_icon.png"
        footer_icon_path = os.path.join(os.path.dirname(__file__), footer_icon_filename)
        if os.path.exists(footer_icon_path):
            files_to_send.append(discord.File(footer_icon_path, filename=footer_icon_filename))
            embed_to_send.set_footer(text="👕 Jaguar Studio • Sistema de Tickets Premium", icon_url=f"attachment://{footer_icon_filename}")
        else:
            embed_to_send.set_footer(text="👕 Jaguar Studio • Sistema de Tickets Premium")

        await ctx.send(embed=embed_to_send, files=files_to_send, view=TicketButtonView(category_name=category_name))
        try: await ctx.message.delete()
        except: pass

    @commands.hybrid_command(name="tickets-fotos", description="Envia o painel de tickets para agendamento de fotos.")
    @commands.has_permissions(administrator=True)
    async def tickets_fotos(self, ctx: commands.Context):
        print(f"[{global_config.CONTEXTO}] Comando !tickets-fotos foi executado.")
        if ctx.guild.id != global_config.ID_SERVIDOR: return

        category_name = "Agendamento de Fotos"
        category_config = module_config.TICKET_CATEGORIAS.get(category_name)
        if not category_config:
            print(f"[{global_config.CONTEXTO}] ERRO: Configuração para 'Agendamento de Fotos' não encontrada no config.py.")
            return

        embed_to_send = module_config.EMBED_TICKETS_ENSAIO
        files_to_send = []
        logo_filename = "icon.png"
        logo_path = os.path.join(os.path.dirname(__file__), logo_filename)
        if os.path.exists(logo_path):
            file_logo = discord.File(logo_path, filename=logo_filename)
            embed_to_send.set_thumbnail(url=f"attachment://{logo_filename}")
            files_to_send.append(file_logo)

        banner_filename = "banner.png"
        banner_path = os.path.join(os.path.dirname(__file__), banner_filename)
        if os.path.exists(banner_path):
            file_banner = discord.File(banner_path, filename=banner_filename)
            embed_to_send.set_image(url=f"attachment://{banner_filename}")
            files_to_send.append(file_banner)

        footer_icon_filename = "roupa_icon.png"
        footer_icon_path = os.path.join(os.path.dirname(__file__), footer_icon_filename)
        if os.path.exists(footer_icon_path):
            files_to_send.append(discord.File(footer_icon_path, filename=footer_icon_filename))
            embed_to_send.set_footer(text="📸 Jaguar Studio • Fotografia Premium", icon_url=f"attachment://{footer_icon_filename}")
        else:
            embed_to_send.set_footer(text="📸 Jaguar Studio • Fotografia Premium")

        await ctx.send(embed=embed_to_send, files=files_to_send, view=TicketButtonView(category_name=category_name))
        try: await ctx.message.delete()
        except: pass

    @tasks.loop(hours=24)
    async def weekly_reset(self):
        await self.bot.wait_until_ready()
        now = datetime.now()
        if now.weekday() == 0 and now.hour == 1:
            save_schedule({})
            print(f"[{global_config.CONTEXTO}] O agendamento semanal foi resetado.")
    
    @tasks.loop(minutes=5)
    async def check_ensaios_schedule(self):
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(global_config.ID_SERVIDOR)
        if not guild: return
        
        schedule = load_schedule()
        now = datetime.now()
        
        portuguese_to_english_days = {
            "Terça-feira": "Tuesday",
            "Quinta-feira": "Thursday",
            "Sábado": "Saturday",
            "Domingo": "Sunday"
        }
        
        role_to_notify = guild.get_role(module_config.ID_CARGO_NOTIFICACAO_ENSAIO)
        if not role_to_notify:
            print(f"[{global_config.CONTEXTO}] ERRO: Cargo de notificação não encontrado.")
            return

        members_to_notify = [member for member in guild.members if role_to_notify in member.roles]

        updated_schedule = False

        for day, users in list(schedule.items()):
            for user_id, data in list(users.items()):
                if data.get("notified", False):
                    continue

                try:
                    english_day = portuguese_to_english_days.get(day)
                    if not english_day: continue

                    time_str = data["time"]
                    
                    # Encontra a próxima ocorrência do dia da semana
                    current_day_of_week = now.weekday()
                    target_day_of_week = datetime.strptime(english_day, '%A').weekday()
                    
                    days_until_target = (target_day_of_week - current_day_of_week + 7) % 7
                    
                    scheduled_datetime = now.replace(hour=int(time_str.split(':')[0]), minute=int(time_str.split(':')[1]), second=0, microsecond=0) + timedelta(days=days_until_target)

                    time_remaining = scheduled_datetime - now
                    
                    if timedelta(hours=0) <= time_remaining <= timedelta(hours=1):
                        
                        ticket_channel = guild.get_channel(data.get("channel_id"))
                        if not ticket_channel:
                            continue

                        # Envia a notificação para cada membro com o cargo
                        for member in members_to_notify:
                            try:
                                await member.send(
                                    f"🔔 Olá! O ensaio fotográfico agendado está prestes a começar!\n\n"
                                    f"**Detalhes:**\n"
                                    f"Membro: <@{user_id}>\n"
                                    f"Horário: {data['time']}\n"
                                    f"Servidor: {data['server']}\n"
                                    f"Clique aqui para ir para o ticket: {ticket_channel.mention}"
                                )
                            except discord.Forbidden:
                                print(f"[{global_config.CONTEXTO}] Não foi possível enviar DM para {member.name}.")

                        data["notified"] = True
                        updated_schedule = True

                except (ValueError, KeyError) as e:
                    print(f"[{global_config.CONTEXTO}] ERRO ao processar agendamento: {e} | Dados: {data}")
        
        if updated_schedule:
            save_schedule(schedule)


async def setup(bot):
    print(f"[{global_config.CONTEXTO}] Carregando módulo MultiTickets...")
    bot.add_view(TicketActionsView())
    bot.add_view(FotoActionsView())
    bot.add_view(RoupasActionsView())
    for name in module_config.TICKET_CATEGORIAS.keys():
        bot.add_view(TicketButtonView(category_name=name))
    await bot.add_cog(MultiTickets(bot))
    print(f"[{global_config.CONTEXTO}] Módulo MultiTickets carregado com sucesso.")