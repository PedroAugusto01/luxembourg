import discord
import re
import json
import os
import pandas as pd
import io
from discord import ui, Interaction, ButtonStyle, TextStyle, Embed
from discord.ext import commands
from datetime import datetime
from . import config as module_config
from config import config as global_config

# --- Funções de Banco de Dados JSON ---
DB_PATH = os.path.join(os.path.dirname(__file__), module_config.NOME_ARQUIVO_DATABASE)

def get_field_label_by_marker(marker_key: str):
    """Encontra o label do campo marcado com 'is_id_field'."""
    for field in module_config.MODAL_FIELDS:
        if field.get(marker_key, False):
            return field["label"]
    return None

def load_database():
    if not os.path.exists(DB_PATH):
        return {}
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_database(data):
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_next_id():
    db = load_database()
    if not db:
        return 1
    max_id = 0
    id_field_label = get_field_label_by_marker("is_id_field")
    if not id_field_label: return 1

    for user_data in db.values():
        if user_data.get("status") == "Aprovado":
            user_id_val = user_data.get("dados_formulario", {}).get(id_field_label, 0)
            try:
                user_id_int = int(user_id_val)
                if user_id_int > max_id:
                    max_id = user_id_int
            except (ValueError, TypeError):
                continue
    return max_id + 1

def formatar_nickname_dinamico(formato_str: str, modal_data: dict) -> str:
    """Substitui placeholders no formato do nickname com os dados do formulário."""
    novo_nick = formato_str
    for label, valor in modal_data.items():
        placeholder = f"{{{label.upper()}}}"
        novo_nick = novo_nick.replace(placeholder, str(valor))
    return novo_nick

# --- FUNÇÃO HELPER PARA APROVAÇÃO ---
async def aprovar_membro(interaction: Interaction, membro_wl: discord.Member, modal_data: dict, moderador: discord.Member = None):
    """Lógica central para aprovar um membro, seja manual ou automaticamente."""
    try:
        cargo_aprovado = interaction.guild.get_role(module_config.ID_CARGO_APROVADO)
        if cargo_aprovado: await membro_wl.add_roles(cargo_aprovado, reason="WL Aprovada")
        
        cargo_removido = interaction.guild.get_role(module_config.ID_CARGO_REMOVIDO)
        if cargo_removido and cargo_removido in membro_wl.roles:
            await membro_wl.remove_roles(cargo_removido, reason="WL Aprovada")

        novo_nome = formatar_nickname_dinamico(module_config.FORMATO_NICKNAME, modal_data)
        if len(novo_nome) > 32:
            novo_nome = novo_nome[:32]
        
        await membro_wl.edit(nick=novo_nome, reason="WL Aprovada")
        
        db = load_database()
        user_id_str = str(membro_wl.id)
        if user_id_str in db:
            db[user_id_str]["status"] = "Aprovado"
            db[user_id_str]["aprovado_em"] = datetime.now().isoformat()
            db[user_id_str]["aprovado_por"] = str(moderador.id) if moderador else "Automático"
            db[user_id_str]["dados_formulario"] = modal_data
            save_database(db)

        log_channel = interaction.client.get_channel(module_config.ID_CANAL_LOGS)
        if log_channel:
            log_embed = Embed(
                title="✅ Whitelist Aprovada", 
                description=f"O membro foi aprovado com sucesso no processo de whitelist.", 
                color=discord.Color.green()
            )
            log_embed.set_thumbnail(url=membro_wl.display_avatar.url)

            if moderador:
                log_embed.add_field(name="Aprovado por", value=moderador.mention, inline=False)
                log_embed.set_footer(text=f"Membro ID: {membro_wl.id} • Moderador ID: {moderador.id}")
            else:
                log_embed.add_field(name="Aprovação", value="Automática", inline=False)
                log_embed.set_footer(text=f"Membro ID: {membro_wl.id}")

            dados_formatados = []
            for label, valor in modal_data.items():
                if valor:
                    dados_formatados.append(f"> **{label}:** {valor}")
            
            if dados_formatados:
                log_embed.add_field(name="Dados Preenchidos", value="\n".join(dados_formatados), inline=False)

            log_embed.timestamp = datetime.now()
            await log_channel.send(content=f"**Solicitação Aprovada de:** {membro_wl.mention}", embed=log_embed)
        
        return True, None
    except Exception as e:
        print(f"[{global_config.CONTEXTO}] ERRO AO APROVAR WL: {e}")
        return False, str(e)


