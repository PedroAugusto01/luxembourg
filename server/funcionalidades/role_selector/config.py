# /server/funcionalidades/role_selector/config.py

import discord

# Título da embed que será enviada.
TITULO_EMBED = "✨ Seletor de Cargos"

# Descrição da embed. Use {mention} para mencionar o usuário.
DESCRICAO_EMBED = ("Olá {mention}! Selecione os cargos que você deseja receber. "
                   "Isso ajudará a personalizar sua experiência no servidor.")

# Cor da embed em formato hexadecimal.
COR_EMBED = 0x2B2D31

# Texto do placeholder (dica) que aparece no menu de seleção.
PLACEHOLDER_MENU = "Clique aqui para ver os cargos disponíveis..."

# Lista de cargos que aparecerão no seletor.
# Você pode adicionar ou remover cargos conforme necessário.
# Formato: {"nome_exibido": "Nome que aparece no menu", "id_cargo": ID_DO_CARGO_AQUI}
CARGOS_SELECIONAVEIS = [
    {"nome_exibido": "Cargo de Notificações", "id_cargo": 123456789012345678},
    {"nome_exibido": "Cargo de Eventos", "id_cargo": 987654321098765432},
    {"nome_exibido": "Cargo de Parceiro", "id_cargo": 112233445566778899},
    # Adicione mais cargos aqui...
]

# Mensagem de confirmação quando o usuário seleciona cargos.
MENSAGEM_SUCESSO = "✅ Seus cargos foram atualizados com sucesso!"

# Mensagem de erro caso algo dê errado.
MENSAGEM_ERRO = "❌ Ocorreu um erro ao atualizar seus cargos. Tente novamente."