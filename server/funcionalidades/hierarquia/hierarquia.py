# /server/funcionalidades/hierarquia/hierarquia.py

import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from . import config as module_config
from config import config as global_config

class HierarquiaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_hierarchy.start()

    def cog_unload(self):
        """Cancela a tarefa quando o cog é descarregado."""
        self.update_hierarchy.cancel()

    async def build_hierarchy_embed(self, guild: discord.Guild) -> discord.Embed:
        """Constrói a embed da hierarquia."""
        embed = discord.Embed(
            title=module_config.TITULO_EMBED,
            color=module_config.COR_EMBED
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        hierarchy_description = ""
        for role_id in module_config.CARGOS_DA_HIERARQUIA:
            role = guild.get_role(role_id)
            if role:
                members = [member for member in role.members if not member.bot]
                hierarchy_description += f"\n**{role.mention} ({len(members)})**\n"
                if members:
                    member_mentions = [member.mention for member in members[:50]]
                    hierarchy_description += "\n".join(member_mentions)
                else:
                    hierarchy_description += "*Nenhum membro neste cargo.*"
                hierarchy_description += "\n"
        
        if not hierarchy_description:
            embed.description = "Nenhum cargo foi configurado para a hierarquia."
        else:
            embed.description = hierarchy_description[:4096]

        # Adiciona o rodapé com a próxima atualização
        next_update_time = datetime.now() + timedelta(hours=module_config.INTERVALO_ATUALIZACAO_HORAS)
        # <t:timestamp:R> é um formato especial do Discord que mostra o tempo relativo
        embed.set_footer(text=f"Próxima atualização:")
        embed.timestamp = next_update_time

        return embed

    @tasks.loop(hours=module_config.INTERVALO_ATUALIZACAO_HORAS)
    async def update_hierarchy(self):
        """Tarefa que atualiza a mensagem da hierarquia periodicamente."""
        await self.bot.wait_until_ready()

        channel_id = module_config.ID_CANAL_HIERARQUIA
        message_id = module_config.ID_MENSAGEM_HIERARQUIA

        if not channel_id or not message_id:
            print(f"[{global_config.CONTEXTO}] Aviso (Hierarquia): Canal ou Mensagem não configurados. A atualização automática está desativada.")
            return

        guild = self.bot.get_guild(global_config.ID_SERVIDOR)
        if not guild: return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            print(f"[{global_config.CONTEXTO}] ERRO (Hierarquia): Canal com ID {channel_id} não encontrado.")
            return

        try:
            message = await channel.fetch_message(message_id)
            new_embed = await self.build_hierarchy_embed(guild)
            await message.edit(embed=new_embed)
            print(f"[{global_config.CONTEXTO}] Hierarquia atualizada com sucesso.")
        except discord.NotFound:
            print(f"[{global_config.CONTEXTO}] ERRO (Hierarquia): Mensagem com ID {message_id} não encontrada no canal.")
        except discord.Forbidden:
            print(f"[{global_config.CONTEXTO}] ERRO (Hierarquia): Sem permissão para editar a mensagem no canal {channel.name}.")
        except Exception as e:
            print(f"[{global_config.CONTEXTO}] ERRO (Hierarquia): Ocorreu um erro inesperado ao atualizar a hierarquia: {e}")

    @commands.hybrid_command(name="setup_hierarquia", description="Envia o painel inicial da hierarquia.")
    @commands.has_permissions(administrator=True)
    async def setup_hierarquia(self, ctx: commands.Context):
        """Envia a mensagem inicial da hierarquia e instrui sobre como configurar a atualização."""
        await ctx.defer(ephemeral=True)

        channel_id = module_config.ID_CANAL_HIERARQUIA
        if not channel_id:
            await ctx.followup.send("❌ **Erro:** O `ID_CANAL_HIERARQUIA` não foi definido no arquivo de configuração.", ephemeral=True)
            return
            
        target_channel = self.bot.get_channel(channel_id)
        if not target_channel:
            await ctx.followup.send(f"❌ **Erro:** O canal com ID `{channel_id}` não foi encontrado.", ephemeral=True)
            return

        try:
            initial_embed = await self.build_hierarchy_embed(ctx.guild)
            message = await target_channel.send(embed=initial_embed)

            reply_message = (
                f"✅ **Painel de Hierarquia Enviado!**\n\n"
                f"Agora, siga este passo crucial:\n"
                f"1. Copie a ID da mensagem abaixo:\n"
                f"```{message.id}```\n"
                f"2. Cole essa ID na variável `ID_MENSAGEM_HIERARQUIA` dentro do arquivo `server/funcionalidades/hierarquia/config.py`.\n"
                f"3. Reinicie o bot para que a atualização automática comece a funcionar."
            )
            await ctx.followup.send(reply_message, ephemeral=True)
        except discord.Forbidden:
            await ctx.followup.send(f"❌ **Erro de Permissão:** Não tenho permissão para enviar mensagens no canal {target_channel.mention}.", ephemeral=True)
        except Exception as e:
            await ctx.followup.send(f"❌ Ocorreu um erro inesperado: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HierarquiaCog(bot))