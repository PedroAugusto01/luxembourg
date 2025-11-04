import discord
# ARQUIVOS NECESSÁRIOS:
# horarios_agendados.json
# ticket_count_fotos.txt
# ticket_count_roupas.txt

# --- Tickets Multicategoria ---
ID_CANAL_LOGS_TICKETS = 0
ARQUIVO_AGENDAMENTO = "horarios_agendados.json"
ID_CANAL_STORAGE_IMAGENS = 0

# IDs para o agendamento de ensaios
ID_CANAL_AGENDAMENTOS = 0
ID_CARGO_NOTIFICACAO_ENSAIO = 0

TICKET_CATEGORIAS = {
    "Roupas e Acessórios": {
        "id_categoria_discord": 0,
        "numero_inicial": 1,
        "arquivo_contagem": "ticket_count_roupas.txt",
        "modelo_embed": "**👕 Olá! Para a compra de roupas, informe a lista completa dos itens desejados.**",
        "permissoes_cargos": [
            {"nome_grupo": "Equipe Roupas", "cargos": [0, 0], "permissoes": { "read_messages": True, "send_messages": True, "manage_messages": True, "view_channel": True }}
        ]
    },
    "Agendamento de Fotos": {
        "id_categoria_discord": 0,
        "numero_inicial": 1,
        "arquivo_contagem": "ticket_count_fotos.txt",
        "modelo_embed": "**🗓️ Olá! Para agendar uma sessão de fotos, informe o horário e a data desejada.**",
        "permissoes_cargos": [
            {"nome_grupo": "Equipe Fotografia", "cargos": [0, 0], "permissoes": { "read_messages": True, "send_messages": True, "manage_messages": True, "view_channel": True }}
        ]
    }
}

EMBED_TICKETS_ROUPAS = discord.Embed (
    title="👕 Jaguar Studio - Roupas Personalizadas",
    description=(
        "✨ Crie seu estilo exclusivo com a Jaguar Studio!\n\n"
        "**Como funciona:**\n"
        "1️⃣ Clique no botão abaixo para abrir seu ticket\n"
        "2️⃣ Explique sua ideia e envie referências\n"
        "3️⃣ Nossa equipe responderá o quanto antes\n\n"
        "⭐ Atendimento premium garantido!"
    ),
    color=discord.Color.from_rgb(212, 16, 222)
)

EMBED_TICKETS_ENSAIO = discord.Embed(
    title="📸 Jaguar Studio - Agende seu Ensaio",
    description=(
        "✨ Fotografia que transforma momentos em arte!\n\n"
        "Clique no botão abaixo para abrir seu ticket e garantir seu horário exclusivo."
    ),
    color=discord.Color.from_rgb(212, 16, 222)
)