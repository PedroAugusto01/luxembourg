import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from . import config as module_config
from config import config as global_config

class AvisoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_avisos_task(self, response_handler, cargo: discord.Role, mensagem: str):
        """
        Esta é a tarefa em segundo plano que faz o envio das DMs.
        O 'response_handler' pode ser um objeto de Interação (para /aviso) ou de Mensagem (para !aviso).
        """
        success_count = 0
        fail_count = 0
        guild = cargo.guild

        # Cria a base da embed uma única vez
        base_embed = discord.Embed(
            color=discord.Color.blue()
        )
        if guild.icon:
            base_embed.set_thumbnail(url=guild.icon.url)
        base_embed.set_footer(text=f"Mensagem enviada do servidor: {guild.name}")

        members_with_role = cargo.members

        for member in members_with_role:
            if member.bot:
                continue

            personal_embed = base_embed.copy()
            personal_embed.description = (
                f"# 📢 AVISO IMPORTANTE 📢 \n\n\n"
                f"### {mensagem}"
            )

            try:
                await member.send(embed=personal_embed)
                success_count += 1
            except (discord.Forbidden, discord.HTTPException):
                fail_count += 1
            
            await asyncio.sleep(1)

        # Edita a mensagem original com o relatório final
        report_message = (
            f"✅ **Relatório de Envio de Avisos Concluído**\n\n"
            f"O aviso foi processado:\n"
            f"- **Enviado com sucesso para:** `{success_count}` membro(s) do cargo `{cargo.name}`\n"
            f"- **Falhas no envio para:** `{fail_count}` membro(s) (provavelmente com DMs fechadas)."
        )
        
        # Edita a resposta final com base no tipo de 'handler'
        if isinstance(response_handler, discord.Interaction):
            await response_handler.edit_original_response(content=report_message, view=None)
        elif isinstance(response_handler, discord.Message):
            await response_handler.edit(content=report_message, view=None)


    @commands.hybrid_command(name="aviso", description="Envia um aviso no privado para todos os membros de um cargo.")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        cargo="O cargo que receberá o aviso.",
        mensagem="A mensagem principal do aviso."
    )
    async def aviso(self, ctx: commands.Context, cargo: discord.Role, mensagem: str):
        """Inicia a tarefa de envio de avisos em segundo plano."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Você não tem permissão de administrador para usar este comando.", ephemeral=True)
            return
            
        initial_message = (
            f"🚀 **Iniciando o envio de avisos para `{len(cargo.members)}` membro(s) do cargo `{cargo.name}`.**\n"
            "Este processo ocorrerá em segundo plano. Esta mensagem será atualizada com o relatório final."
        )

        response_handler = None
        # Se for um comando de barra (/)
        if ctx.interaction:
            await ctx.defer(ephemeral=True)
            await ctx.interaction.edit_original_response(content=initial_message)
            response_handler = ctx.interaction 
        # Se for um comando de prefixo (!)
        else:
            response_handler = await ctx.send(initial_message)

        # Cria e inicia a tarefa em segundo plano
        self.bot.loop.create_task(self.send_avisos_task(response_handler, cargo, mensagem))


async def setup(bot):
    await bot.add_cog(AvisoCog(bot))