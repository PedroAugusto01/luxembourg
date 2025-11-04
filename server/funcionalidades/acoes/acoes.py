# /server/funcionalidades/acoes/acoes.py

import discord
from discord import ui, Interaction, ButtonStyle, Embed, TextStyle
from discord.ext import commands, tasks
import asyncio
import re
import traceback
from datetime import datetime, timedelta
import pytz
from . import config as module_config

# --- Funções Auxiliares ---

def has_permission(member: discord.Member) -> bool:
    """Verifica se um membro tem permissão para gerenciar ações."""
    if not module_config.IDS_CARGOS_PERMITIDOS or all(cid == 0 for cid in module_config.IDS_CARGOS_PERMITIDOS):
        return member.guild_permissions.administrator
        
    ids_permitidos = set(module_config.IDS_CARGOS_PERMITIDOS)
    ids_usuario = {role.id for role in member.roles}
    return not ids_usuario.isdisjoint(ids_permitidos)

def parse_embed_data(embed: Embed):
    data = {}
    if not embed.description: return data
    
    inscritos_match = re.search(r"\*\*<a:SetaDireita:1418996596699566164> Inscritos \(\d+/(\d+)\):?\*\*\n(.*?)\n\n", embed.description, re.DOTALL)
    reservas_match = re.search(r"\*\*<a:SetaDireita:1418996596699566164> Reservas \(\d+/(\d+)\):?\*\*\n(.*)", embed.description, re.DOTALL)

    data['limite_inscritos'] = int(inscritos_match.group(1)) if inscritos_match else 0
    data['inscritos'] = [int(uid) for uid in re.findall(r'<@(\d+)>', inscritos_match.group(2))] if inscritos_match else []

    data['limite_reservas'] = int(reservas_match.group(1)) if reservas_match else 0
    data['reservas'] = [int(uid) for uid in re.findall(r'<@(\d+)>', reservas_match.group(2))] if reservas_match else []
    
    return data

async def atualizar_embed_acao(message: discord.Message, novos_inscritos: list[int], novos_reservas: list[int]):
    embed = message.embeds[0]
    
    linhas = embed.description.splitlines()
    participantes_line = [l for l in linhas if 'Participantes' in l][0]
    data_line = [l for l in linhas if 'Data e Hora' in l][0]
    premio_line = [l for l in linhas if 'Prêmio' in l][0]
    
    limite_inscritos = int(re.search(r'Participantes \((\d+)\)', participantes_line).group(1))
    limite_reservas = int(re.search(r'Vagas Reserva \((\d+)\)', participantes_line).group(1))

    inscritos_str = "\n".join([f"- <@{uid}>" for uid in novos_inscritos]) if novos_inscritos else "Nenhuma inscrição."
    reservas_str = "\n".join([f"- <@{uid}>" for uid in novos_reservas]) if novos_reservas else "Nenhuma reserva."

    embed.description = (
        f"{participantes_line}\n\n"
        f"{data_line}\n\n"
        f"{premio_line}\n\n"
        f"**<a:SetaDireita:1418996596699566164> Inscritos ({len(novos_inscritos)}/{limite_inscritos}):**\n{inscritos_str}\n\n"
        f"**<a:SetaDireita:1418996596699566164> Reservas ({len(novos_reservas)}/{limite_reservas}):**\n{reservas_str}"
    )
    await message.edit(embed=embed)

# --- Views ---

class AcaoResultadoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Ganhamos", style=ButtonStyle.success, custom_id="acao_ganhamos")
    async def ganhamos(self, interaction: Interaction, button: ui.Button):
        if not has_permission(interaction.user):
            return await interaction.response.send_message("❌ Você não tem permissão para decidir o resultado.", ephemeral=True)
        
        embed = interaction.message.embeds[0]
        tipo_acao = embed.title.split(": ")[-1].strip("• ")
        embed.title = f"<a:check:1419191983674626168> • • AÇÃO VENCIDA: {tipo_acao} • • <a:check:1419191983674626168>"
        embed.color = discord.Color.green()
        for item in self.children: item.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("Resultado registrado como **VITÓRIA**.", ephemeral=True)

    @ui.button(label="Perdemos", style=ButtonStyle.danger, custom_id="acao_perdemos")
    async def perdemos(self, interaction: Interaction, button: ui.Button):
        if not has_permission(interaction.user):
            return await interaction.response.send_message("❌ Você não tem permissão para decidir o resultado.", ephemeral=True)
            
        embed = interaction.message.embeds[0]
        tipo_acao = embed.title.split(": ")[-1].strip("• ")
        embed.title = f"<a:deny:1419191992952553533> • • AÇÃO PERDIDA: {tipo_acao} • • <a:deny:1419191992952553533>"
        embed.color = discord.Color.red()
        for item in self.children: item.disabled = True
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("Resultado registrado como **DERROTA**.", ephemeral=True)

class AcaoInscricaoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @ui.button(label="Inscrever-se", style=ButtonStyle.primary, emoji="✍️", custom_id="inscrever_acao")
    async def inscrever(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        data = parse_embed_data(interaction.message.embeds[0])
        inscritos, limite_inscritos = data['inscritos'], data['limite_inscritos']
        reservas, limite_reservas = data['reservas'], data['limite_reservas']
        user_id = interaction.user.id

        if user_id in inscritos or user_id in reservas:
            return await interaction.followup.send("Você já está inscrito ou na reserva.", ephemeral=True)
        
        if len(inscritos) < limite_inscritos:
            inscritos.append(user_id)
            await interaction.followup.send("✅ Inscrição confirmada como participante!", ephemeral=True)
        elif len(reservas) < limite_reservas:
            reservas.append(user_id)
            await interaction.followup.send("✅ Vagas de participantes preenchidas. Você foi adicionado à reserva.", ephemeral=True)
        else:
            return await interaction.followup.send("❌ Todas as vagas de inscrição e reserva estão preenchidas.", ephemeral=True)
        
        await atualizar_embed_acao(interaction.message, inscritos, reservas)

    @ui.button(label="Sair", style=ButtonStyle.danger, custom_id="sair_acao")
    async def sair(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        data = parse_embed_data(interaction.message.embeds[0])
        inscritos, reservas = data['inscritos'], data['reservas']
        user_id = interaction.user.id
        promovido = None

        if user_id in inscritos:
            inscritos.remove(user_id)
            if reservas:
                promovido = reservas.pop(0)
                inscritos.append(promovido)
            await interaction.followup.send("Você saiu da lista de participantes.", ephemeral=True)
        elif user_id in reservas:
            reservas.remove(user_id)
            await interaction.followup.send("Você saiu da lista de reservas.", ephemeral=True)
        else:
            return await interaction.followup.send("Você não está inscrito nesta ação.", ephemeral=True)

        await atualizar_embed_acao(interaction.message, inscritos, reservas)

        if promovido:
            membro_promovido = interaction.guild.get_member(promovido)
            if membro_promovido:
                try:
                    await membro_promovido.send(
                        f"🎉 Você foi promovido da reserva para a lista de participantes!\n"
                        f"Clique aqui para ir para a ação: {interaction.message.jump_url}"
                    )
                except discord.Forbidden: pass

    @ui.button(label="Cancelar", style=ButtonStyle.secondary, emoji="✖️", custom_id="cancelar_acao")
    async def cancelar(self, interaction: Interaction, button: ui.Button):
        if not has_permission(interaction.user):
            return await interaction.response.send_message("❌ Você não tem permissão para cancelar a ação.", ephemeral=True)
        await interaction.message.delete()
        await interaction.response.send_message("Ação cancelada com sucesso.", ephemeral=True)
        
# --- Modal ---

class MarcarAcaoModal(ui.Modal, title="Marcar Nova Ação"):
    tipo_acao = ui.TextInput(label="Tipo de Ação", placeholder="Ex: Roubo ao Banco Central", required=True)
    participantes = ui.TextInput(label="Quantidade de Participantes", placeholder="Ex: 8", required=True)
    reservas = ui.TextInput(label="Quantidade de Reservas", placeholder="Ex: 2", required=True)
    data_hora = ui.TextInput(label="Data e Hora (DD/MM/AAAA HH:MM)", placeholder="Ex: 25/12/2025 21:30", required=True)
    premio = ui.TextInput(label="Prêmio", placeholder="Ex: R$ 5.000.000,00", required=True, style=TextStyle.paragraph)

    async def on_submit(self, interaction: Interaction):
        try:
            num_participantes = int(self.participantes.value)
            num_reservas = int(self.reservas.value)
        except ValueError:
            return await interaction.response.send_message("❌ A quantidade de participantes e reservas deve ser um número.", ephemeral=True)
        
        try:
            tz = pytz.timezone(module_config.FUSO_HORARIO)
            datetime.strptime(self.data_hora.value, '%d/%m/%Y %H:%M').astimezone(tz)
        except (ValueError, pytz.UnknownTimeZoneError):
            return await interaction.response.send_message(f"❌ Formato de data e hora inválido. Use `DD/MM/AAAA HH:MM` e verifique o fuso horário no config.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        embed = Embed(
            color=discord.Color.blue()
        )
        embed.description = (
            f"# <a:gun:1419161276759670924> • • AÇÃO MARCADA: {self.tipo_acao.value.upper()} • • <a:gun:1419161276759670924>\n\n"
            f"**<a:SetaDireita:1418996596699566164> Participantes ({num_participantes}) e Vagas Reserva ({num_reservas})**\n\n"
            f"**<a:SetaDireita:1418996596699566164> Data e Hora:** {self.data_hora.value}\n\n"
            f"**<a:SetaDireita:1418996596699566164> Prêmio:** {self.premio.value}\n\n"
            f"**<a:SetaDireita:1418996596699566164> Inscritos (0/{num_participantes}):**\nNenhuma inscrição.\n\n"
            f"**<a:SetaDireita:1418996596699566164> Reservas (0/{num_reservas}):**\nNenhuma reserva."
        )
        embed.set_footer(text=f"Ação marcada por: {interaction.user.display_name}")
        
        canal_acoes = interaction.guild.get_channel(module_config.ID_CANAL_ACOES)
        if canal_acoes:
            await canal_acoes.send(embed=embed, view=AcaoInscricaoView())
            await interaction.followup.send("✅ Ação marcada com sucesso!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Canal de ações não configurado.", ephemeral=True)
            
# --- Cog ---

class AcoesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_acoes.start()

    def cog_unload(self):
        self.check_acoes.cancel()

    @tasks.loop(minutes=1)
    async def check_acoes(self):
        await self.bot.wait_until_ready()
        
        canal_acoes = self.bot.get_channel(module_config.ID_CANAL_ACOES)
        if not canal_acoes: return
            
        try:
            tz = pytz.timezone(module_config.FUSO_HORARIO)
        except pytz.UnknownTimeZoneError:
            print(f"ERRO: Fuso horário '{module_config.FUSO_HORARIO}' inválido no config de ações.")
            return

        now = datetime.now(tz)
        
        async for message in canal_acoes.history(limit=50):
            if not message.embeds or message.author.id != self.bot.user.id:
                continue
            
            embed = message.embeds[0]
            if not embed.title.startswith("• • AÇÃO MARCADA:"):
                continue
            
            try:
                # CORREÇÃO: Extrai data e hora de forma segura
                data_hora_match = re.search(r"\*\*<a:SetaDireita:1418996596699566164> Data e Hora:\*\* (.*)", embed.description)
                if not data_hora_match:
                    continue
                
                action_time = datetime.strptime(data_hora_match.group(1), '%d/%m/%Y %H:%M').astimezone(tz)
                time_diff = action_time - now
                
                # Se a ação já passou, troca para a view de resultado
                if time_diff <= timedelta(seconds=0):
                    await message.edit(view=AcaoResultadoView())
                    continue

                # CORREÇÃO: Lógica de notificação robusta
                notificacao_enviada = embed.footer.text and "Notificação de 30min enviada" in embed.footer.text
                
                # Se a ação está a 30 minutos ou menos de começar E a notificação ainda não foi enviada
                if time_diff <= timedelta(minutes=30) and not notificacao_enviada:
                    data = parse_embed_data(embed)
                    for user_id in data['inscritos']:
                        member = canal_acoes.guild.get_member(user_id)
                        if member:
                            try:
                                await member.send(
                                    f"🔔 **AVISO:** A ação `{embed.title}` começará em 30 minutos!\n"
                                    f"Prepare-se! Vá para a ação: {message.jump_url}"
                                )
                            except discord.Forbidden:
                                pass
                    
                    # Marca a notificação como enviada no rodapé
                    original_footer = embed.footer.text if embed.footer.text else ""
                    embed.set_footer(text=f"{original_footer} | Notificação de 30min enviada.")
                    await message.edit(embed=embed)

            except (AttributeError, ValueError, TypeError):
                continue

    @commands.hybrid_command(name="painel_acao", description="Envia o painel para marcar ações.")
    @commands.has_permissions(manage_guild=True)
    async def painel_acao(self, ctx: commands.Context):
        if not has_permission(ctx.author):
            return await ctx.send("❌ Você não tem permissão para usar este comando.", ephemeral=True, delete_after=10)
            
        embed = Embed(
            description=(
                f"# <a:gun:1419161276759670924> MARCAR AÇÃO <a:gun:1419161276759670924>\n\n"
                f"`Clique no botão abaixo e preencha as informações:`\n\n"
                f"**<a:SetaDireita:1418996596699566164> Tipo de ação:**\n\n"
                f"**<a:SetaDireita:1418996596699566164> Quantidade de Participantes:**\n\n"
                f"**<a:SetaDireita:1418996596699566164> Quantidade de Reservas:**\n\n"
                f"**<a:SetaDireita:1418996596699566164> Data e Hora:**\n\n"
                f"**<a:SetaDireita:1418996596699566164> Prêmio:**"
            ),
            color=discord.Color.orange()
        )
        view = ui.View(timeout=None)
        view.add_item(ui.Button(label="Marcar Ação", emoji="🔫", custom_id="marcar_acao_btn", style=ButtonStyle.gray))
        
        target_channel = self.bot.get_channel(module_config.ID_CANAL_COMANDO) or ctx.channel
        await target_channel.send(embed=embed, view=view)
        
        if ctx.interaction:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message("Painel enviado!", ephemeral=True, delete_after=5)
            else:
                await ctx.interaction.followup.send("Painel enviado!", ephemeral=True, delete_after=5)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.data and interaction.data.get("custom_id") == "marcar_acao_btn":
            if not has_permission(interaction.user):
                return await interaction.response.send_message("❌ Você não tem permissão para marcar ações.", ephemeral=True)
            await interaction.response.send_modal(MarcarAcaoModal())

async def setup(bot):
    await bot.add_cog(AcoesCog(bot))
    bot.add_view(AcaoInscricaoView())
    bot.add_view(AcaoResultadoView())