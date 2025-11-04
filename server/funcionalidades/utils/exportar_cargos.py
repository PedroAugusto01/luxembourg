import discord
from discord.ext import commands
from discord import app_commands
import io
from . import config as module_config
from config import config as global_config

class ExportarCargosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="exportar_cargos", description="Exporta todos os cargos do servidor para um arquivo de texto.")
    @commands.has_permissions(administrator=True)
    async def exportar_cargos(self, ctx: commands.Context):
        """Exporta todos os cargos do servidor em um formato específico para um arquivo de texto."""
        await ctx.typing()
        
        roles = [role for role in sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True) if not role.is_default() and not role.managed]
        
        if not roles:
            await ctx.send("Não há cargos para exportar neste servidor (além do @everyone).")
            return

        formatted_roles = []
        for role in roles:
            role_name = role.name.replace('"', '\\"')
            formatted_roles.append(f'{{"nome_exibido": "{role_name}", "id_cargo": {role.id}}},')
        
        output_string = "\n".join(formatted_roles)

        try:
            buffer = io.BytesIO(output_string.encode('utf-8'))
            file = discord.File(buffer, filename="lista_de_cargos.txt")
            await ctx.send("✅ Aqui está a lista de cargos do servidor:", file=file)
        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro ao gerar o arquivo: {e}")
            print(f"[{global_config.CONTEXTO}] Erro ao exportar cargos: {e}")

async def setup(bot):
    await bot.add_cog(ExportarCargosCog(bot))