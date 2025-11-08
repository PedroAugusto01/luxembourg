# --- Módulo de Logs ---
# Defina o ID do canal para cada tipo de log.
# Coloque 0 para desativar o log para um evento específico.
LOGS_CONFIG = {
    # Logs de Mensagens
    "message_delete": 1436755476338446356,    # Canal para logs de mensagens deletadas
    "message_edit": 1436755451239731342,      # Canal para logs de mensagens editadas

    # Logs de Membros
    "member_update": 1436755431799390371,     # Canal para logs de alteração de apelido/cargos
    "voice_state_update": 1436755414988624025 # Canal para logs de entrada/saída de canais de voz
}
# ---------------------------------------------------------------------------------------