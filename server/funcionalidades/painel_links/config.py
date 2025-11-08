import discord

# --- Painel de Links ---

# ID do canal onde o painel será enviado.
ID_CANAL_PAINEL = 1347904633057710154

# Título e descrição da embed.
TITULO_EMBED = "Sejam bem vindos à Luxemburgo!\nA melhor organização do Complexo RJ! 🚀"
DESCRICAO_EMBED = "Selecione abaixo uma opção de acordo com a necessidade que deseja."

# Cor da embed (formato 0xRRGGBB).
COR_EMBED = discord.Color.from_rgb(139, 0, 0) # Ex: Vermelho escuro

# Lista de botões a serem criados.
# 'label': O texto que aparece no botão.
# 'emoji': O emoji do botão.
# 'url': O link para o canal. Você pode obter o link clicando com o botão direito no canal > Copiar link.
BOTOES_DE_LINKS = [
    {"label": "Whatsapp", "emoji": "💬", "url": "https://discord.com/channels/1347904626669916170/1404454539129524244"},
    {"label": "Call Dominação", "emoji": "🔊", "url": "https://discord.com/channels/1347904626669916170/1376168449927155722"},
    {"label": "Tabela de Preços", "emoji": "💸", "url": "https://discord.com/channels/1347904626669916170/1347904634781437972"},
    {"label": "Vagas Gerência", "emoji": "🔥", "url": "https://discord.com/channels/1347904626669916170/1391771649866465311"},
    {"label": "Avisos Gerais", "emoji": "❗", "url": "https://discord.com/channels/1347904626669916170/1347904634781437968"},
    {"label": "Ticket Denúncia", "emoji": "📝", "url": "https://discord.com/channels/1347904626669916170/1347904633057710158"},
    {"label": "Roupas", "emoji": "👕", "url": "https://discord.com/channels/1347904626669916170/1347904634781437964"},
    {"label": "Pagar Advertência", "emoji": "💳", "url": "https://discord.com/channels/1347904626669916170/1347904634446024817"},
    {"label": "Solicitar Ação", "emoji": "🔫", "url": "https://discord.com/channels/1347904626669916170/1347904635012386895"},
    {"label": "Eventos", "emoji": "🌟", "url": "https://discord.com/channels/1347904626669916170/1388257553028350032"},
    {"label": "Justificar Ausência", "emoji": "📅", "url": "https://discord.com/channels/1347904626669916170/1347904635012386886"},
    {"label": "Ações Marcadas", "emoji": "📜", "url": "https://discord.com/channels/1347904626669916170/1410657298430427176"}
]