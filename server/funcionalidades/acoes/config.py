# /server/funcionalidades/acoes/config.py

# --- MÓDULO DE AÇÕES ---

# ID do canal onde o comando para criar o painel de ação será enviado.
ID_CANAL_COMANDO = 1439698545010544640

# ID do canal para onde as embeds das ações marcadas serão enviadas.
ID_CANAL_ACOES = 1439698681774211083

# Lista de IDs de cargos que podem marcar/gerenciar ações.
IDS_CARGOS_PERMITIDOS = [
    1434643759735242823, # 00
    1434559390823747602, # Sub-Lider
    1434559390836592720, # Dono
    1434559390823747603, # Chave
    1436168481266470922, # Gerente elite
    1436750681582207168 # Gerente ações
]

# Fuso horário para as notificações (Ex: 'America/Sao_Paulo')
# Para ver a lista de fusos: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
FUSO_HORARIO = 'America/Sao_Paulo'