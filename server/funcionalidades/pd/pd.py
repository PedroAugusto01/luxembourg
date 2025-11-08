# diamond/server/funcionalidades/pd/pd.py

import discord
from discord import ui, Interaction, Embed
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import re
import pytz # Para fuso horário
from typing import Optional # <--- ADICIONADO AQUI

# Importar configs
from . import config as module_config
from config import config as global_config

# --- Função Auxiliar de Permissão ---
def pode_usar_pd(member: discord.Member) -> bool:
    """Verifica se o membro tem permissão para usar o comando PD."""
    # 1. Administradores sempre podem
    if member.guild_permissions.administrator:
        return True
        
    ids_permitidos = set(module_config.IDS_CARGOS_PERMITIDOS_PD)
    
    # 2. Se a lista está vazia ou com 0, apenas admin pode (tratado acima)
    if not ids_permitidos or all(cid == 0 for cid in ids_permitidos):
        return False 

    # 3. Verifica se o membro tem algum dos cargos
    ids_usuario = {role.id for role in member.roles}
    return not ids_usuario.isdisjoint(ids_permitidos)

# --- Cog Principal ---
class PDCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def encontrar_membro_por_id(self, guild: discord.Guild, target_id: int) -> Optional[discord.Member]: # <--- CORRIGIDO AQUI
        """Varre os membros e encontra um pelo ID no nickname."""
        target_id_str = str(target_id)
        
        # Regex para encontrar o ID no final do nick, ex: "Nome | 4567" ou "Nome 4567"
        # Ajustado para aceitar ID no início, meio ou fim, desde que seja o número exato
        regex_pattern = rf"(?:\D|^)({re.escape(target_id_str)})(?:\D|$)"
        
        for member in guild.members:
            if member.bot:
                continue
            
            # Checa o apelido (display_name)
            if re.search(regex_pattern, member.display_name):
                return member
        
        # Fallback: Se o regex falhar, tenta uma busca mais simples
        for member in guild.members:
             if member.bot:
                continue
             if target_id_str in member.display_name:
                print(f"[{global_config.CONTEXTO}] Aviso (PD): Membro {member.name} encontrado via fallback (ID no meio do nome).")
                return member

        return None

    @commands.hybrid_command(name="pd", description="Remove um membro do servidor e registra a perda.")
    @app_commands.describe(
        id="O ID do jogo do membro (presente no apelido).",
        motivo="O motivo da remoção."
    )
    async def pd(self, ctx: commands.Context, id: int, motivo: str):
        
        # 1. Checar permissão
        if not pode_usar_pd(ctx.author):
            await ctx.send("❌ Você não tem permissão para usar este comando.", ephemeral=True, delete_after=10)
            return
        
        await ctx.defer(ephemeral=True)
        
        # 2. Encontrar o membro
        guild = ctx.guild
        membro_alvo = await self.encontrar_membro_por_id(guild, id)
        
        if not membro_alvo:
            return await ctx.followup.send(f"❌ Nenhum membro encontrado com o ID `{id}` no apelido.", ephemeral=True)

        # 3. Preparar a Embed de Log (antes de expulsar, para ter os dados)
        log_channel = self.bot.get_channel(module_config.ID_CANAL_LOGS_PD)
        if not log_channel:
            return await ctx.followup.send("❌ Erro de configuração: Canal de logs de PD não encontrado.", ephemeral=True)

        try:
            # Tenta usar o fuso horário de 'America/Sao_Paulo'
            tz = pytz.timezone('America/Sao_Paulo')
        except Exception:
            tz = pytz.UTC # Fallback

        agora = datetime.now(tz)

        embed_log = Embed(
            title="🚨 Relatório de PD 🚨",
            description=f"Um membro foi removido do servidor.",
            color=discord.Color.red(),
            timestamp=agora
        )
        if membro_alvo.display_avatar:
            embed_log.set_thumbnail(url=membro_alvo.display_avatar.url)
        
        # Usei a seta animada de outros módulos seus para consistência
        embed_log.add_field(name="<a:SetaDireita:1436757674124378222> Membro Afetado", value=f"{membro_alvo.mention} (`{membro_alvo.display_name}`)", inline=False)
        embed_log.add_field(name="<a:SetaDireita:1436757674124378222> ID no Jogo", value=f"`{id}`", inline=False)
        embed_log.add_field(name="<a:SetaDireita:1436757674124378222> Motivo", value=f"```\n{motivo}\n```", inline=False)
        embed_log.add_field(name="<a:SetaDireita:1436757674124378222> Aplicado por", value=ctx.author.mention, inline=False)
        
        embed_log.set_footer(text=f"ID do Membro: {membro_alvo.id} • ID do Autor: {ctx.author.id}")

        # 4. Tentar expulsar o membro
        try:
            await membro_alvo.kick(reason=f"PD aplicado por {ctx.author.name}. Motivo: {motivo}")
        except discord.Forbidden:
            return await ctx.followup.send(f"❌ Falha de Permissão. Não consigo expulsar {membro_alvo.mention}. Meu cargo é mais baixo que o dele?", ephemeral=True)
        except Exception as e:
            return await ctx.followup.send(f"❌ Ocorreu um erro ao expulsar o membro: {e}", ephemeral=True)
        
        # 5. Enviar o log
        await log_channel.send(embed=embed_log)
        await ctx.followup.send(f"✅ Membro **{membro_alvo.display_name}** (`{id}`) foi expulso com sucesso e o log foi registrado.", ephemeral=True)


    @commands.hybrid_command(name="pd_embed", description="Envia o painel de instruções do PD.")
    @commands.has_permissions(administrator=True)
    async def pd_embed(self, ctx: commands.Context):
        
        embed = Embed(
            title="🚨 PD 🚨",
            color=discord.Color.dark_red() # Cor escura, similar à imagem
        )
        
        descricao = (
            "Seja bem vindo ao **Painel de PD**! Para utiliza-lo siga as instruções abaixo:\n\n"
            "➡️ Digite **/pd** e complete com os campos solicitados (`ID` e `Motivo`).\n"
            "➡️ O bot irá encontrar o membro pelo ID no apelido e expulsá-lo.\n"
            "➡️ Dê enter e **irá gerar um relatório automático** no canal de logs."
        )
        
        embed.description = descricao
        
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        # Footer padrão do seu bot
        embed.set_footer(text="BOT Luxemburgo — Copyright © Pedro Kazoii")

        await ctx.send(embed=embed)
        
        if ctx.interaction:
            await ctx.interaction.response.send_message("Painel enviado!", ephemeral=True, delete_after=5)
        else:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PDCog(bot))