# --- View de Aprovação/Recusa (usada se APROVACAO_NECESSARIA = True) ---
class AprovacaoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _processar_wl(self, interaction: Interaction, aprovado: bool):
        moderador = interaction.user
        original_embed = interaction.message.embeds[0]
        
        match = re.search(r"ID do Solicitante: (\d+)", original_embed.footer.text)
        if not match:
            return await interaction.response.send_message("❌ Não foi possível encontrar o ID do solicitante.", ephemeral=True)
        
        membro_id = int(match.group(1))
        membro_wl = interaction.guild.get_member(membro_id)
        if not membro_wl:
            return await interaction.response.send_message(f"❌ Membro com ID `{membro_id}` não encontrado.", ephemeral=True)

        # --- CORREÇÃO APLICADA AQUI ---
        # Remove os ``` do valor do campo antes de processar
        modal_data = {field.name.strip("📝 "): field.value.strip("`") for field in original_embed.fields}

        if aprovado:
            sucesso, erro = await aprovar_membro(interaction, membro_wl, modal_data, moderador=moderador)
            if sucesso:
                await interaction.response.send_message("✅ Whitelist aprovada com sucesso!", ephemeral=True)
                await interaction.message.delete()
            else:
                await interaction.response.send_message(f"❌ Erro ao aprovar: {erro}", ephemeral=True)
        else: # Recusado
            db = load_database()
            user_id_str = str(membro_wl.id)
            if user_id_str in db:
                db[user_id_str]["status"] = "Recusado"
                db[user_id_str]["recusado_em"] = datetime.now().isoformat()
                db[user_id_str]["recusado_por"] = str(moderador.id)
                save_database(db)

            await interaction.response.send_message("❌ Whitelist recusada.", ephemeral=True)
            await interaction.message.delete()

            log_channel = interaction.client.get_channel(module_config.ID_CANAL_LOGS)
            if log_channel:
                log_embed = Embed(
                    title="❌ Whitelist Recusada", 
                    description=f"A solicitação de whitelist foi recusada.",
                    color=discord.Color.red()
                )
                log_embed.set_thumbnail(url=membro_wl.display_avatar.url)
                log_embed.add_field(name="Recusado por", value=interaction.user.mention, inline=False)
                
                dados_formatados = []
                for label, valor in modal_data.items():
                    if valor:
                        dados_formatados.append(f"> **{label}:** {valor}")
                
                if dados_formatados:
                    log_embed.add_field(name="Dados Preenchidos", value="\n".join(dados_formatados), inline=False)

                log_embed.set_footer(text=f"Membro ID: {membro_wl.id} • Moderador ID: {moderador.id}")
                log_embed.timestamp = datetime.now()
                await log_channel.send(content=f"**Solicitação Recusada de:** {membro_wl.mention}", embed=log_embed)

    @ui.button(label="Aprovar", style=ButtonStyle.success, custom_id="aprovar_wl", emoji="✔️")
    async def aprovar_callback(self, interaction: Interaction, button: ui.Button):
        await self._processar_wl(interaction, aprovado=True)

    @ui.button(label="Recusar", style=ButtonStyle.danger, custom_id="recusar_wl", emoji="✖️")
    async def recusar_callback(self, interaction: Interaction, button: ui.Button):
        await self._processar_wl(interaction, aprovado=False)


