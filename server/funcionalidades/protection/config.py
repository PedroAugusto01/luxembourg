# --- Proteção do Servidor (Anti-Raid) ---
# O cargo que a pessoa terá RESTANTE após a punição.
ID_CARGO_BASE_PROTECAO = 0 # Ex: ID do cargo da Whitelist

# ID do canal para onde os logs de alerta de proteção serão enviados.
ID_CANAL_LOGS_PROTECAO = 0 # Ex: 1394293358999310336

# --- CONFIGURAÇÃO DE PROTEÇÃO E REVERSÃO POR AÇÃO ---
PROTECAO_CONFIG = {
    # Chave de Ação: { "cargo_minimo_id": ID, "reverter_acao": True/False }
    #
    # cargo_minimo_id: Cargo mínimo para realizar a ação sem ser punido. (0 para desativar punição)
    # reverter_acao: Se True, o bot tentará desfazer a ação.

    # -- CANAIS --
    "criar_canal":              { "cargo_minimo_id": 0, "reverter_acao": True }, # Reversão: Deleta o canal criado.
    "deletar_canal":            { "cargo_minimo_id": 0, "reverter_acao": False }, # Reversão: Impossível.
    "alterar_canal_perms":      { "cargo_minimo_id": 0, "reverter_acao": True }, # Reversão: Restaura as permissões anteriores.

    # -- CARGOS --
    "criar_cargo":              { "cargo_minimo_id": 0, "reverter_acao": True }, # Reversão: Deleta o cargo criado.
    "deletar_cargo":            { "cargo_minimo_id": 0, "reverter_acao": False }, # Reversão: Impossível.
    "alterar_cargo_perms":      { "cargo_minimo_id": 0, "reverter_acao": True }, # Reversão: Restaura as permissões anteriores.

    # -- MEMBROS --
    "banir_membro":             { "cargo_minimo_id": 0, "reverter_acao": True }, # Reversão: Desbane o membro.
    "expulsar_membro":          { "cargo_minimo_id": 0, "reverter_acao": False }, # Reversão: Impossível.
    "dar_cargo_perigoso":       { "cargo_minimo_id": 0, "reverter_acao": True }, # Reversão: Remove o cargo do membro.

    # -- OUTRAS --
    "gerenciar_webhooks":       { "cargo_minimo_id": 0, "reverter_acao": True }, # Reversão: Deleta o webhook criado/editado.
}

# Lista de permissões perigosas (usada pelas ações "alterar_cargo_perms" e "dar_cargo_perigoso").
PERMISSOES_PERIGOSAS = [
    'administrator', 'manage_channels', 'manage_roles', 'manage_guild',
    'ban_members', 'kick_members', 'mention_everyone', 'manage_webhooks',
]
# ---------------------------------------------------------------------------------------