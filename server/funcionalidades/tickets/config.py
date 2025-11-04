import discord

# --- Tickets ---
ID_CANAL_LOGS_TICKETS = 0 
ID_CARGO_USAR_TICKETS = 0
ID_CANAL_STORAGE_IMAGENS = 0

TICKETS_COMMAND_EMBED = discord.Embed(
    title="🎫 Central de Suporte e Serviços",
    description=(
        "Precisa de ajuda com um de nossos produtos ou deseja contratar uma nova solução?\n\n"
        "Selecione uma das opções abaixo para criar um ticket e nossa equipe especializada entrará em contato em breve."
    ),
    color=discord.Color.from_rgb(88, 101, 242)
)

USAR_BOTOES_PARA_TICKETS = True

TICKET_CATEGORIAS = {
    "🆘 Suporte ao Cliente": {
        "id_categoria_discord": 0,
        "numero_inicial": 1,
        "arquivo_contagem": "ticket_count_suporte.txt",
        "modelo_embed": "**👋 Bem-vindo ao nosso canal de Suporte!**\n\n...",
        "permissoes_cargos": [
            {"nome_grupo": "Gerentes de Suporte", "cargos": [], "permissoes": { "read_messages": True, "send_messages": True, "manage_messages": True, "view_channel": True }},
            {"nome_grupo": "Equipe de Suporte", "cargos": [], "permissoes": { "read_messages": True, "send_messages": False, "view_channel": True }}
        ]
    },
    "💼 Contratar Serviços": {
        "id_categoria_discord": 0,
        "numero_inicial": 1,
        "arquivo_contagem": "ticket_count_comercial.txt",
        "modelo_embed": "**Olá! Que bom ver seu interesse em nossos serviços!**\n\n...",
        "permissoes_cargos": [
            {"nome_grupo": "Gerentes Comerciais", "cargos": [], "permissoes": { "read_messages": True, "send_messages": True, "manage_messages": True, "view_channel": True }},
            {"nome_grupo": "Equipe Comercial", "cargos": [], "permissoes": { "read_messages": True, "send_messages": False, "view_channel": True }}
        ]
    }
}