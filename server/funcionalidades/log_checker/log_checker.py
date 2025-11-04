# /server/funcionalidades/log_checker/log_checker.py

import discord
from discord import ui, app_commands, Embed, TextStyle
from discord.ext import commands
import aiohttp
from datetime import datetime
from typing import Optional
import json
import re
import math
from . import config as module_config

# --- Funções Auxiliares ---
def parse_revived_id(contents: str) -> str:
    match = re.search(r'\[REVIVEU\]:\s*(\d+)', contents)
    return match.group(1) if match else "N/A"

def parse_cds(contents: str) -> str:
    match = re.search(r'\[CDS\]:\s*(vec3\(.*?\))', contents)
    return match.group(1) if match else "N/A"

def format_date(date_str: str) -> str:
    """Converte a data do formato AAAA-MM-DD HH:MM:SS para DD-MM-AAAA | HH:MM:SS."""
    if not date_str or date_str == "N/A":
        return "N/A"
    try:
        dt_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return dt_obj.strftime('%d-%m-%Y | %H:%M:%S')
    except (ValueError, TypeError):
        return date_str # Retorna o original se o formato for inesperado

def create_detailed_embed(log: dict) -> Embed:
    embed = Embed(color=discord.Color.from_rgb(88, 101, 242))
    embed.description = (
        f"**[ID]**: `{log.get('player_id', 'N/A')}` {log.get('player_name', 'N/A')}\n"
        f"**[SOURCE]**: `{log.get('source', 'N/A')}`\n\n"
        f"**[{log.get('sala', 'N/A')}]**\n"
        f"**[REVIVEU]**: `{parse_revived_id(log.get('contents', ''))}`\n"
        f"**[CDS]**: `{parse_cds(log.get('contents', ''))}`\n\n"
        f"**[DATA]**: `{format_date(log.get('date', 'N/A'))}`"
    )
    return embed

# --- Componentes da Interface ---

class SaveLogView(ui.View):
    def __init__(self, detailed_embed: Embed):
        super().__init__(timeout=180)
        self.detailed_embed = detailed_embed

    @ui.button(label="Salvar Log", style=discord.ButtonStyle.success, emoji="💾")
    async def save_log(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=False)
        log_channel = interaction.guild.get_channel(module_config.ID_CANAL_SALVAR_LOGS)
        if not log_channel:
            await interaction.followup.send("❌ Canal de salvamento não encontrado.", ephemeral=True)
            return
        try:
            await log_channel.send(embed=self.detailed_embed)
            button.disabled = True
            button.label = "Salvo com Sucesso"
            await interaction.edit_original_response(view=self)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao salvar log: {e}", ephemeral=True)

class LogSelect(ui.Select):
    def __init__(self, logs_data: list, options: list):
        super().__init__(placeholder="Selecione um log para ver os detalhes...", options=options)
        self.logs_data = logs_data

    async def callback(self, interaction: discord.Interaction):
        selected_index = int(self.values[0])
        log = self.logs_data[selected_index]
        detailed_embed = create_detailed_embed(log)
        await interaction.response.edit_message(embed=detailed_embed, view=SaveLogView(detailed_embed))

