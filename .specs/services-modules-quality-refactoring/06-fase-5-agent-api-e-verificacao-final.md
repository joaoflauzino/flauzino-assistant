# Fase 5 — Eixo C `agent_api` + `__all__` Remanescentes + Verificação Final

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** ⬜ Não iniciada · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** Fase 1 concluída (cria `agent_api/services/utils.py`)
> **Commits previstos:** 1–2
> **Meta:** zero funções top-level com `_` no `agent_api`; zero `__all__` em módulos internos; spec 100% verificada.

---

## Tarefas

### 5.1 `agent_api/core/callbacks.py` (5 funções `_`)
- [ ] Mover helpers puros para `agent_api/core/utils.py` (novo): `usage_from_mapping`, `usage_from_generations`, `extract_token_usage`, `record_llm_metrics`, `log_llm_end` (nomes públicos — Regra 4)
- [ ] `on_llm_end` continua orquestrando (≤ 20 linhas)
- [ ] Testes: `test_callbacks_metrics.py`
- [ ] Commit: `refactor(agent): core/utils + services/utils + remove __all__` (agrupado com 5.2/5.3)

### 5.2 `agent_api/services/classify.py` (2 funções `_`) + `system_prompt.py` (1) + `main.py` (1)
- [ ] `build_tx_payload`, `normalize_confidence` → `agent_api/services/utils.py` (criado na Fase 1.1)
- [ ] `quote_join` (system_prompt.py) → `agent_api/services/utils.py`
- [ ] `_session_cleanup_loop` (main.py) → renomear público `session_cleanup_loop`
- [ ] Testes: `test_classify_service.py`, `test_system_prompt.py`

### 5.3 `__all__` remanescentes (Regra 5)
- [ ] `agent_api/services/tools/__init__.py`: remover `__all__`; consumers importam direto do módulo (`tools.registry` etc.)
- [ ] `telegram_api/services/__init__.py`: remover `__all__` (verificar consumers após a Fase 4.3, que cria `expense_service.py`)
- [ ] Atualizar imports quebrados + testes

### 5.4 Verificação final do plano inteiro
- [ ] Re-rodar o scan AST: **zero** funções violando gates (`ifs > 3` OU `loc > 40` OU `prof. ≥ 4`), salvo justificativas documentadas (Fase 2.6)
- [ ] Re-rodar o scan de smells: **zero** funções top-level com `_`, zero imports tardios, zero `__all__` interno
- [ ] Reduzir tetos do ruff conforme Fase 0.2 (`max-branches = 6`, `max-statements = 40`) e garantir lint verde
- [ ] Fechar o checklist "Definição de pronto" no [00-master-plan.md](./00-master-plan.md)
- [ ] `make format` && `make lint` && `uv run pytest` verdes (suíte completa das 4 APIs)
- [ ] Apresentar resumo final (antes/depois das métricas) ao desenvolvedor

---

## Critérios de aceite da fase (gates)

- [ ] Zero funções top-level com prefixo `_` em `agent_api`, `telegram_api`, `finance_api`, `graph_api`
- [ ] Zero `__all__` em módulos internos
- [ ] Scan AST final sem violações (ou com justificativas registradas)
- [ ] Gates do ruff endurecidos e verdes
- [ ] Todos os checkboxes deste spec fechados ou com pendência justificada

---

## Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| — | — | — | — |
