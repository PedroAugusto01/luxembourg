# diamond/server/funcionalidades/advertencia/advertencia.py

import discord
from discord.ext import commands
from discord import app_commands # Necessário para o @app_commands.guilds
import datetime

# Importa do config local (da pasta advertencia)
from .config import ADVERTENCIA_LOG_CHANNEL_ID, ALLOWED_ROLES_IDS

# Classe do Cog
class Advertencia(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Comando Híbrido /advertencia ou !advertencia
    @commands.hybrid_command(
        name="advertencia", 
        description="Aplica uma advertência e um cargo a um membro."
    )
    @commands.has_any_role(*ALLOWED_ROLES_IDS) # Verifica se o usuário tem QUALQUER um dos cargos da lista
    @app_commands.describe(
        membro="O membro que receberá a advertência.",
        cargo="O cargo de advertência que será aplicado.",
        motivo="O motivo da advertência."
    )
    async def advertencia(
        self, 
        ctx: commands.Context, 
        membro: discord.Member, 
        cargo: discord.Role,
        *, # Faz 'motivo' pegar todo o resto da string no comando de prefixo
        motivo: str
    ):
        # Resposta inicial (defer). Funciona para prefixo e slash.
        await ctx.defer(ephemeral=True)
        
        log_channel = self.bot.get_channel(ADVERTENCIA_LOG_CHANNEL_ID)
        if not log_channel:
            # ctx.send() será um followup do defer, mantendo o ephemeral=True
            await ctx.send("❌ Canal de log de advertência não encontrado. Verifique o `config.py` do módulo.", ephemeral=True)
            return

        # 1. Aplicar o cargo
        try:
            # Usamos ctx.author (funciona para ambos)
            await membro.add_roles(cargo, reason=f"Advertência aplicada por {ctx.author.name}. Motivo: {motivo}")
        except discord.Forbidden:
            await ctx.send(f"❌ Erro de permissão. Não consigo aplicar o cargo {cargo.mention}. (Meu cargo pode estar abaixo dele).", ephemeral=True)
            return
        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro inesperado ao aplicar o cargo: {e}", ephemeral=True)
            return

        # 2. Criar o Embed (Baseado no PD)
        embed = discord.Embed(
            title="🚨 REGISTRO DE ADVERTÊNCIA 🚨",
            color=discord.Color.orange(), # Laranja para advertência
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="<a:SetaDireita:1436757674124378222> Membro:", value=f"{membro.mention} ({membro.id})", inline=False)
        embed.add_field(name="<a:SetaDireita:1436757674124378222> Staff:", value=f"{ctx.author.mention} ({ctx.author.id})", inline=False)
        embed.add_field(name="<a:SetaDireita:1436757674124378222> Cargo Aplicado:", value=f"{cargo.mention}", inline=False)
        embed.add_field(name="<a:SetaDireita:1436757674124378222> Motivo:", value=motivo, inline=False)

        embed.set_footer(text=f"ID do Membro: {membro.id} • ID do Autor: {ctx.author.id}")
        
        if membro.display_avatar:
            embed.set_thumbnail(url=membro.display_avatar.url)
        
        # 3. Enviar o Embed no canal de Log
        await log_channel.send(embed=embed)

        # 4. Enviar DM para o membro
        try:
            dm_embed = discord.Embed(
                title="Aviso de Advertência",
                description=f"Você recebeu uma advertência no servidor **Luxemburgo**.\n\n"
                            f"**Cargo Recebido:** {cargo.name}\n"
                            f"**Motivo:** {motivo}",
                color=discord.Color.orange()
            )
            await membro.send(embed=dm_embed)
        except discord.Forbidden:
            pass # Ignora se não puder enviar DM

        # 5. Confirmação para o Staff (Sem Kick)
        await ctx.send(f"✅ Advertência aplicada! O membro {membro.mention} recebeu o cargo {cargo.mention}.", ephemeral=True)

    # Tratamento de erro para o comando híbrido
    @advertencia.error
    async def on_advertencia_error(self, ctx: commands.Context, error: commands.CommandError):
        # Erros mais comuns com comandos de prefixo
        if isinstance(error, commands.MissingAnyRole):
            await ctx.send("❌ Você não tem permissão para usar este comando.", ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Argumento inválido. Verifique se marcou o membro e o cargo corretamente.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
             await ctx.send(f"❌ Faltando argumento. Uso: `!advertencia @membro @cargo Motivo da advertência`", ephemeral=True)
        else:
            # Erro genérico
            await ctx.send(f"❌ Ocorreu um erro: {error}", ephemeral=True)


    @commands.hybrid_command(
        name="advertencia_embed",
        description="Cria um embed de registro de advertências no canal atual."
    )
    @commands.has_any_role(*ALLOWED_ROLES_IDS)
    async def advertencia_embed(
        self,
        ctx: commands.Context
    ):
        await ctx.defer(ephemeral=True)

        embed = discord.Embed(
            title="🚨 REGISTRO DE ADVERTÊNCIAS 🚨",
            color=discord.Color.orange()
        )
        
        # Ajuste: Removidas as vírgulas para criar uma string única
        descricao = (
            "<a:SetaDireita:1436757674124378222> Seja bem vindo ao **Painel de Punições!** Para utiliza-lo siga as instruções abaixo: \n\n"
            "<a:SetaDireita:1436757674124378222> Digite **/advertencia** e complete com os campos solicitados\n"
            "<a:SetaDireita:1436757674124378222> Dê enter e selecione **qual advertência você deseja aplicar!**\n"
            "<a:SetaDireita:1436757674124378222> Dê enter novamente e **irá gerar um relatório automático neste canal!**"
        )
        
        embed.description = descricao
        embed.set_footer(text="BOT Luxemburgo — Copyright © Pedro Kazoii") # Footer atualizado

        try:
            # Envia o embed no canal ONDE O COMANDO FOI USADO
            await ctx.channel.send(embed=embed)
            
            # Confirma para o staff
            await ctx.send("✅ Embed de registro enviado com sucesso!", ephemeral=True)
            
        except discord.Forbidden:
            await ctx.send("❌ Não tenho permissão para enviar embeds neste canal.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro ao enviar o embed: {e}", ephemeral=True)


    @advertencia_embed.error
    async def on_advertencia_embed_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.send("❌ Você não tem permissão para usar este comando.", ephemeral=True)
        # Erro de argumento removido, pois o comando não tem argumentos
        else:
            await ctx.send(f"❌ Ocorreu um erro: {error}", ephemeral=True)

# Função setup para carregar o Cog
async def setup(bot):
    await bot.add_cog(Advertencia(bot))