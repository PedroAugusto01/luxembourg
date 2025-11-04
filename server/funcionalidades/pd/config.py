# diamond/server/funcionalidades/pd/config.py

# ID do canal para onde os relatórios de PD (Perda Definitiva) serão enviados.
ID_CANAL_LOGS_PD = 1357065185482768555

# IDs de cargos que podem usar o comando /pd.
# Se a lista estiver vazia ou contiver apenas 0, apenas Administradores poderão usar.
IDS_CARGOS_PERMITIDOS_PD = [
    1347904626669916177, # GERENTE DIAMOND 
    1347904626678300722, # Sub-Lider
    1347904626690625547, # Lider
    1347904626690625548 # DEV
]