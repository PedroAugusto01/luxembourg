# /server/funcionalidades/licenca/licenca.py

import discord
from discord import ui, Interaction, ButtonStyle, Embed
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import re
import json
import os
from . import config as module_config
from config import config as global_config

# --- Lógica de Armazenamento em JSON ---
def load_licenses():
    file_path = module_config.NOME_ARQUIVO_LICENCAS
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_licenses(data):
    file_path = module_config.NOME_ARQUIVO_LICENCAS
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# --- Funções de Data ---
def parse_duration(duration_str: str):
    """Analisa a string de duração e retorna a data de expiração."""
    now = datetime.now()
    
    days_match = re.match(r'(\d+)\s*dias?', duration_str, re.IGNORECASE)
    if days_match:
        days = int(days_match.group(1))
        return now + timedelta(days=days + 1)

    range_match = re.match(r'(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})', duration_str, re.IGNORECASE)
    if range_match:
        end_date_str = range_match.group(2)
        return datetime.strptime(end_date_str, '%d/%m/%Y') + timedelta(days=1)

    return None

# --- Modal de Justificativa ---
class LicencaModal(ui.Modal, title="📝 Justificar Licença"):
    id_jogo = ui.TextInput(label="Seu ID no Jogo (Passaporte)", placeholder="Apenas os números", required=True)
    duracao = ui.TextInput(label="Duração da Licença", placeholder="Ex: '7 dias' ou '01/01/2025 a 15/01/2025'", required=True)
    motivo = ui.TextInput(label="Motivo da Licença", style=discord.TextStyle.paragraph, placeholder="Seja breve e claro.", required=True)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        expiry_date = parse_duration(self.duracao.value)
        if not expiry_date:
            await interaction.followup.send("❌ Formato de data/duração inválido. Use 'X dias' ou 'DD/MM/AAAA a DD/MM/AAAA'.", ephemeral=True)
            return

        member = interaction.user
        reason_text = f"Licença justificada. Motivo: {self.motivo.value}"

        # --- Adicionar Cargos de Licença ---
        roles_to_add_ids = module_config.IDS_CARGOS_ADICIONAR
        roles_to_add = [interaction.guild.get_role(role_id) for role_id in roles_to_add_ids if role_id != 0]
        roles_to_add = [role for role in roles_to_add if role]

        if not roles_to_add:
            await interaction.followup.send("⚠️ Nenhum cargo de licença para adicionar foi configurado. Contate um administrador.", ephemeral=True)
            return

        try:
            await member.add_roles(*roles_to_add, reason=reason_text)
        except discord.Forbidden:
            await interaction.followup.send("❌ Erro de permissão ao tentar adicionar o cargo de licença. Contate um administrador.", ephemeral=True)
            return

        # --- Salvar Licença para processamento futuro ---
        licenses = load_licenses()
        user_id_str = str(member.id)
        licenses[user_id_str] = {
            "expiry_timestamp": expiry_date.timestamp(),
            "added_roles": [role.id for role in roles_to_add],
            "roles_to_remove_on_expiry": module_config.IDS_CARGOS_REMOVER,
        }
        save_licenses(licenses)

        # --- Enviar Log ---
        log_channel = interaction.guild.get_channel(module_config.ID_CANAL_LOGS)
        if log_channel:
            embed_log = Embed(
                title="📝 Nova Justificativa de Licença",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed_log.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
            embed_log.add_field(name="👤 Solicitante", value=member.mention, inline=False)
            embed_log.add_field(name="🔢 ID no Jogo", value=self.id_jogo.value, inline=False)
            embed_log.add_field(name="📅 Duração", value=self.duracao.value, inline=False)
            embed_log.add_field(name="📄 Motivo", value=self.motivo.value, inline=False)
            embed_log.set_footer(text=f"ID do Solicitante: {member.id}")
            
            await log_channel.send(embed=embed_log)

        await interaction.followup.send("✅ Sua licença foi justificada com sucesso!", ephemeral=True)


# --- View do Botão Inicial ---
class LicencaButtonView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Justificar Licença", style=ButtonStyle.primary, custom_id="justificar_licenca_btn", emoji="📝")
    async def justificar_licenca(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(LicencaModal())


# --- Cog e Comando ---
class Licenca(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_expired_licenses.start()

    def cog_unload(self):
        self.check_expired_licenses.cancel()

    @commands.hybrid_command(name="licenca", description="Envia o painel para justificar licença.")
    @commands.has_permissions(manage_guild=True)
    async def licenca(self, ctx: commands.Context):
        if ctx.channel.id != module_config.ID_CANAL_COMANDO:
            return

        embed = Embed(
            title="📋 Central de Licenças",
            description=(
                "Precisa se ausentar por um período?\n\n"
                "Para garantir que sua situação seja registrada corretamente, clique no botão abaixo para preencher o formulário de licença.\n\n"
                "Sua ausência será justificada e os cargos adequados serão aplicados durante o período informado."
            ),
            color=discord.Color.from_rgb(88, 101, 242)
        )
        embed.set_footer(text="Agradecemos sua responsabilidade e cooperação.")
        
        await ctx.send(embed=embed, view=LicencaButtonView())
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    @tasks.loop(hours=1)
    async def check_expired_licenses(self):
        await self.bot.wait_until_ready()
        
        licenses = load_licenses()
        now = datetime.now().timestamp()
        expired_users_ids = [uid for uid, data in licenses.items() if data["expiry_timestamp"] < now]
        
        if not expired_users_ids:
            return

        guild = self.bot.get_guild(global_config.ID_SERVIDOR)
        if not guild: return

        for user_id_str in expired_users_ids:
            member = guild.get_member(int(user_id_str))
            license_data = licenses[user_id_str]
            
            if member:
                # Junta todos os cargos que precisam ser removidos no final da licença
                all_role_ids_to_remove = license_data.get("added_roles", []) + license_data.get("roles_to_remove_on_expiry", [])
                
                # Converte IDs em objetos de cargo, filtrando os nulos e duplicatas
                roles_to_remove = {guild.get_role(role_id) for role_id in all_role_ids_to_remove if role_id != 0}
                roles_to_remove = {role for role in roles_to_remove if role}
                
                if roles_to_remove:
                    try:
                        await member.remove_roles(*roles_to_remove, reason="Licença finalizada.")
                        print(f"[{global_config.CONTEXTO}] Cargos da licença de {member.name} removidos.")
                    except discord.Forbidden:
                         print(f"[{global_config.CONTEXTO}] ERRO: Sem permissão para remover cargos de {member.name} após licença.")
                    except Exception as e:
                         print(f"[{global_config.CONTEXTO}] ERRO ao remover cargos de {member.name}: {e}")

            # Remove a licença do arquivo após o processamento
            del licenses[user_id_str]
        
        save_licenses(licenses)
        if expired_users_ids:
            print(f"[{global_config.CONTEXTO}] Verificação de licenças concluída. {len(expired_users_ids)} licença(s) processada(s).")


async def setup(bot):
    bot.add_view(LicencaButtonView())
    await bot.add_cog(Licenca(bot))