import discord
from discord.ext import commands
import asyncio
from config import config as global_config
from . import config as module_config 

class ConfirmKickView(discord.ui.View):
    def __init__(self, *, author: discord.Member, members_to_kick: list[discord.Member], bot: commands.Bot):
        super().__init__(timeout=60)
        self.author = author
        self.members_to_kick = members_to_kick
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            print(f"[{global_config.CONTEXTO}] BLOQUEIO: {interaction.user.name} tentou interagir com um comando de {self.author.name}.")
            await interaction.response.send_message("Apenas quem iniciou o comando pode interagir.", ephemeral=True)
            return False
        return True

    @staticmethod
    async def kick_task(channel: discord.TextChannel, author: discord.Member, members: list[discord.Member]):
        """Tarefa estática para rodar em segundo plano com logs."""
        print(f"[{global_config.CONTEXTO}] Iniciando tarefa de expulsão para {len(members)} membros, solicitada por {author.name}.")
        kick_count = 0
        fail_count = 0
        for member in members:
            try:
                await member.kick(reason=f"Expulso por {author.name} (ação automática: sem cargos).")
                kick_count += 1
                print(f"[{global_config.CONTEXTO}] SUCESSO: Membro {member.name} ({member.id}) expulso.")
            except (discord.Forbidden, discord.HTTPException) as e:
                fail_count += 1
                print(f"[{global_config.CONTEXTO}] FALHA: Não foi possível expulsar {member.name} ({member.id}). Erro: {e}")
            await asyncio.sleep(1) 

        report_message = (
            f"✅ **Operação Concluída**\n\n"
            f"Relatório de expulsão solicitado por {author.mention}:\n"
            f"- **Membros expulsos com sucesso:** `{kick_count}`\n"
            f"- **Falhas ao expulsar:** `{fail_count}`"
        )
        await channel.send(report_message)
        print(f"[{global_config.CONTEXTO}] Tarefa de expulsão concluída. Sucessos: {kick_count}, Falhas: {fail_count}.")

    @discord.ui.button(label='Confirmar', style=discord.ButtonStyle.danger, emoji='✔️')
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[{global_config.CONTEXTO}] {interaction.user.name} confirmou a expulsão de {len(self.members_to_kick)} membros.")
        
        await interaction.response.edit_message(content=f"🚀 Processo de expulsão iniciado para **{len(self.members_to_kick)}** membro(s). Um relatório será enviado neste canal quando terminar.", view=None)
        
        self.bot.loop.create_task(self.kick_task(interaction.channel, interaction.user, self.members_to_kick))

    @discord.ui.button(label='Cancelar', style=discord.ButtonStyle.secondary, emoji='✖️')
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[{global_config.CONTEXTO}] {interaction.user.name} cancelou a operação de expulsão.")
        await interaction.response.edit_message(content="❌ Operação cancelada pelo usuário.", view=None)

class ExpulsarSemCargoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="expulsar_sem_cargo", description="Expulsa todos os membros que não possuem cargos.")
    @commands.has_permissions(administrator=True)
    async def expulsar_sem_cargo(self, ctx: commands.Context):
        """Expulsa todos os membros sem cargos, com confirmação. Apenas para usuários autorizados."""
        print(f"[{global_config.CONTEXTO}] Comando 'expulsar_sem_cargo' iniciado por {ctx.author.name} ({ctx.author.id}).")
        
        if ctx.author.id not in module_config.ALLOWED_USERS_FOR_CLEAR:
            print(f"[{global_config.CONTEXTO}] BLOQUEIO: {ctx.author.name} não tem permissão para usar 'expulsar_sem_cargo'.")
            await ctx.send("❌ Você não tem permissão para usar este comando.", ephemeral=True)
            return

        if ctx.interaction:
            await ctx.defer(ephemeral=True)
            
        print(f"[{global_config.CONTEXTO}] Buscando membros sem cargos...")
        members_to_kick = [m for m in ctx.guild.members if len(m.roles) == 1 and not m.bot]
        
        if not members_to_kick:
            print(f"[{global_config.CONTEXTO}] Nenhum membro sem cargo encontrado.")
            if ctx.interaction:
                await ctx.followup.send("✅ **Nenhum membro sem cargo foi encontrado para expulsar.**", ephemeral=True)
            else:
                await ctx.send("✅ **Nenhum membro sem cargo foi encontrado para expulsar.**")
            return

        print(f"[{global_config.CONTEXTO}] {len(members_to_kick)} membro(s) encontrado(s) para expulsão. Enviando confirmação.")
        view = ConfirmKickView(author=ctx.author, members_to_kick=members_to_kick, bot=self.bot)
        confirmation_message = (
            f"⚠️ **Atenção!** Você está prestes a expulsar **{len(members_to_kick)}** membro(s) que não possuem cargos.\n"
            f"Esta ação é irreversível. Clique em **Confirmar** para prosseguir."
        )
        
        if ctx.interaction:
            await ctx.followup.send(confirmation_message, view=view, ephemeral=True)
        else:
            await ctx.send(confirmation_message, view=view)


async def setup(bot):
    await bot.add_cog(ExpulsarSemCargoCog(bot))