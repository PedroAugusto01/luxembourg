import discord
from discord.ext import commands
from . import config as module_config
from config import config as global_config
from datetime import datetime
import math
import asyncio

class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- FUNÇÃO HELPER PARA DIVIDIR MENSAGENS LONGAS ---
    def split_content_into_fields(self, embed: discord.Embed, title_prefix: str, content: str):
        """Divide uma string longa em múltiplos campos de 1024 caracteres para uma embed."""
        limit = 1024
        if not content:
            embed.add_field(name=title_prefix, value="*Vazio*", inline=False)
            return

        char_limit_per_field = 1016
        if len(content) <= char_limit_per_field:
            embed.add_field(name=title_prefix, value=f"```\n{content}\n```", inline=False)
            return
            
        total_parts = math.ceil(len(content) / char_limit_per_field)
        for i in range(total_parts):
            start = i * char_limit_per_field
            end = start + char_limit_per_field
            chunk = content[start:end]
            part_title = f"{title_prefix} (Parte {i+1}/{total_parts})"
            embed.add_field(name=part_title, value=f"```\n{chunk}\n```", inline=False)


    # --- Listener de Mensagem Deletada (COM SUPORTE A EMBEDS E ANEXOS) ---
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        log_channel_id = module_config.LOGS_CONFIG.get("message_delete")
        if not log_channel_id or log_channel_id == 0: return
        if not message.guild or message.author.bot or (datetime.now().timestamp() - message.created_at.timestamp()) > 3600: return

        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel: return

        if not message.content and not message.embeds and not message.attachments:
            return

        embed = discord.Embed(
            color=discord.Color.red(),
            description=f"**🗑️ Mensagem deletada em {message.channel.mention}**",
            timestamp=datetime.now()
        )
        embed.set_author(name=f"{message.author.name} ({message.author.id})", icon_url=message.author.display_avatar.url)
        embed.set_footer(text=f"ID do Autor: {message.author.id}")
        
        if message.content:
            self.split_content_into_fields(embed, "Conteúdo do Texto", message.content)
        
        if message.attachments:
            attachment_links = "\n".join([f"[{att.filename}]({att.url})" for att in message.attachments])
            embed.add_field(name="Anexos", value=attachment_links, inline=False)

        if message.embeds:
            first_embed = message.embeds[0]
            embed_content = ""
            if first_embed.title:
                embed_content += f"**{first_embed.title}**\n"
            if first_embed.description:
                embed_content += f"{first_embed.description}\n"
            
            for field in first_embed.fields:
                embed_content += f"\n**{field.name}**\n{field.value}"

            if embed_content:
                self.split_content_into_fields(embed, "Conteúdo da Embed", embed_content)

        await log_channel.send(embed=embed)

    # --- Listener de Mensagem Editada ---
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        log_channel_id = module_config.LOGS_CONFIG.get("message_edit")
        if not log_channel_id or log_channel_id == 0: return
        if not after.guild or after.author.bot or before.content == after.content: return

        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel: return

        embed = discord.Embed(
            color=discord.Color.orange(),
            description=f"**✍️ Mensagem editada em {after.channel.mention}** [Ir para a mensagem]({after.jump_url})",
            timestamp=datetime.now()
        )
        
        before_content = before.content or "*Vazio*"
        after_content = after.content or "*Vazio*"

        self.split_content_into_fields(embed, "Conteúdo Original (Antes)", before_content)
        self.split_content_into_fields(embed, "Conteúdo Novo (Depois)", after_content)

        embed.set_author(name=f"{after.author.name} ({after.author.id})", icon_url=after.author.display_avatar.url)
        embed.set_footer(text=f"ID da Mensagem: {after.id}")
        
        await log_channel.send(embed=embed)

    # --- Listener de Atualização de Membro ---
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        log_channel_id = module_config.LOGS_CONFIG.get("member_update")
        if not log_channel_id or log_channel_id == 0: return

        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel: return

        # Checa mudança de apelido
        if before.nick != after.nick:
            embed = discord.Embed(color=discord.Color.blue(), description=f"**👤 Apelido alterado para {after.mention}**", timestamp=datetime.now())
            embed.add_field(name="Antes", value=f"`{before.nick or before.name}`", inline=True)
            embed.add_field(name="Depois", value=f"`{after.nick or after.name}`", inline=True)
            embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
            await log_channel.send(embed=embed)

        # Checa mudança de cargos
        if before.roles != after.roles:
            await asyncio.sleep(1) # Pequeno delay para garantir que o log de auditoria seja populado
            responsible_user = None
            try:
                # Busca no log de auditoria pela ação de atualização de cargos no membro
                async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                    if entry.target.id == after.id:
                        responsible_user = entry.user
                        break
            except discord.Forbidden:
                print(f"[{global_config.CONTEXTO}] Sem permissão para ler logs de auditoria no servidor {after.guild.name}.")
            except Exception as e:
                print(f"[{global_config.CONTEXTO}] Erro ao buscar log de auditoria para member_update: {e}")

            if len(after.roles) > len(before.roles):
                new_role = next(role for role in after.roles if role not in before.roles)
                embed = discord.Embed(color=discord.Color.green(), description=f"**➕ Cargo adicionado a {after.mention}**", timestamp=datetime.now())
                embed.add_field(name="Cargo Adicionado", value=new_role.mention, inline=False)
                if responsible_user:
                    embed.add_field(name="Adicionado por", value=responsible_user.mention, inline=False)
                embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
                embed.set_footer(text=f"ID do Membro: {after.id}")
                await log_channel.send(embed=embed)

            elif len(after.roles) < len(before.roles):
                removed_role = next(role for role in before.roles if role not in after.roles)
                embed = discord.Embed(color=discord.Color.dark_red(), description=f"**➖ Cargo removido de {after.mention}**", timestamp=datetime.now())
                embed.add_field(name="Cargo Removido", value=removed_role.mention, inline=False)
                if responsible_user:
                    embed.add_field(name="Removido por", value=responsible_user.mention, inline=False)
                embed.set_author(name=f"{after.name} ({after.id})", icon_url=after.display_avatar.url)
                embed.set_footer(text=f"ID do Membro: {after.id}")
                await log_channel.send(embed=embed)

    # --- Listener de Canal de Voz ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        log_channel_id = module_config.LOGS_CONFIG.get("voice_state_update")
        if not log_channel_id or log_channel_id == 0: return

        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel: return

        if not before.channel and after.channel:
            embed = discord.Embed(color=discord.Color.green(), description=f"**➡️ {member.mention} entrou no canal de voz {after.channel.mention}**", timestamp=datetime.now())
            embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
            await log_channel.send(embed=embed)
        elif before.channel and not after.channel:
            embed = discord.Embed(color=discord.Color.red(), description=f"**⬅️ {member.mention} saiu do canal de voz {before.channel.mention}**", timestamp=datetime.now())
            embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
            await log_channel.send(embed=embed)
        elif before.channel and after.channel and before.channel != after.channel:
            embed = discord.Embed(color=discord.Color.blue(), description=f"**🔄 {member.mention} trocou de canal de voz**", timestamp=datetime.now())
            embed.add_field(name="Saiu de", value=before.channel.mention, inline=True)
            embed.add_field(name="Entrou em", value=after.channel.mention, inline=True)
            embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
            await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logs(bot))