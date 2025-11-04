import discord
from discord.ext import commands
import asyncio
import io
import html
import aiohttp
import chat_exporter
import re
from datetime import datetime
import pytz
import os

import server.funcionalidades.tickets.config as module_config
import config.config as global_config

# Define o fuso horário de São Paulo
fuso_horario_sp = pytz.timezone('America/Sao_Paulo')

async def create_ticket_channel(interaction: discord.Interaction, category_name: str):
    """Lógica centralizada para criar um canal de ticket para uma categoria específica."""
    await interaction.response.defer(ephemeral=True, thinking=True)

    guild = interaction.guild
    membro = interaction.user
    category_config = module_config.TICKET_CATEGORIAS.get(category_name)

    if not category_config:
        await interaction.followup.send(f"❌ Erro de configuração: A categoria '{category_name}' não foi encontrada.", ephemeral=True)
        return

    # Verifica se o membro já tem um ticket aberto para esta categoria
    ticket_category_channel = guild.get_channel(category_config["id_categoria_discord"])
    if ticket_category_channel:
        for channel in ticket_category_channel.text_channels:
            if channel.topic and f"ID do Autor: {membro.id}" in channel.topic and f"Categoria: {category_name}" in channel.topic:
                await interaction.followup.send(f"❌ Você já possui um ticket aberto em {channel.mention} para esta categoria.", ephemeral=True)
                return

    # Incrementa o contador de tickets da categoria
    count_file_path = category_config.get("arquivo_contagem", f"ticket_count_{category_name.lower()}.txt")
    initial_num = category_config.get("numero_inicial", 1)
    try:
        with open(count_file_path, "r") as f:
            count = int(f.read())
    except (FileNotFoundError, ValueError):
        count = initial_num - 1
    count += 1
    with open(count_file_path, "w") as f:
        f.write(str(count))

    # Formata o nome do canal
    ticket_number = f"{count:04d}"
    user_name_safe = re.sub(r'[^a-z0-9-]', '', interaction.user.name.lower())
    channel_name = f"ticket-{user_name_safe}-{ticket_number}"

    # Define as permissões
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        membro: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    staff_mentions_list = []
    # Adiciona cargos de staff configurados para a categoria
    for grupo in category_config.get("permissoes_cargos", []):
        perm_obj = discord.PermissionOverwrite(**grupo.get("permissoes", {}))
        for cargo_id in grupo.get("cargos", []):
            role = guild.get_role(cargo_id)
            if role:
                overwrites[role] = perm_obj
                staff_mentions_list.append(f'<@&{cargo_id}>')

    # Cria o canal do ticket
    ticket_channel = await guild.create_text_channel(
        channel_name,
        overwrites=overwrites,
        category=ticket_category_channel,
        topic=f"Ticket de {membro.mention} | Categoria: {category_name} | ID do Autor: {membro.id}"
    )

    # Envia a mensagem de boas-vindas no ticket
    embed = discord.Embed(
        title=f"🎫 Ticket - {category_name}",
        description=category_config["modelo_embed"].format(user=membro.mention),
        color=discord.Color.blue()
    )

    staff_mentions = ' '.join(staff_mentions_list)

    await ticket_channel.send(content=f"{membro.mention} {staff_mentions}", embed=embed, view=TicketManagementView())
    await interaction.followup.send(f"✅ Seu ticket foi criado com sucesso em {ticket_channel.mention}!", ephemeral=True)


async def _close_ticket_logic(interaction: discord.Interaction):
    """Lógica centralizada para fechar e arquivar um ticket."""
    await interaction.response.send_message("🔒 A arquivar o ticket, isto pode demorar um momento...", ephemeral=True)

    channel = interaction.channel
    transcript_log_channel = interaction.guild.get_channel(module_config.ID_CANAL_LOGS_TICKETS)
    image_storage_channel = interaction.guild.get_channel(module_config.ID_CANAL_STORAGE_IMAGENS)

    if not transcript_log_channel or not image_storage_channel:
        error_msg = "❌ Erro de configuração: Um ou mais canais de log/storage não foram encontrados."
        print(f"[{global_config.CONTEXTO}] ERRO CRÍTICO: {error_msg}")
        await interaction.followup.send(error_msg, ephemeral=True)
        return

    try:
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

        transcript_html = await chat_exporter.export(channel)

        if transcript_html:
            for old_url, new_url in attachment_map.items():
                url_variations = [
                    old_url, html.escape(old_url),
                    old_url.replace("cdn.discordapp.com", "media.discordapp.net"),
                    html.escape(old_url.replace("cdn.discordapp.com", "media.discordapp.net"))
                ]
                for url in url_variations:
                    transcript_html = transcript_html.replace(url, new_url)

            final_transcript_file = discord.File(io.BytesIO(transcript_html.encode("utf-8")), filename=f"transcript-{channel.name}.html")

            creator = None
            category_name_from_topic = "Geral"
            if channel.topic:
                creator_match = re.search(r"ID do Autor: (\d+)", channel.topic)
                category_match = re.search(r"Categoria: (.*?)(?: \||$)", channel.topic)
                if creator_match:
                    creator = interaction.guild.get_member(int(creator_match.group(1)))
                if category_match:
                    category_name_from_topic = category_match.group(1).strip()
            
            autor_mention = creator.mention if creator else "Não encontrado"

            embed = discord.Embed(title="📝 Transcript de Ticket Fechado", color=discord.Color.from_rgb(255, 170, 51))
            embed.add_field(name="Nome do Canal", value=f"`{channel.name}`", inline=False)
            embed.add_field(name="Aberto por", value=autor_mention, inline=True)
            embed.add_field(name="Fechado por", value=interaction.user.mention, inline=True)
            embed.add_field(name="Categoria", value=category_name_from_topic, inline=True)
            embed.timestamp = datetime.now(fuso_horario_sp)
            await transcript_log_channel.send(embed=embed, file=final_transcript_file)

    except Exception as e:
        print(f"[{global_config.CONTEXTO}] ERRO CRÍTICO ao gerar transcript: {e}")

    await channel.delete(reason=f"Ticket fechado por {interaction.user.name}")


