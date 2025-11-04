import discord
from discord.ext import commands
from . import config as module_config # Carrega o config.py local
from config import config as global_config # Carrega o config.py global

class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_error(self, guild, message):
        """Helper para enviar erros para um canal de log, se configurado."""
        print(f"[{global_config.CONTEXTO}] ERRO AutoRole: {message}")
        log_channel = guild.get_channel(module_config.ID_CANAL_LOGS) # Usando o canal de log da WL como padrão
        if log_channel:
            try:
                await log_channel.send(f"⚠️ **Erro no Módulo AutoRole:**\n{message}")
            except Exception as e:
                print(f"[{global_config.CONTEXTO}] Falha ao enviar log de erro do AutoRole para o canal: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != global_config.ID_SERVIDOR:
            return
        if member.bot:
            return

        print(f"[{global_config.CONTEXTO}] Novo membro entrou: {member.name}. Iniciando Auto Role.")

        role_ids_to_add = module_config.IDS_CARGOS_AUTO_ROLE
        if not role_ids_to_add or all(role_id == 0 for role_id in role_ids_to_add):
            await self.log_error(member.guild, "A lista `IDS_CARGOS_AUTO_ROLE` está vazia ou contém apenas zeros. Nenhum cargo foi adicionado.")
            return

        roles_to_add = []
        for role_id in role_ids_to_add:
            if role_id == 0: continue # Ignora os placeholders
            role = member.guild.get_role(role_id)
            if role:
                roles_to_add.append(role)
            else:
                await self.log_error(member.guild, f"O cargo com ID `{role_id}` não foi encontrado no servidor.")

        if not roles_to_add:
            await self.log_error(member.guild, f"Nenhum dos cargos configurados foi encontrado para adicionar a {member.mention}.")
            return
        
        try:
            await member.add_roles(*roles_to_add, reason="Auto Role na entrada do servidor.")
            added_role_names = ", ".join([f"'{role.name}'" for role in roles_to_add])
            print(f"[{global_config.CONTEXTO}] Cargos adicionados com sucesso para {member.name}: {added_role_names}.")
        except discord.Forbidden:
            await self.log_error(member.guild, f"**Falha de Permissão!** Não foi possível adicionar cargos a {member.mention}. Verifique se o cargo do bot está acima dos cargos de Auto Role na hierarquia do servidor.")
        except Exception as e:
            await self.log_error(member.guild, f"Ocorreu um erro inesperado ao tentar adicionar cargos a {member.mention}: `{e}`")

# Função de setup para carregar a Cog
async def setup(bot):
    await bot.add_cog(AutoRole(bot))