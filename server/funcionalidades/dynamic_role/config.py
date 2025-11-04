# --- Cargo por Leitura de Mensagem ---
CARGO_POR_MENSAGEM_CONFIG = {
    "id_canal_observado": 1395034286171623607, # ID do canal que o bot irá monitorar para as mensagens
}

# --- CONFIGURAÇÕES DE APELIDO AUTOMÁTICO ---
# ESCOLHA APENAS UMA DAS DUAS OPÇÕES ABAIXO (DEIXE APENAS UMA COMO "ativado": True)
# OPÇÃO 1: Formato de Apelido Detalhado por Cargo
CARGO_POR_MENSAGEM_NICKNAME = {
    "ativado": False, # Se este for True, o formato fixo será ignorado.

    # Defina o formato do apelido para cada ID de cargo específico.
    # Chaves disponíveis: {TAG}, {NOME}, {ID}
    "formatos_por_cargo": {
        1394309117958426674: { "tag": "[TESTE]", "formato": "{TAG} {NOME} | {ID}" },
        1394309246291808429: { "tag": "(AUX)", "formato": "{TAG} {NOME} #{ID}" },
    }
}

# OPÇÃO 2: Formato de Apelido Fixo para Qualquer Cargo
NICKNAME_FIXED_FORMAT_CONFIG = {
    "ativado": True, # Se este for True, o formato por cargo será ignorado.

    # O bot usará este formato para qualquer cargo concedido pelo módulo.
    # Chaves disponíveis: {NOME}, {ID}
    "formato_fixo": "{NOME} | {ID}"
}

# --- OPÇÃO 3: Confirmação para ID Ausente ---
# Se ativado, e nenhum ID for encontrado na mensagem ou no apelido,
# o bot irá pedir confirmação antes de alterar o apelido.
NICKNAME_ID_CONFIRMATION = {
    "ativado": True
}
# ---------------------------------------------------------------------------------------