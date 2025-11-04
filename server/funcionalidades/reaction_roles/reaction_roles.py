import discord
from discord.ext import commands
from . import config as module_config # Carrega o config.py local
from config import config as global_config # Carrega o config.py global
import json
import os

# --- Lógica de Armazenamento em Arquivo JSON ---
def load_reaction_roles():
    """Carrega as configurações do arquivo JSON definido no config.py."""
    file_path = module_config.REACTION_ROLES_FILE
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_reaction_roles(data):
    """Salva as configurações no arquivo JSON."""
    file_path = module_config.REACTION_ROLES_FILE
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


# --- Cog Principal ---
class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reaction_config = load_reaction_roles()

    # --- Verificação de Permissão Customizada ---
    async def cog_check(self, ctx: commands.Context):
        """Verifica se o autor do comando tem o cargo necessário."""
        if ctx.interaction:
            return True

        manager_role_id = module_config.ID_CARGO_GERENCIAR_REACTION_ROLES
        if manager_role_id == 0:
            return await ctx.bot.is_owner(ctx.author) or ctx.author.guild_permissions.administrator
            
        manager_role = ctx.guild.get_role(manager_role_id)
        if not manager_role:
            return False
            
        return ctx.author.top_role.position >= manager_role.position

    async def handle_reaction(self, payload: discord.RawReactionActionEvent, *, add_role: bool):
        """Função central que lida com adição e remoção de reações."""
        if payload.user_id == self.bot.user.id: return

        message_id_str = str(payload.message_id)
        if message_id_str not in self.reaction_config: return

        emoji = str(payload.emoji)
        role_id = self.reaction_config[message_id_str].get(emoji)
        if not role_id: return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        
        member = guild.get_member(payload.user_id)
        if not member: return

        role = guild.get_role(role_id)
        if not role: return

        try:
            if add_role:
                if role not in member.roles:
                    await member.add_roles(role, reason="Cargo por reação")
                    # Envia a mensagem de confirmação
                    await member.send(f"✅ Você recebeu o cargo **`{role.name}`** no servidor **{guild.name}**.")
            else:
                if role in member.roles:
                    await member.remove_roles(role, reason="Cargo por reação")
                    # Envia a mensagem de confirmação
                    await member.send(f"❌ O cargo **`{role.name}`** foi removido de você no servidor **{guild.name}**.")
        except discord.Forbidden:
            # Não envia DM se não tiver permissão para gerenciar o cargo, para evitar spam de erro
            print(f"[{global_config.CONTEXTO}] ERRO (Reaction Role): Sem permissão para gerenciar o cargo '{role.name}'.")
        except discord.HTTPException:
            # Ignora erros de DM (ex: se o usuário tiver DMs desativadas)
            pass
        except Exception as e:
            print(f"[{global_config.CONTEXTO}] ERRO (Reaction Role): {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.handle_reaction(payload, add_role=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.handle_reaction(payload, add_role=False)

    # --- Comandos de Gerenciamento Híbridos ---
    
    @commands.hybrid_group(name="reactionrole", description="Gerencia o sistema de cargos por reação.")
    @commands.has_permissions(manage_roles=True)
    async def reactionrole_group(self, ctx: commands.Context):
        """Comando base para o sistema de cargos por reação."""
        await ctx.send("Comando inválido. Use `!reactionrole add`, `!reactionrole edit`, ou `!reactionrole delete`.", ephemeral=True, delete_after=10)

    @reactionrole_group.command(name="add", description="Adiciona uma nova configuração de cargo por reação.")
    async def add_reaction_role(self, ctx: commands.Context, message_id: str, emoji: str, role: discord.Role):
        """Adiciona uma nova configuração de cargo por reação."""
        if not message_id.isdigit():
            return await ctx.send("❌ O ID da mensagem deve ser um número.", ephemeral=True, delete_after=10)
            
        try:
            target_message = await ctx.channel.fetch_message(int(message_id))
        except discord.NotFound:
            return await ctx.send("❌ Mensagem não encontrada neste canal.", ephemeral=True, delete_after=10)
        
        current_config = load_reaction_roles()
        
        if message_id not in current_config:
            current_config[message_id] = {}
        current_config[message_id][emoji] = role.id
        
        save_reaction_roles(current_config)
        self.reaction_config = current_config
        
        try:
            await target_message.add_reaction(emoji)
        except discord.HTTPException:
            return await ctx.send("❌ Emoji inválido.", ephemeral=True, delete_after=10)

        await ctx.send(f"✅ **Configuração Salva!**\nReagir com {emoji} agora concede o cargo `{role.name}`.", ephemeral=True)
        if not ctx.interaction: await ctx.message.delete()

    @reactionrole_group.command(name="edit", description="Edita o cargo associado a uma reação existente.")
    async def edit_reaction_role(self, ctx: commands.Context, message_id: str, emoji: str, new_role: discord.Role):
        """Edita o cargo associado a uma reação existente."""
        if not message_id.isdigit():
            return await ctx.send("❌ O ID da mensagem deve ser um número.", ephemeral=True, delete_after=10)

        current_config = load_reaction_roles()
        if message_id not in current_config or emoji not in current_config[message_id]:
            return await ctx.send("❌ Nenhuma configuração encontrada para esta mensagem e emoji.", ephemeral=True, delete_after=10)

        current_config[message_id][emoji] = new_role.id
        save_reaction_roles(current_config)
        self.reaction_config = current_config
        
        await ctx.send(f"✅ **Configuração Editada!**\nReagir com {emoji} agora concede o novo cargo `{new_role.name}`.", ephemeral=True)
        if not ctx.interaction: await ctx.message.delete()

    @reactionrole_group.command(name="delete", description="Remove uma configuração de cargo por reação.")
    async def delete_reaction_role(self, ctx: commands.Context, message_id: str, emoji: str):
        """Remove uma configuração de cargo por reação."""
        if not message_id.isdigit():
            return await ctx.send("❌ O ID da mensagem deve ser um número.", ephemeral=True, delete_after=10)
        
        current_config = load_reaction_roles()
        if message_id not in current_config or emoji not in current_config[message_id]:
            return await ctx.send("❌ Nenhuma configuração encontrada para esta mensagem e emoji.", ephemeral=True, delete_after=10)
            
        del current_config[message_id][emoji]
        
        if not current_config[message_id]:
            del current_config[message_id]
            
        save_reaction_roles(current_config)
        self.reaction_config = current_config
        
        try:
            target_message = await ctx.channel.fetch_message(int(message_id))
            await target_message.clear_reaction(emoji)
        except (discord.NotFound, discord.Forbidden):
            pass
            
        await ctx.send(f"✅ **Configuração Removida!**\nA reação {emoji} não concede mais cargos.", ephemeral=True)
        if not ctx.interaction: await ctx.message.delete()

# Função de setup para carregar a Cog
async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))