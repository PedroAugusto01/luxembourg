# /server/funcionalidades/acoes/config.py

# --- MÓDULO DE AÇÕES ---

# ID do canal onde o comando para criar o painel de ação será enviado.
ID_CANAL_COMANDO = 1357064394785296384

# ID do canal para onde as embeds das ações marcadas serão enviadas.
ID_CANAL_ACOES = 1410657298430427176

# Lista de IDs de cargos que podem marcar/gerenciar ações.
IDS_CARGOS_PERMITIDOS = [
    1408891454490935387, # GERENTE ELITE 
    1347904626678300719, # SUB ELITES & AÇÃO 
    1347904626669916174, # GERENTE DE AÇÃO 
    1347904626669916177, # GERENTE DIAMOND 
    1347904626678300722, # Sub-Lider
    1347904626690625547, # Lider
    1347904626690625548 # DEV
]

# Fuso horário para as notificações (Ex: 'America/Sao_Paulo')
# Para ver a lista de fusos: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
FUSO_HORARIO = 'America/Sao_Paulo'