class TicketCategoryButton(discord.ui.Button):
    def __init__(self, category_name: str):
        super().__init__(
            label=category_name,
            style=discord.ButtonStyle.gray,
            custom_id=f"create_ticket_{category_name.replace(' ', '_')}"
        )
        self.category_name = category_name

    async def callback(self, interaction: discord.Interaction):
        await create_ticket_channel(interaction, self.category_name)


class TicketCreationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Cria um botão para cada categoria definida no config
        for category_name in module_config.TICKET_CATEGORIAS.keys():
            self.add_item(TicketCategoryButton(category_name))


class TicketManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def _get_category_config_from_channel(self, channel: discord.TextChannel):
        """Obtém a configuração da categoria a partir do tópico do canal."""
        if not channel.topic:
            return next(iter(module_config.TICKET_CATEGORIAS.values()), None)
        match = re.search(r"Categoria: (.*?)(?: \||$)", channel.topic)
        if not match:
            return next(iter(module_config.TICKET_CATEGORIAS.values()), None)
        category_name = match.group(1).strip()
        return module_config.TICKET_CATEGORIAS.get(category_name)

    @discord.ui.button(label="Assumir Ticket", style=discord.ButtonStyle.primary, emoji="🙋", custom_id="assume_ticket")
    async def assume_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        category_config = self._get_category_config_from_channel(interaction.channel)
        if not category_config:
            return await interaction.response.send_message("❌ Não foi possível determinar a categoria deste ticket.", ephemeral=True)

        # Define os cargos que podem assumir o ticket
        staff_role_ids = set()
        for grupo in category_config.get("permissoes_cargos", []):
            staff_role_ids.update(grupo.get("cargos", []))
        
        user_role_ids = {role.id for role in interaction.user.roles}

        # Verifica se o usuário tem permissão
        if user_role_ids.isdisjoint(staff_role_ids) and not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Você não tem um cargo de suporte para assumir este ticket.", ephemeral=True)

        # Verifica se o ticket já foi assumido
        async for message in interaction.channel.history(limit=20, oldest_first=False):
            if message.author.bot and "ticket foi assumido por" in message.content:
                await interaction.response.send_message("❌ Este ticket já foi assumido.", ephemeral=True)
                if not button.disabled:
                    button.disabled = True
                    await interaction.message.edit(view=self)
                return
        
        await interaction.response.defer()
        
        staff_member = interaction.user
        channel = interaction.channel
        
        await channel.set_permissions(staff_member, send_messages=True, view_channel=True, read_messages=True)

        button.disabled = True
        await interaction.message.edit(view=self)
        await channel.send(f"✅ Este ticket foi assumido por {staff_member.mention}.")

    @discord.ui.button(label="Fechar", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="fechar_ticket_confirm")
    async def callback_fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Apenas membros com permissão de gerenciar canais podem fechar tickets
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Apenas administradores podem fechar o ticket.", ephemeral=True)
        
        await _close_ticket_logic(interaction)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="tickets", description="Envia o painel de abertura de tickets com categorias.")
    @commands.has_permissions(administrator=True)
    async def tickets(self, ctx: commands.Context):
        embed = module_config.TICKETS_COMMAND_EMBED
        view = TicketCreationView() if module_config.USAR_BOTOES_PARA_TICKETS else None
        
        await ctx.send(embed=embed, view=view)
        
        if ctx.interaction:
            await ctx.interaction.response.send_message("Painel enviado!", ephemeral=True, delete_after=5)
        else:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

async def setup(bot):
    bot.add_view(TicketCreationView())
    bot.add_view(TicketManagementView())
    await bot.add_cog(Tickets(bot))