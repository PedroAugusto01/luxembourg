import discord
from discord.ext import commands
from .aviso import AvisoCog
from .exportar_cargos import ExportarCargosCog
from .clear import ClearCog
from .expulsar_sem_cargo import ExpulsarSemCargoCog

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(AvisoCog(bot))
    await bot.add_cog(ExportarCargosCog(bot))
    await bot.add_cog(ClearCog(bot))
    await bot.add_cog(ExpulsarSemCargoCog(bot))