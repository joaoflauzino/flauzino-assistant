# Fase 5 — Eixo C `agent_api` + `__all__` Remanescentes + Verificação Final

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** ✅ Concluída (2026-11-02) · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** Fase 1 concluída (cria `agent_api/services/utils.py`)
> **Commits previstos:** 1–2
> **Meta:** zero funções top-level com `_` no `agent_api`; zero `__all__` em módulos internos; spec 100% verificada.

---

## Tarefas

### 5.1 `agent_api/core/callbacks.py` (5 funções `_`)
- [x] Mover helpers puros para `agent_api/core/utils.py` (novo): `usage_from_mapping`, `usage_from_generations`, `extract_token_usage`, `record_llm_metrics`, `log_llm_end` (nomes públicos — Regra 4)
- [x] `on_llm_end` continua orquestrando (≤ 20 linhas)
- [x] Testes: `test_callbacks_metrics.py` (+ `tests/core/test_utils.py`)
- [x] Commit: `refactor(agent): core/utils + services/utils + remove __all__` (agrupado com 5.2/5.3)

### 5.2 `agent_api/services/classify.py` (2 funções `_`) + `system_prompt.py` (1) + `main.py` (1)
- [x] `build_tx_payload`, `normalize_confidence` → `agent_api/services/utils.py` (criado na Fase 1.1)
- [x] `quote_join` (system_prompt.py) → `agent_api/services/utils.py`
- [x] `_session_cleanup_loop` (main.py) → renomear público `session_cleanup_loop`
- [x] Testes: `test_classify_service.py`, `test_system_prompt.py`, `test_utils.py`

### 5.3 `__all__` remanescentes (Regra 5)
- [x] `agent_api/services/tools/__init__.py`: remover `__all__`; consumers importam direto do módulo (`tools.registry` etc.)
- [x] `telegram_api/services/__init__.py`: remover `__all__` (verificar consumers após a Fase 4.3, que cria `expense_service.py`)
- [x] Atualizar imports quebrados + testes

### 5.4 Verificação final do plano inteiro
- [x] Re-rodar o scan AST: **zero** funções violando gates (`ifs > 3` OU `loc > 40` OU `prof. ≥ 4`), salvo justificativas documentadas (Fase 2.6)
- [x] Re-rodar o scan de smells: **zero** funções top-level com `_`, zero imports tardios, zero `__all__` interno
- [x] Reduzir tetos do ruff conforme Fase 0.2 (`max-branches = 6`, `max-statements = 40`) e garantir lint verde
- [x] Fechar o checklist "Definição de pronto" no [00-master-plan.md](./00-master-plan.md)
- [x] `make format` && `make lint` && `uv run pytest` verdes (suíte completa das 4 APIs)
- [x] Apresentar resumo final (antes/depois das métricas) ao desenvolvedor

---

## Critérios de aceite da fase (gates)

- [x] Zero funções top-level com prefixo `_` em `agent_api`, `telegram_api`, `finance_api`, `graph_api`
- [x] Zero `__all__` em módulos internos
- [x] Scan AST final sem violações (ou com justificativas registradas)
- [x] Gates do ruff endurecidos e verdes
- [x] Todos os checkboxes deste spec fechados ou com pendência justificada

---

## Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| 2026-11-02 | — (aguardando autorização) | 5.1 `core/utils.py` + `core/schemas.py` (`TokenUsage`, Regra 1); `callbacks.py` 202 → 149 LOC, `on_llm_end` 16 LOC | 670 passed |
| 2026-11-02 | — | 5.2 `build_tx_payload`/`normalize_confidence`/`quote_join` em `services/utils.py`; `session_cleanup_loop` público; `classify.py` 162 → 139 LOC | 670 passed |
| 2026-11-02 | — | 5.3 `__all__` removido de `agent_api/services/tools/__init__.py` e `telegram_api/services/__init__.py`; consumers importam de `tools.registry` | 670 passed · gate 12 → 10 |
| 2026-11-02 | — | 5.4 ruff endurecido (`max-branches=6`, `max-statements=40`); 3 funções com 4 `if`s decompostas (session_repository, category_rules, importers/registry); 2 helpers `_` → públicos (`normalize_separators`, `resolve_default_payment_type`) | 670 passed · gate 10 sem stale/novas |

### Notas de execução

- **5.1** — `TokenUsage` não podia morar em `core/utils.py` sem violar a Regra 1 (contrato de dados junto de helpers), então foi para `agent_api/core/schemas.py`; `utils.py` ficou só com as funções. `on_llm_end` mantém apenas a orquestração (busca info → mede → registra → loga) em 16 LOC.
- **5.2** — `DEFAULT_CONFIDENCE` acompanhou `normalize_confidence` para `services/utils.py` (fonte única). `classify.py` ficou só com a orquestração do LLM e a sanitização de sugestões.
- **5.3** — `__init__.py` de ambos os pacotes ficou só com a docstring (sem re-export), conforme Regra 5/8.5. Consumidores de `create_agent_tools` passaram a importar de `agent_api.services.tools.registry`.
- **5.4 (scan final)** — `ifs > 3`: **0**; `profundidade ≥ 4`: **0**; imports tardios: **0**; `__all__`: **0**; funções top-level com `_`: **0**. Restam apenas as **3** funções com `loc > 40` já justificadas em §2.2-B (`_to_staged` 45, `build_gerar_grafico` 41, `_parse_row` 50) — todas com profundidade ≤ 1 e `if`s ≤ 2.
- **5.4 (ruff)** — `max-branches=6` revelou `finance_api/core/decorators.py` com 7 branches: os três `except` de re-raise foram colapsados em um tuple `(EntityNotFoundError, EntityConflictError, ValidationError)`, sem mudar a ordem de captura (5 branches). `max-statements=40` revelou o fixture `mock_dependencies` (48 statements) em `test_facade.py`, quebrado em builders (`build_batch_repository`, `build_staged_transaction_repository`, `build_rule_repository`, `build_purchase_service`, `attach_batch_identity`, `apply_batch_stats`).
- **5.4 (fora do escopo previsto, mesma sessão)** — para fechar os gates de condicional e Regra 4, três funções com 4 `if`s foram decompostas sem mudança de comportamento: `SessionRepository.get_session` (helper puro `is_session_expired`), `CategoryRuleRepository.find_matching_rule` (predicado `_matches_rule`) e `CheckingAccountTargetResolver.resolve` (`_account_id_from_card`); e dois helpers top-level com `_` viraram públicos (`normalize_separators` em `c6_common.py`, `resolve_default_payment_type` em `classification.py`).
- **Gate de arquitetura** — baseline **12 → 10** (regra E zerada); restam os 10 renomes da 6.5, sem entradas obsoletas nem violações novas.
- **Colisão de basename no pytest** — `agent_api/tests/core/test_utils.py` exigiu `agent_api/tests/core/__init__.py`; sem ele, o pytest importava o módulo como top-level e conflitava com `finance_api/tests/services/test_utils.py`.
- **Pendência registrada (não silenciosa)** — `telegram_api/repositories/session_repository.py` mantém 4 `except Exception` de degradação best-effort (cache de sessão: log + `rollback` + retorno nulo/lista vazia). O comportamento é intencional e está fixado por `test_list_distinct_chat_ids_and_error_handling`; cada bloco ganhou comentário `# Boundary`. Trocar por exceções específicas exige decisão de produto (propagar falha de DB derrubaria todo update do bot), por isso **não** foi alterado nesta fase.
