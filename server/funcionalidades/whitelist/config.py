import discord

# --- WhiteList ---

# --- Comportamento ---
APROVACAO_NECESSARIA = True
GERAR_ID_AUTOMATICAMENTE = False

# --- Arquivos ---
NOME_ARQUIVO_DATABASE = "whitelist_db.json"

# --- Canais e Cargos ---
ID_CARGO_PERMITIDO = 1434642845758914671
ID_CANAL_APROVACAO = 1439696985669243020
ID_CANAL_LOGS = 1439696985669243020
ID_CARGO_APROVADO = 1434559390668554344
ID_CARGO_REMOVIDO = 0
ID_CARGO_MODERADOR = 1434642845758914671

# --- Textos e Aparência ---

# Texto que aparecerá no botão para iniciar o processo de whitelist.
TEXTO_BOTAO = "Seja Recrutado!"

# --- IMAGEM ADICIONADA AQUI ---
NOME_ARQUIVO_BANNER = "banner_wl.png"

# Embed que será enviada com o comando !wl
EMBED = discord.Embed(
    title=":clipboard: RECRUTAMENTO :clipboard:",
    description=(
        "<a:SetaDireita:1436757674124378222> Para realizar o recrutamento, clique no botão abaixo e preencha com as seguintes informações: \n"
        "```NOME E SOBRENOME: \n"
        "SEU ID: \n"
        "TELEFONE NA CIDADE: \n"
        "FAC PAGOU SUA BLACKLIST: \n"
        "QUEM TE RECRUTOU:```"
    ),
    color=discord.Color.from_rgb(255, 53, 237)
)

# --- Campos do Formulário (Modal) ---
MODAL_FIELDS = [
    {
        "label": "Nome e Sobrenome",
        "placeholder": "Insira seu nome e sobre nome do RP",
        "required": True,
        "style": "short"
    },
    {
        "label": "ID",
        "placeholder": "Ex: 10000",
        "required": True,
        "is_id_field": True,
        "style": "short"
    },
    {
        "label": "TELEFONE NA CIDADE",
        "placeholder": "Ex: 000-000",
        "required": True,
        "style": "short"
    },
    {
        "label": "FAC PAGOU SUA BLACKLIST",
        "placeholder": "Ex: SIM/NÃO",
        "required": True,
        "style": "short"
    },
    {
        "label": "QUEM TE RECRUTOU:",
        "placeholder": "Ex: 1520",
        "required": False,
        "style": "short"
    }
]

# --- Formato do Nickname ---
FORMATO_NICKNAME = "[MEM] {NOME E SOBRENOME} | {ID}"