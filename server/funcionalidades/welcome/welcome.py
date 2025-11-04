import discord
from discord.ext import commands
from . import config as module_config
from config import config as global_config

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_welcome_message(self, member: discord.Member):
        if member.bot:
            return

        welcome_channel = self.bot.get_channel(module_config.ID_CANAL_BOAS_VINDAS)
        if not welcome_channel:
            print(f"[{global_config.CONTEXTO}] ERRO: Canal de boas-vindas não encontrado. Verifique ID_CANAL_BOAS_VINDAS no config.")
            return

        embed = discord.Embed(
            title="✨ Bem-vindo(a) ao Jaguar Studio! ✨",
            description=f"Olá {member.mention}, seja muito bem-vindo(a) ao nosso servidor!\nExplore e agende seu ensaio fotográfico conosco!",
            color=discord.Color.from_rgb(212, 16, 222)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Jaguar Studio • Fotografia Premium")

        try:
            await welcome_channel.send(embed=embed)
        except discord.Forbidden:
            print(f"[{global_config.CONTEXTO}] ERRO: Sem permissão para enviar mensagem no canal de boas-vindas.")
        except Exception as e:
            print(f"[{global_config.CONTEXTO}] ERRO ao enviar mensagem de boas-vindas: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != global_config.ID_SERVIDOR:
            return
            
        await self._send_welcome_message(member)
    
    @commands.hybrid_command(name="testar_boas_vindas", description="Envia uma mensagem de boas-vindas para um membro (apenas para admins).")
    @commands.has_permissions(administrator=True)
    async def testar_boas_vindas(self, ctx: commands.Context, member: discord.Member = None):
        welcome_channel = self.bot.get_channel(module_config.ID_CANAL_BOAS_VINDAS)
        target_member = member or ctx.author
        await self._send_welcome_message(target_member)
        embed = discord.Embed(
            title="✨ Bem-vindo(a) ao Jaguar Studio! ✨",
            description=f"Olá {member.mention}, seja muito bem-vindo(a) ao nosso servidor!\nExplore e agende seu ensaio fotográfico conosco!",
            color=discord.Color.from_rgb(212, 16, 222)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Jaguar Studio • Fotografia Premium")

        try:
            await welcome_channel.send(embed=embed)
        except discord.Forbidden:
            print(f"[{global_config.CONTEXTO}] ERRO: Sem permissão para enviar mensagem no canal de boas-vindas.")
        except Exception as e:
            print(f"[{global_config.CONTEXTO}] ERRO ao enviar mensagem de boas-vindas: {e}")


async def setup(bot):
    await bot.add_cog(Welcome(bot))