# --- Modal de Whitelist (Dinâmico) ---
class WhitelistModal(ui.Modal, title="📝 Formulário de WhiteList"):
    def __init__(self):
        super().__init__()
        self.fields_map = {}
        id_field_label = get_field_label_by_marker("is_id_field")

        for field_config in module_config.MODAL_FIELDS:
            if module_config.GERAR_ID_AUTOMATICAMENTE and field_config.get("is_id_field", False):
                continue
            
            text_input = ui.TextInput(
                label=field_config["label"],
                placeholder=field_config.get("placeholder"),
                required=field_config.get("required", True),
                style=TextStyle.paragraph if field_config.get("style") == "paragraph" else TextStyle.short
            )
            self.add_item(text_input)
            self.fields_map[field_config["label"]] = text_input

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        modal_data = {label: input_field.value for label, input_field in self.fields_map.items()}
        id_field_label = get_field_label_by_marker("is_id_field")

        if module_config.GERAR_ID_AUTOMATICAMENTE and id_field_label:
            novo_id = get_next_id()
            modal_data[id_field_label] = novo_id

        db = load_database()
        user_id_str = str(interaction.user.id)
        db[user_id_str] = {
            "discord_username": interaction.user.name,
            "solicitado_em": datetime.now().isoformat(),
            "status": "Pendente" if module_config.APROVACAO_NECESSARIA else "Aprovado",
            "dados_formulario": modal_data
        }
        
        if not module_config.APROVACAO_NECESSARIA:
            db[user_id_str]["aprovado_em"] = datetime.now().isoformat()
            db[user_id_str]["aprovado_por"] = "Automático"

        save_database(db)

        if module_config.APROVACAO_NECESSARIA:
            canal_aprovacao = interaction.client.get_channel(module_config.ID_CANAL_APROVACAO)
            if not canal_aprovacao:
                return await interaction.followup.send("❌ Canal de aprovação não configurado.", ephemeral=True)
            
            embed_aprovacao = Embed(
                title="📥 Nova Solicitação de Whitelist",
                color=discord.Color.orange(),
                description="Um novo membro preencheu o formulário e aguarda análise da moderação."
            )
            embed_aprovacao.set_thumbnail(url=interaction.user.display_avatar.url)

            for label, value in modal_data.items():
                if value:
                    embed_aprovacao.add_field(name=f"📝 {label}", value=f"```{value}```", inline=False)
            
            embed_aprovacao.set_footer(text=f"ID do Solicitante: {interaction.user.id}")
            embed_aprovacao.timestamp = datetime.now()
            
            await canal_aprovacao.send(
                content=f"**Nova solicitação de:** {interaction.user.mention}",
                embed=embed_aprovacao, 
                view=AprovacaoView()
            )
            await interaction.followup.send("✅ Sua solicitação foi enviada para análise!", ephemeral=True)
        else:
            sucesso, erro = await aprovar_membro(interaction, interaction.user, modal_data)
            if sucesso:
                await interaction.followup.send("✅ Você foi aprovado na whitelist com sucesso!", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Erro ao te aprovar: {erro}", ephemeral=True)


# --- View do Botão Inicial ---
class WhitelistButtonView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label=module_config.TEXTO_BOTAO, style=ButtonStyle.gray, custom_id="fazer_wl_button", emoji="📝")
    async def fazer_wl(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(WhitelistModal())


# --- Cog e Comandos ---
class Whitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="wl", description="Envia o painel para iniciar o processo de whitelist.")
    @commands.has_permissions(manage_guild=True)
    async def inscrever(self, ctx: commands.Context):
        embed_para_enviar = module_config.EMBED.copy()
        arquivo_para_enviar = None

        if module_config.NOME_ARQUIVO_BANNER:
            caminho_banner = os.path.join(os.path.dirname(module_config.__file__), module_config.NOME_ARQUIVO_BANNER)

            if os.path.exists(caminho_banner):
                arquivo_para_enviar = discord.File(caminho_banner, filename=module_config.NOME_ARQUIVO_BANNER)
                embed_para_enviar.set_image(url=f"attachment://{module_config.NOME_ARQUIVO_BANNER}")
            else:
                print(f"AVISO: Banner '{module_config.NOME_ARQUIVO_BANNER}' não encontrado.")
                embed_para_enviar.set_image(url=None)

        await ctx.send(embed=embed_para_enviar, view=WhitelistButtonView(), file=arquivo_para_enviar)
        
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    @commands.hybrid_command(name="exportwl", description="Exporta os dados da whitelist para um arquivo Excel.")
    @commands.has_permissions(manage_guild=True)
    async def exportwl(self, ctx: commands.Context):
        async with ctx.typing():
            db = load_database()
            if not db:
                await ctx.send("❌ O banco de dados da whitelist está vazio.", delete_after=10)
                return

            records = []
            for discord_id, data in db.items():
                record = {
                    "Discord ID": discord_id,
                    "Discord Username": data.get("discord_username"),
                    "Status": data.get("status"),
                    "Solicitado Em": data.get("solicitado_em"),
                    "Aprovado Em": data.get("aprovado_em"),
                    "Recusado Em": data.get("recusado_em"),
                    "Aprovado Por ID": data.get("aprovado_por"),
                    "Recusado Por ID": data.get("recusado_por")
                }
                record.update(data.get("dados_formulario", {}))
                records.append(record)
            
            try:
                df = pd.DataFrame(records)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='WhitelistData')
                
                buffer.seek(0)
                file = discord.File(buffer, filename="whitelist_export.xlsx")
                await ctx.send("✅ Aqui está o arquivo Excel com os dados da whitelist:", file=file)
            except Exception as e:
                await ctx.send(f"❌ Ocorreu um erro ao gerar o arquivo Excel: {e}")
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

async def setup(bot):
    bot.add_view(AprovacaoView())
    bot.add_view(WhitelistButtonView())
    await bot.add_cog(Whitelist(bot))