import discord
from discord.ext import commands
from discord import ui, Embed
from . import config as module_config

class PainelLinksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="painel-links", description="Envia o painel com botões e links para canais.")
    @commands.has_permissions(administrator=True)
    async def painel_links(self, ctx: commands.Context):
        # Verifica se o comando foi enviado no canal de configuração
        if ctx.channel.id != module_config.ID_CANAL_PAINEL:
            await ctx.send(f"❌ Este comando só pode ser usado no canal <#{module_config.ID_CANAL_PAINEL}>.", ephemeral=True)
            return

        embed = Embed(
            title=module_config.TITULO_EMBED,
            description=module_config.DESCRICAO_EMBED,
            color=module_config.COR_EMBED
        )
        
        embed.set_thumbnail(url="attachment://logo.gif")
        embed.set_footer(text="BOT Luxemburgo — Copyright © Pedro Kazoii")
        
        # Cria a única View que irá conter todos os botões.
        view = ui.View(timeout=None)
        
        # Adiciona cada botão à view, controlando a linha.
        for i, item in enumerate(module_config.BOTOES_DE_LINKS):
            row_index = i // 3 # Calcula o índice da linha (0, 1, 2, ...)
            view.add_item(
                ui.Button(
                    label=item.get("label"),
                    style=discord.ButtonStyle.gray,
                    emoji=item.get("emoji"),
                    url=item.get("url"),
                    row=row_index
                )
            )

        # Envia a embed com a view de botões.
        await ctx.send(embed=embed, view=view)

        if ctx.interaction:
            await ctx.interaction.response.send_message("Painel de links enviado!", ephemeral=True, delete_after=5)
        else:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
    
async def setup(bot):
    await bot.add_cog(PainelLinksCog(bot))
    # Registra as views para que elas continuem funcionando após o restart
    bot.add_view(ui.View(timeout=None))