# /server/funcionalidades/elite_test/elite_test.py

import discord
from discord import ui, Interaction, ButtonStyle, Embed, TextStyle
from discord.ext import commands
import asyncio
import traceback
import re
from . import config as module_config

# --- Funções Auxiliares ---

def tem_permissao(interaction: Interaction) -> bool:
    """Verifica se o usuário tem um dos cargos permitidos."""
    if not module_config.IDS_CARGOS_RESP_ELITE or all(cid == 0 for cid in module_config.IDS_CARGOS_RESP_ELITE):
        return interaction.user.guild_permissions.administrator
        
    ids_cargos_permitidos = set(module_config.IDS_CARGOS_RESP_ELITE)
    ids_cargos_usuario = {role.id for role in interaction.user.roles}
    return not ids_cargos_usuario.isdisjoint(ids_cargos_permitidos)

def parse_inscritos_from_embed(embed: discord.Embed) -> list[int]:
    """Extrai os IDs dos usuários inscritos a partir da descrição da embed."""
    if not embed.description:
        return []
    # Encontra todos os padrões de menção de usuário e extrai os IDs
    user_ids = re.findall(r'<@(\d+)>', embed.description)
    return [int(uid) for uid in user_ids]

async def atualizar_embed_inscritos(message: discord.Message, inscritos: list[int]):
    """Atualiza a embed com a lista de inscritos."""
    embed = message.embeds[0]
    linhas = embed.description.splitlines()
    data_e_horario = [linha for linha in linhas if "Data:" in linha or "Horário:" in linha]

    inscritos_str = "\n".join([f"- <@{user_id}>" for user_id in inscritos])
    if not inscritos_str:
        inscritos_str = "Nenhum inscrito ainda."

    embed.description = f"{data_e_horario[0]}\n{data_e_horario[1]}\n\n**Inscritos:**\n{inscritos_str}"
    await message.edit(embed=embed)

async def _enviar_dms_cancelamento_task(guild: discord.Guild, inscritos_ids: list[int], data: str, horario: str):
    """Tarefa em segundo plano para enviar DMs de cancelamento."""
    for user_id in inscritos_ids:
        member = guild.get_member(user_id)
        if member:
            try:
                await member.send(f"O teste de elite do dia {data} às {horario} foi cancelado.")
            except (discord.Forbidden, discord.HTTPException):
                pass # Ignora se não puder enviar DM
        await asyncio.sleep(1)


# --- Views dos Botões ---

class TesteEliteIniciadoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Finalizar", style=ButtonStyle.success, emoji="🏆", custom_id="finalizar_elite")
    async def finalizar(self, interaction: Interaction, button: ui.Button):
        if not tem_permissao(interaction):
            return await interaction.response.send_message("❌ Apenas um **RESP ELITE** pode finalizar o teste.", ephemeral=True)

        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.description = "# <a:check:1419191983674626168> • • TESTE DE ELITE CONCLUÍDO • • <a:check:1419191983674626168>\n\n"
        embed.color = discord.Color.greyple()

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("O teste de elite foi finalizado com sucesso!", ephemeral=True)

    @ui.button(label="Reinscrição", style=ButtonStyle.primary, emoji="🔄", custom_id="reinscricao_elite")
    async def reinscricao(self, interaction: Interaction, button: ui.Button):
        if not tem_permissao(interaction):
            return await interaction.response.send_message("❌ Apenas um **RESP ELITE** pode reabrir as inscrições.", ephemeral=True)
        
        view_inscricao = TesteEliteInscricaoView()
        await interaction.message.edit(view=view_inscricao)
        await interaction.response.send_message("As inscrições foram reabertas.", ephemeral=True)


class TesteEliteInscricaoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Inscrever-se", style=ButtonStyle.primary, emoji="✍️", custom_id="inscrever_elite")
    async def inscrever_se(self, interaction: Interaction, button: ui.Button):
        inscritos = parse_inscritos_from_embed(interaction.message.embeds[0])
        if interaction.user.id not in inscritos:
            inscritos.append(interaction.user.id)
            await atualizar_embed_inscritos(interaction.message, inscritos)
            await interaction.response.send_message("Você se inscreveu no teste de elite!", ephemeral=True)
        else:
            await interaction.response.send_message("Você já está inscrito.", ephemeral=True)

    @ui.button(label="Sair", style=ButtonStyle.danger, custom_id="sair_elite")
    async def sair(self, interaction: Interaction, button: ui.Button):
        inscritos = parse_inscritos_from_embed(interaction.message.embeds[0])
        if interaction.user.id in inscritos:
            inscritos.remove(interaction.user.id)
            await atualizar_embed_inscritos(interaction.message, inscritos)
            await interaction.response.send_message("Você saiu da lista de inscritos.", ephemeral=True)
        else:
            await interaction.response.send_message("Você não está na lista de inscritos.", ephemeral=True)

    @ui.button(label="Iniciar", style=ButtonStyle.secondary, custom_id="iniciar_elite")
    async def iniciar(self, interaction: Interaction, button: ui.Button):
        if not tem_permissao(interaction):
            return await interaction.response.send_message("❌ Apenas um **RESP ELITE** pode iniciar o teste.", ephemeral=True)
            
        view_iniciado = TesteEliteIniciadoView()
        await interaction.message.edit(view=view_iniciado)
        await interaction.response.send_message("O teste de elite foi iniciado!", ephemeral=True)

    @ui.button(label="Cancelar", style=ButtonStyle.secondary, custom_id="cancelar_elite")
    async def cancelar(self, interaction: Interaction, button: ui.Button):
        if not tem_permissao(interaction):
            return await interaction.response.send_message("❌ Apenas um **RESP ELITE** pode cancelar o teste.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = interaction.message.embeds[0]
            linhas = embed.description.splitlines()
            data = [l.split("**Data:**")[1].strip() for l in linhas if l.startswith("**Data:**")][0]
            horario = [l.split("**Horário:**")[1].strip() for l in linhas if l.startswith("**Horário:**")][0]
            
            inscritos_para_notificar = parse_inscritos_from_embed(embed)

            asyncio.create_task(
                _enviar_dms_cancelamento_task(interaction.guild, inscritos_para_notificar, data, horario)
            )

            await interaction.message.delete()
            await interaction.followup.send("✅ Teste cancelado! Os inscritos estão sendo notificados.", ephemeral=True)

        except Exception:
            traceback.print_exc()
            await interaction.followup.send("❌ Ocorreu um erro ao processar o cancelamento.", ephemeral=True)


# --- Modal e Cog Principal ---

class TesteEliteModal(ui.Modal, title="Abrir Teste para a Elite"):
    data = ui.TextInput(label="Data", placeholder="Exemplo: 01/01/2025", required=True)
    horario = ui.TextInput(label="Horário", placeholder="Exemplo: 23:00", required=True)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = Embed(description=(
                            "# <a:gun:1419161276759670924> • • TESTE DA ELITE ABERTO • • <a:gun:1419161276759670924>\n\n"
                            f"**Data:** {self.data.value}\n**Horário:** {self.horario.value}\n\n**Inscritos:**\nNenhum inscrito ainda."
                        ),
                      color=discord.Color.gold())
        canal_testes = interaction.guild.get_channel(module_config.ID_CANAL_TESTES)
        if canal_testes:
            await canal_testes.send(embed=embed, view=TesteEliteInscricaoView())
            await interaction.followup.send("Teste de elite aberto com sucesso!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Erro: Canal de testes não configurado.", ephemeral=True)


class EliteTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="teste_elite", description="Envia o painel para abrir um teste de elite.")
    @commands.has_permissions(manage_guild=True)
    async def teste_elite(self, ctx: commands.Context):
        target_channel_id = module_config.ID_CANAL_COMANDO
        target_channel = ctx.guild.get_channel(target_channel_id) if target_channel_id != 0 else ctx.channel

        embed = Embed(description=("# <a:gun:1419161276759670924> • • TESTE PARA A ELITE • • <a:gun:1419161276759670924>\n\n"
                                    "<a:SetaDireita:1418996596699566164> Clique no botão abaixo para abrir um **TESTE ELITE.**\n\n"
                                    "<a:SetaDireita:1418996596699566164> Apenas um **RESP ELITE** pode abrir um novo teste."),
                      color=discord.Color.gold())
        view = ui.View(timeout=None)
        view.add_item(ui.Button(label="Abrir TESTE elite", style=ButtonStyle.gray, emoji="🔫", custom_id="abrir_teste_elite"))
        await target_channel.send(embed=embed, view=view)
        
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.interaction.response.send_message("Painel enviado!", ephemeral=True, delete_after=5)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "abrir_teste_elite":
            if tem_permissao(interaction):
                await interaction.response.send_modal(TesteEliteModal())
            else:
                await interaction.response.send_message("❌ Apenas um **RESP ELITE** pode abrir um novo teste.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EliteTestCog(bot))
    bot.add_view(TesteEliteInscricaoView())
    bot.add_view(TesteEliteIniciadoView())