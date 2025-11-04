import discord
from discord.ext import commands
from discord import ui, ButtonStyle
from . import config as module_config # Carrega o config.py local
from config import config as global_config # Carrega o config.py global
import re

# --- Funções e Classes do Módulo ---

def extract_name_and_id(display_name: str, fallback_name: str, message_content: str):
    """Extrai nome e ID, com lógica corrigida e rigorosa."""
    game_id = "N/A"
    
    id_match_in_message = re.search(r'ID:\s*(\d+)', message_content, re.IGNORECASE)
    
    if id_match_in_message:
        game_id = id_match_in_message.group(1)
    else:
        id_match_in_name = re.search(r'\d{2,}', display_name)
        if id_match_in_name:
            game_id = id_match_in_name.group(0)

    clean_name = re.sub(r'\[.*?\]|\(.*?\)|\d', '', display_name).strip()
    first_name = clean_name.split()[0] if clean_name else fallback_name
    
    return first_name, game_id

async def apply_nickname(member: discord.Member, new_nickname: str, reason: str) -> bool:
    """Aplica o novo apelido ao membro e retorna True se houve mudança."""
    if member.nick == new_nickname:
        return False # Nenhuma mudança necessária
        
    if len(new_nickname) > 32:
        new_nickname = new_nickname[:32]
        
    await member.edit(nick=new_nickname, reason=reason)
    return True

async def format_and_set_nickname(member: discord.Member, role: discord.Role, game_id: str) -> bool:
    """Formata e define o apelido, retornando True se a mudança foi aplicada."""
    nick_per_role_config = module_config.CARGO_POR_MENSAGEM_NICKNAME
    nick_fixed_config = module_config.NICKNAME_FIXED_FORMAT_CONFIG
    
    clean_name = re.sub(r'\[.*?\]|\(.*?\)|\d', '', member.display_name).strip()
    first_name = clean_name.split()[0] if clean_name else member.name
    
    new_nickname = None

    if nick_per_role_config.get("ativado", False):
        format_config = nick_per_role_config.get("formatos_por_cargo", {}).get(role.id)
        if format_config:
            tag = format_config.get("tag", "")
            formato = format_config.get("formato", "{NOME} | {ID}")
            new_nickname = formato.format(TAG=tag, NOME=first_name, ID=game_id)
            
    elif nick_fixed_config.get("ativado", False):
        formato = nick_fixed_config.get("formato_fixo")
        if formato:
            new_nickname = formato.format(NOME=first_name, ID=game_id)

    if new_nickname:
        return await apply_nickname(member, new_nickname, f"Apelido atualizado pelo cargo '{role.name}'.")
    return False

# --- Views e Modals para Interação ---

class AddIdModal(ui.Modal, title="Adicionar ID Manualmente"):
    id_input = ui.TextInput(label="ID do Jogo", placeholder="Digite aqui o ID numérico...", required=True)

    def __init__(self, member: discord.Member, role: discord.Role, original_interaction: discord.Interaction):
        super().__init__()
        self.member = member
        self.role = role
        self.original_interaction = original_interaction

    async def on_submit(self, interaction: discord.Interaction):
        game_id = self.id_input.value
        await format_and_set_nickname(self.member, self.role, game_id)
        await interaction.response.send_message(f"✅ Apelido de {self.member.mention} atualizado com o ID `{game_id}`!", ephemeral=True, delete_after=10)
        await self.original_interaction.delete_original_response()

class ConfirmNoIdView(ui.View):
    def __init__(self, member: discord.Member, role: discord.Role, author_id: int):
        super().__init__(timeout=180)
        self.member = member
        self.role = role
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message("Apenas o autor da solicitação pode usar estes botões.", ephemeral=True)
        return False

    async def disable_and_delete(self, interaction: discord.Interaction):
        for item in self.children: item.disabled = True
        await interaction.message.delete()

    @ui.button(label="Continuar sem ID", style=ButtonStyle.secondary, emoji="➡️")
    async def continue_callback(self, interaction: discord.Interaction, button: ui.Button):
        await format_and_set_nickname(self.member, self.role, "N/A")
        await interaction.response.send_message(f"✅ Apelido de {self.member.mention} atualizado sem ID.", ephemeral=True, delete_after=10)
        await self.disable_and_delete(interaction)

    @ui.button(label="Adicionar ID", style=ButtonStyle.primary, emoji="✍️")
    async def add_id_callback(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AddIdModal(self.member, self.role, interaction))
        await self.disable_and_delete(interaction)

# --- Cog Principal ---
class DynamicRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.main_config = module_config.CARGO_POR_MENSAGEM_CONFIG
        self.nick_id_confirm_config = module_config.NICKNAME_ID_CONFIRMATION

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (message.author.bot or not message.guild or 
            message.channel.id != self.main_config.get("id_canal_observado")):
            return
        
        if not message.mentions or not message.role_mentions:
            return

        target_member = next((m for m in message.mentions if not m.bot), None)
        target_roles = message.role_mentions

        if not target_member or not target_roles:
            return
        
        try:
            action_was_performed = False

            # 1. Adiciona cargos, se necessário
            roles_to_add = [role for role in target_roles if role not in target_member.roles]
            if roles_to_add:
                await target_member.add_roles(*roles_to_add, reason="Cargo(s) concedido(s) dinamicamente.")
                action_was_performed = True
            
            # 2. Tenta mudar o apelido, se ativado
            nickname_change_enabled = module_config.CARGO_POR_MENSAGEM_NICKNAME.get("ativado") or module_config.NICKNAME_FIXED_FORMAT_CONFIG.get("ativado")
            if nickname_change_enabled:
                first_role = target_roles[0]
                _, game_id = extract_name_and_id(target_member.display_name, target_member.name, message.content)
                
                if game_id == "N/A" and self.nick_id_confirm_config.get("ativado"):
                    embed = discord.Embed(
                        title="⚠️ Confirmação Necessária",
                        description=f"Nenhum ID de jogo foi encontrado para **{target_member.display_name}**. Como deseja prosseguir?",
                        color=discord.Color.orange()
                    )
                    await message.channel.send(content=f"{message.author.mention}, ação necessária:", embed=embed, view=ConfirmNoIdView(target_member, first_role, message.author.id), delete_after=180.0)
                    await message.add_reaction("❓")
                    return # Ação de confirmação é separada, então paramos aqui.
                else:
                    # A função agora retorna True se o apelido realmente mudou
                    nickname_was_changed = await format_and_set_nickname(target_member, first_role, game_id)
                    if nickname_was_changed:
                        action_was_performed = True

            # 3. Reage com base no resultado final
            if action_was_performed:
                await message.add_reaction("✅")
            else:
                await message.add_reaction("⚠️")

        except discord.Forbidden:
            await message.add_reaction("❌")
        except Exception as e:
            print(f"[{global_config.CONTEXTO}] ERRO (Cargo Dinâmico): {e}")
            await message.add_reaction("❌")

async def setup(bot):
    await bot.add_cog(DynamicRole(bot))