class LogPaginatorView(ui.View):
    """View que gerencia a paginação do menu de seleção."""
    def __init__(self, logs_data: list, user: discord.Member):
        super().__init__(timeout=300)
        self.logs_data = logs_data
        self.user = user
        self.current_page = 0
        self.items_per_page = 25
        self.total_pages = math.ceil(len(self.logs_data) / self.items_per_page)
        self.update_components()

    def get_options_for_page(self) -> list[discord.SelectOption]:
        """Cria as opções do menu para a página atual."""
        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page
        
        return [
            discord.SelectOption(
                label=f"{format_date(log.get('date', 'Data Desconhecida'))}",
                description=f"ID: {log.get('player_id', 'N/A')} | Reviveu: {parse_revived_id(log.get('contents', ''))}",
                value=str(start_index + i) # O valor é o índice global do log
            ) for i, log in enumerate(self.logs_data[start_index:end_index])
        ]

    def update_components(self):
        """Limpa e recria os componentes da view (menu e botões)."""
        self.clear_items()
        
        # Recria o menu de seleção para a página atual
        options = self.get_options_for_page()
        self.add_item(LogSelect(logs_data=self.logs_data, options=options))

        # Recria os botões de paginação
        prev_button = ui.Button(label="< Anterior", style=discord.ButtonStyle.secondary, disabled=(self.current_page == 0))
        next_button = ui.Button(label="Próximo >", style=discord.ButtonStyle.secondary, disabled=(self.current_page >= self.total_pages - 1))
        
        prev_button.callback = self.go_to_previous_page
        next_button.callback = self.go_to_next_page
        
        self.add_item(prev_button)
        self.add_item(next_button)

    async def go_to_previous_page(self, interaction: discord.Interaction):
        self.current_page -= 1
        self.update_components()
        await interaction.response.edit_message(view=self)

    async def go_to_next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        self.update_components()
        await interaction.response.edit_message(view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Você não pode interagir com a busca de outra pessoa.", ephemeral=True)
            return False
        return True

class LogSearchModal(ui.Modal, title="Buscar Logs"):
    data_inicio = ui.TextInput(label="Data de Início (DD/MM/AAAA)", placeholder="Ex: 01/08/2025")
    data_fim = ui.TextInput(label="Data de Fim (DD/MM/AAAA)", placeholder="Ex: 22/08/2025")
    jogador_id = ui.TextInput(label="ID do Jogador (Opcional)", required=False)
    termo = ui.TextInput(label="Termo da Ação (Opcional)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            start_date = datetime.strptime(self.data_inicio.value, "%d/%m/%Y").replace(hour=0, minute=0, second=0)
            end_date = datetime.strptime(self.data_fim.value, "%d/%m/%Y").replace(hour=23, minute=59, second=59)
            date_param_1 = start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            date_param_2 = end_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        except ValueError:
            await interaction.followup.send("❌ Formato de data inválido.", ephemeral=True)
            return
        
        params = {"s": "MEDICO-TRATAMENTO", "dates[0]": date_param_1, "dates[1]": date_param_2, "i": self.jogador_id.value or "", "a": self.termo.value or ""}
        headers = {"Cookie": module_config.COOKIE}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(module_config.API_BASE_URL, params=params) as response:
                if response.status == 200:
                    raw_text = await response.text()
                    lines = raw_text.strip().split('\n')
                    logs_data = [json.loads(line[len("data: "):]) for line in lines if line.startswith("data: ") and "fim-da-stream" not in line]
                    
                    if not logs_data:
                        await interaction.followup.send("ℹ️ Nenhuma informação encontrada.", ephemeral=True)
                        return
                    
                    embed = Embed(title=f"🔎 {len(logs_data)} Logs Encontrados", description="Selecione um log no menu para ver detalhes.", color=discord.Color.blue())
                    await interaction.followup.send(embed=embed, view=LogPaginatorView(logs_data, interaction.user), ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Erro ao consultar a API: `{response.status}`", ephemeral=True)

class LogPanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @ui.button(label="Puxar Logs", style=discord.ButtonStyle.primary, custom_id="puxar_logs_btn", emoji="🔍")
    async def puxar_logs(self, interaction: discord.Interaction, button: ui.Button):
        cargo_permitido = interaction.guild.get_role(module_config.ID_CARGO_PERMITIDO)
        if not cargo_permitido or interaction.user.top_role.position < cargo_permitido.position:
            await interaction.response.send_message("❌ Você não tem permissão para usar esta função.", ephemeral=True)
            return
        await interaction.response.send_modal(LogSearchModal())

class LogChecker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.hybrid_command(name="setup_logs", description="Envia o painel de busca de logs.")
    @commands.has_permissions(administrator=True)
    async def setup_logs(self, ctx: commands.Context):
        target_channel = self.bot.get_channel(module_config.ID_CANAL_PAINEL)
        if not target_channel:
            await ctx.send("❌ Canal do painel não configurado.", ephemeral=True)
            return
        embed = Embed(title="Painel de Controle de Logs", description="Clique no botão para iniciar uma busca.", color=discord.Color.from_rgb(47, 49, 54))
        await target_channel.send(embed=embed, view=LogPanelView())
        await ctx.send("✅ Painel enviado com sucesso!", ephemeral=True)
        if ctx.interaction is None:
            try: await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound): pass

async def setup(bot):
    bot.add_view(LogPanelView())
    await bot.add_cog(LogChecker(bot))