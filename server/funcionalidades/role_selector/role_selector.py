import discord
from discord.ext import commands
from discord import app_commands
import server.funcionalidades.role_selector.config as module_config
import config.config as global_config

class RoleSelectorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        options = [
            discord.SelectOption(label=cargo["nome_exibido"], value=str(cargo["id_cargo"]))
            for cargo in module_config.CARGOS_SELECIONAVEIS
        ]

        self.add_item(RoleSelect(options))

class RoleSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(
            placeholder=module_config.PLACEHOLDER_MENU,
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id="role_selector_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        guild = interaction.guild

        # Pega todos os IDs dos cargos configurados
        all_configured_role_ids = {int(opt.value) for opt in self.options}
        
        # Pega os IDs dos cargos que o usuário selecionou
        selected_role_ids = {int(value) for value in self.values}
        
        # Pega os cargos que o membro já possui e que estão na lista de seleção
        current_member_role_ids = {role.id for role in member.roles if role.id in all_configured_role_ids}

        roles_to_add_ids = selected_role_ids - current_member_role_ids
        roles_to_remove_ids = all_configured_role_ids - selected_role_ids

        try:
            # Adiciona novos cargos
            for role_id in roles_to_add_ids:
                role = guild.get_role(role_id)
                if role:
                    await member.add_roles(role)

            # Remove cargos desmarcados
            for role_id in roles_to_remove_ids:
                role = guild.get_role(role_id)
                if role:
                    await member.remove_roles(role)
            
            await interaction.followup.send(module_config.MENSAGEM_SUCESSO, ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send("❌ Não tenho permissão para gerenciar seus cargos.", ephemeral=True)
        except Exception as e:
            print(f"[{global_config.CONTEXTO}] Erro no seletor de cargos: {e}")
            await interaction.followup.send(module_config.MENSAGEM_ERRO, ephemeral=True)


class RoleSelectorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="enviar-seletor-cargos", description="Envia a mensagem com o seletor de cargos.")
    @commands.has_permissions(administrator=True)
    async def setup_role_selector(self, ctx: commands.Context):
        embed = discord.Embed(
            title=module_config.TITULO_EMBED,
            description=module_config.DESCRICAO_EMBED.format(mention=ctx.author.mention),
            color=module_config.COR_EMBED
        )
        
        await ctx.send(embed=embed, view=RoleSelectorView())
        
        if ctx.interaction:
            await ctx.interaction.response.send_message("Painel de seleção de cargos enviado!", ephemeral=True, delete_after=5)
        else:
            await ctx.message.delete()

async def setup(bot: commands.Bot):
    bot.add_view(RoleSelectorView())
    await bot.add_cog(RoleSelectorCog(bot))