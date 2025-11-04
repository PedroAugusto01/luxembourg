import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from . import config as module_config
from config import config as global_config

class ClearCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="clear", description="Excluí todas as mensagens do canal específico. CUIDADO AO USAR!!!")
    @commands.has_permissions(administrator=True)
    async def clear(self, ctx: commands.Context):
        """Apaga todas as mensagens de um canal. Apenas para usuários autorizados."""
        # Apenas 'defere' se for uma interação de barra (slash command)
        if ctx.interaction:
            await ctx.defer(ephemeral=True)

        if ctx.author.id not in module_config.ALLOWED_USERS_FOR_CLEAR:
            await ctx.send("❌ Você não tem permissão para usar este comando.", ephemeral=True, delete_after=10)
            if not ctx.interaction:
                try:
                    await ctx.message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
            return

        # Para comandos de barra, a resposta deve ser um followup
        send_method = ctx.followup.send if ctx.interaction else ctx.send
        
        confirm_message = await send_method(f"⚠️ **Atenção!** Esta ação é irreversível e irá apagar **TODAS** as mensagens em {ctx.channel.mention}. Digite `confirmar` para prosseguir.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "confirmar"

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=20.0)
            await msg.delete() 
            if confirm_message: await confirm_message.delete()
        except asyncio.TimeoutError:
            await send_method("Tempo esgotado. A limpeza do canal foi cancelada.", delete_after=10)
            return
        except discord.NotFound: # A mensagem de confirmação pode já ter sido apagada
            pass
        
        try:
            processing_message = await send_method("✅ Confirmado. Limpando o canal...")
            new_channel = await ctx.channel.clone(reason=f"Canal limpo por {ctx.author.name}")
            await ctx.channel.delete(reason=f"Canal limpo por {ctx.author.name}")
            await new_channel.send(f"✅ Canal limpo com sucesso por {ctx.author.mention}!")
        except discord.Forbidden:
            if processing_message: await processing_message.edit(content="❌ Erro de permissão. Não foi possível clonar ou deletar este canal.")
        except Exception as e:
            if processing_message: await processing_message.edit(content="❌ Ocorreu um erro inesperado.")
            print(f"[{global_config.CONTEXTO}] ERRO ao tentar limpar o canal '{ctx.channel.name}': {e}")

async def setup(bot):
    await bot.add_cog(ClearCog(bot))