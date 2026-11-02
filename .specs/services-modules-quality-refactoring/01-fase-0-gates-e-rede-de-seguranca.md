# Fase 0 — Pré-requisitos, Gates e Rede de Segurança

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** ⬜ Não iniciada · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** —
> **Commits previstos:** 2
> **Regra:** nenhuma refatoração acontece nesta fase.

---

## Tarefas

### 0.1 Destino do WIP atual (branch `feat/refactor`)
O working tree tem alterações não commitadas em `finance_api/services/invoices.py`, `balances.py`, `dashboard_strategies.py` + testes (trabalho de fechamento de faturas). Nada da Fase 1 começa antes disso resolvido.

- [ ] Rodar suíte completa sobre o WIP (`uv run pytest`) e garantir verde
- [ ] Apresentar `git diff` e resumo ao desenvolvedor (`AGENTS.md` §7)
- [ ] Obter autorização explícita e commitar o WIP
- [ ] **Re-medir** `invoices.py` e `balances.py` após o commit (os itens 1.2 e 1.6 da Fase 1 dependem dessa nova medição)

### 0.2 Gates de complexidade no `ruff` (`pyproject.toml`)
Já existe `C90 max-complexity = 10`. Adicionar:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "C90", "PLR0912", "PLR0915"]

[tool.ruff.lint.pylint]
max-branches = 8      # começar permissivo; reduzir para 6 ao final das fases
max-statements = 50   # reduzir para 40 ao final das fases
```

- [ ] Medir o ruído das regras novas antes de fixar tetos
- [ ] Configurar `PLR0912`/`PLR0915` com tetos permissivos
- [ ] Congelar a lista de violações atuais (dívida visível — mapa está no master plan §2)
- [ ] Avaliar `PLR0913` (max-args) apenas como sinalização para `ImportService.__init__`; se gerar ruído no código-base inteiro, **não adotar**

### 0.3 Testes de caracterização (rede de segurança)
Garantir cobertura ANTES de mexer nos pontos críticos:

- [ ] `agent_api/tests/services/test_agent_service.py`: as 3 vias de `_extract_assistant_response` (structured no state, dict, tool_calls nas mensagens, fallback de texto) + merge de `image_base64`
- [ ] `finance_api/tests/services/test_invoices.py`: patch parcial (só closing, só due, só status), invoice inexistente (criação), cartão sem `credit_card_id`
- [ ] `update()` de spents/incomes/subscriptions/credit_cards: categoria inválida, PM inválida, PM que resolve conta/cartão, entidade inexistente
- [ ] `telegram_api/tests/services/test_session_service.py`: repo injetado vs default × complete vs session_id vs sem nada
- [ ] `finance_api/tests/repositories/test_payment_methods_repository.py`: `get_by_key` achando em payment_methods, credit_cards, accounts e não achando

### 0.4 Verificação
- [ ] `make format` && `make lint` && `uv run pytest` verdes

---

## Critérios de aceite da fase (gates)

- [ ] WIP commitado **com autorização explícita** do desenvolvedor
- [ ] Gates `PLR0912`/`PLR0915` configurados e violações congeladas
- [ ] Testes de caracterização dos 5 pontos críticos escritos e verdes
- [ ] `invoices.py`/`balances.py` re-medidos (números atualizados no master plan, se mudarem)
- [ ] Suíte completa verde

---

## Evidências de execução
> Preencher durante a execução: data, hash do commit, resultado dos testes.

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| — | — | — | — |
