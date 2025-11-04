import discord
from discord.ext import commands
from . import config as module_config # Carrega o config.py local
from config import config as global_config # Carrega o config.py global
import asyncio

class Protection(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.punished_users = set()

    # --- FUNÇÕES HELPER (AJUDA) ---
    async def log_action(self, embed: discord.Embed):
        log_channel_id = module_config.ID_CANAL_LOGS_PROTECAO
        if not log_channel_id or log_channel_id == 0:
            return
        channel = self.bot.get_channel(log_channel_id)
        if channel:
            await channel.send(embed=embed)

    async def get_responsible_user(self, guild, target_id, action):
        await asyncio.sleep(1.5)
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if entry.target and entry.target.id == target_id:
                    member = await guild.fetch_member(entry.user.id)
                    if member: return member
        except discord.NotFound: return None
        except discord.Forbidden: print(f"[{global_config.CONTEXTO}] ERRO: Sem permissão para ler o log de auditoria.")
        except Exception as e: print(f"[{global_config.CONTEXTO}] ERRO INESPERADO em get_responsible_user: {e}")
        return None

    async def execute_action(self, responsible_member: discord.Member, action_key: str, reason: str, **kwargs):
        """Função central que verifica permissões, pune E reverte a ação."""
        if not responsible_member or responsible_member.id in self.punished_users or responsible_member.id == self.bot.user.id or responsible_member.id == responsible_member.guild.owner_id:
            return

        action_config = module_config.PROTECAO_CONFIG.get(action_key, {})
        min_role_id = action_config.get("cargo_minimo_id", 0)
        
        if not min_role_id or min_role_id == 0: return

        min_role = responsible_member.guild.get_role(min_role_id)
        if not min_role: return

        # A lógica principal: a punição ocorre se o cargo do membro for inferior ao exigido.
        if responsible_member.top_role.position < min_role.position:
            # Tenta reverter a ação se estiver configurado
            if action_config.get("reverter_acao", False):
                await self.revert_action(action_key, reason, **kwargs)

            # Pune o usuário
            await self.punish(responsible_member, reason)

    async def punish(self, responsible_member: discord.Member, reason: str):
        """Aplica a punição de remover os cargos."""
        if responsible_member.top_role.position >= responsible_member.guild.me.top_role.position:
            return

        self.punished_users.add(responsible_member.id)
        base_role = responsible_member.guild.get_role(module_config.ID_CARGO_BASE_PROTECAO)
        
        roles_to_remove = [role for role in responsible_member.roles if role.is_assignable() and role != base_role]
        removed_roles_str = ", ".join([f"`@{role.name}`" for role in roles_to_remove]) or "Nenhum cargo aplicável removido."
        roles_to_keep = [base_role] if base_role else []

        try:
            await responsible_member.edit(roles=roles_to_keep, reason=f"Punição Automática: {reason}")
            embed = discord.Embed(title="🚨 ALERTA DE PROTEÇÃO - PUNIÇÃO APLICADA 🚨", description=f"O usuário **{responsible_member.mention}** foi punido.", color=discord.Color.red())
            embed.add_field(name="Motivo da Punição", value=reason, inline=False)
            embed.add_field(name="Cargos Removidos", value=removed_roles_str, inline=False)
            embed.set_footer(text=f"ID do Usuário: {responsible_member.id}")
            await self.log_action(embed)
        except Exception as e:
            print(f"[{global_config.CONTEXTO}] ERRO ao punir {responsible_member.name}: {e}")
        
        await asyncio.sleep(10)
        self.punished_users.discard(responsible_member.id)

    async def revert_action(self, action_key: str, reason: str, **kwargs):
        """Tenta reverter a ação maliciosa com base na chave da ação."""
        try:
            reverted = False
            if action_key == "criar_canal":
                channel = kwargs.get('channel')
                if channel: await channel.delete(reason="Reversão automática de proteção")
                reverted = True
            elif action_key == "alterar_canal_perms":
                before = kwargs.get('before')
                after = kwargs.get('after')
                if before and after: await after.edit(overwrites=before.overwrites, reason="Reversão automática de proteção")
                reverted = True
            elif action_key == "criar_cargo":
                role = kwargs.get('role')
                if role: await role.delete(reason="Reversão automática de proteção")
                reverted = True
            elif action_key == "alterar_cargo_perms":
                before = kwargs.get('before')
                after = kwargs.get('after')
                if before and after: await after.edit(permissions=before.permissions, reason="Reversão automática de proteção")
                reverted = True
            elif action_key == "banir_membro":
                guild = kwargs.get('guild')
                user = kwargs.get('user')
                if guild and user: await guild.unban(user, reason="Reversão automática de proteção")
                reverted = True
            elif action_key == "dar_cargo_perigoso":
                member = kwargs.get('member')
                role = kwargs.get('role')
                if member and role: await member.remove_roles(role, reason="Reversão automática de proteção")
                reverted = True
            
            if reverted:
                embed = discord.Embed(title="✅ PROTEÇÃO - AÇÃO REVERTIDA ✅", description=f"A ação maliciosa foi desfeita.", color=discord.Color.green())
                embed.add_field(name="Ação Revertida", value=reason, inline=False)
                await self.log_action(embed)

        except Exception as e:
            print(f"[{global_config.CONTEXTO}] ERRO ao tentar reverter a ação '{action_key}': {e}")


    # --- LISTENERS DE EVENTOS ---
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        responsible_user = await self.get_responsible_user(channel.guild, channel.id, discord.AuditLogAction.channel_create)
        await self.execute_action(responsible_user, "criar_canal", f"Criou o canal `#{channel.name}`.", channel=channel)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        responsible_user = await self.get_responsible_user(channel.guild, channel.id, discord.AuditLogAction.channel_delete)
        await self.execute_action(responsible_user, "deletar_canal", f"Excluiu o canal `#{channel.name}`.")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.overwrites == after.overwrites: return
        responsible_user = await self.get_responsible_user(after.guild, after.id, discord.AuditLogAction.channel_update)
        await self.execute_action(responsible_user, "alterar_canal_perms", f"Alterou permissões no canal `#{after.name}`.", before=before, after=after)
        
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        responsible_user = await self.get_responsible_user(role.guild, role.id, discord.AuditLogAction.role_create)
        await self.execute_action(responsible_user, "criar_cargo", f"Criou o cargo `@{role.name}`.", role=role)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        responsible_user = await self.get_responsible_user(role.guild, role.id, discord.AuditLogAction.role_delete)
        await self.execute_action(responsible_user, "deletar_cargo", f"Excluiu o cargo `@{role.name}`.")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        perms_list = module_config.PERMISSOES_PERIGOSAS
        dangerous_perms_added = [p for p in perms_list if getattr(after.permissions, p) and not getattr(before.permissions, p)]
        if dangerous_perms_added:
            responsible_user = await self.get_responsible_user(after.guild, after.id, discord.AuditLogAction.role_update)
            reason = f"Concedeu permissões perigosas ({', '.join(dangerous_perms_added)}) ao cargo `@{after.name}`."
            await self.execute_action(responsible_user, "alterar_cargo_perms", reason, before=before, after=after)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        responsible_user = await self.get_responsible_user(guild, user.id, discord.AuditLogAction.ban)
        await self.execute_action(responsible_user, "banir_membro", f"Baniu o membro `{user.name}`.", guild=guild, user=user)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await asyncio.sleep(1)
        try:
            async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if entry.target and entry.target.id == member.id:
                    responsible_user = await member.guild.fetch_member(entry.user.id)
                    await self.execute_action(responsible_user, "expulsar_membro", f"Expulsou o membro `{member.name}`.")
                    return
        except discord.Forbidden: pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if len(after.roles) > len(before.roles):
            new_role = next((role for role in after.roles if role not in before.roles), None)
            if new_role:
                perms_list = module_config.PERMISSOES_PERIGOSAS
                dangerous_perms_in_role = [p for p in perms_list if getattr(new_role.permissions, p)]
                if dangerous_perms_in_role:
                    responsible_user = await self.get_responsible_user(after.guild, after.id, discord.AuditLogAction.member_role_update)
                    reason = f"Concedeu o cargo perigoso `@{new_role.name}` para `{after.name}`."
                    await self.execute_action(responsible_user, "dar_cargo_perigoso", reason, member=after, role=new_role)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        # A reversão aqui seria deletar o webhook, o que pode ser complexo de identificar qual foi alterado.
        # Por segurança, a punição é a ação principal.
        responsible_user = await self.get_responsible_user(channel.guild, channel.id, discord.AuditLogAction.webhook_update)
        await self.execute_action(responsible_user, "gerenciar_webhooks", f"Alterou webhooks no canal `#{channel.name}`.")

async def setup(bot):
    await bot.add_cog(Protection(bot))