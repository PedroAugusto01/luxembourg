import os

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"

# Lista de funcionalidades (Cogs) a serem carregadas.
# O caminho é a partir da pasta principal, usando pontos em vez de barras.
MODULOS_ATIVOS = {
    'server.funcionalidades.whitelist.whitelist':           True,
    'server.funcionalidades.tickets.tickets':               False,
    'server.funcionalidades.autorole.autorole':             False,
    'server.funcionalidades.protection.protection':         False,
    'server.funcionalidades.logs.logs':                     False,
    'server.funcionalidades.dynamic_role.dynamic_role':     False,
    'server.funcionalidades.reaction_roles.reaction_roles': False,
    'server.funcionalidades.licenca.licenca':               False,
    'server.funcionalidades.log_checker.log_checker':       False,
    'server.funcionalidades.multi_tickets.multi_tickets':   False,
    'server.funcionalidades.welcome.welcome':               False,
    'server.funcionalidades.role_selector.role_selector':   False,
    'server.funcionalidades.utils.utils':                   False,
    'server.funcionalidades.elite_test.elite_test':         False,
    'server.funcionalidades.acoes.acoes':                   False,
    'server.funcionalidades.hierarquia.hierarquia':         False,
    'server.funcionalidades.painel_links.painel_links':     False,
    'server.funcionalidades.pd.pd':                         False,
}

# Nome para LOG
CONTEXTO = "Servidor Luxembourg" # Contexto global para os logs no console

# --- IDs de Configuração ---

# ID do servidor
ID_SERVIDOR = 1434559390647713975
# ---------------------------------------------------------------------------------------