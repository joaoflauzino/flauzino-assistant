# Fase 1 — Eixo A: Condicionais em Cascata nos Services

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** ⬜ Não iniciada · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** Fase 0 concluída
> **Commits previstos:** 5 (itens 1.1–1.5; item 1.6 pode virar 1 commit extra ou ser descartado)
> **Meta:** nenhuma função de `services/` com > 3 condicionais (`AGENTS.md` §3.4).

---

## Tarefas

### 1.1 `agent_api/services/agent.py:83` — `_extract_assistant_response` (7 `if`s, 49 LOC, prof. 5)
**Padrão:** Chain of Responsibility / lista de extratores (`python-pattern-chain-of-responsibility`).

```python
def _extract_assistant_response(self, result: dict[str, Any]) -> AssistantResponse:
    image_base64 = result.get("image_base64")
    for extract in (self._from_structured_state, self._from_tool_calls, self._from_last_message):
        response = extract(result)
        if response is not None:
            return attach_image(response, image_base64)  # helper único p/ o merge repetido 3×
    return self._fallback_response(image_base64)
```

- [ ] Criar `agent_api/services/utils.py` com `attach_image` (público — Regra 4)
- [ ] Decompor em 3 extratores com guard clauses (≤ 2 `if`s cada) + `_fallback_response`
- [ ] Manter logs informativos de cada via (observabilidade existente)
- [ ] Testes: `test_agent_service.py` cobre as 3 vias + fallback (caracterizados na Fase 0)
- [ ] Commit: `refactor(agent): chain-of-responsibility in _extract_assistant_response`

### 1.2 `finance_api/services/invoices.py:131` — `update_invoice_dates` (6 `if`s, 43 LOC)
**Padrão:** SRP + patch declarativo (Regra 7 do `python-modular-code-organization`).
⚠️ Re-medir após o commit do WIP (Fase 0.1).

- [ ] Guard clause: `invoice is None` → delega para `_create_invoice(pm, reference_month, closing_date, due_date, status)`
- [ ] `_patch_existing_invoice(...)`: substituir os 4 `if x is not None` por dict comprehension:

```python
patch = {
    field: value
    for field, value in {
        "real_closing_date": closing_date,
        "real_due_date": due_date,
        "status": status,
    }.items()
    if value is not None
}
```

- [ ] Preservar o backfill de `credit_card_id` (`if not invoice.credit_card_id and pm.id`)
- [ ] Testes: `test_invoices.py` (caracterizados na Fase 0)
- [ ] Commit: `refactor(invoices): split patch vs create + declarative patch`

### 1.3 Família `update()` — `spents.py:216` (6 `if`s), `incomes.py:122` (5), `subscriptions.py:78` (5), `credit_cards.py:64` (5)
**Problema:** os 4 services duplicam "valida categoria → valida payment method → resolve relações → patch no DTO", com `_validate_category`/`_validate_payment_method` reimplementados.
**Padrão:** Extract Class + DI (`python-pattern-repository-service`).

- [ ] Criar colaborador `UpdateDataPreparer` em `finance_api/services/update_preparation.py` (contratos em `services/protocols.py`), recebendo repos validadores via `__init__`, expondo `prepare(update_data) -> None`
- [ ] Cada `update()` vira: `preparer.prepare(...)` → guard de existência → `repo.update` → resposta (≤ 3 condicionais)
- [ ] Corrigir violação de DI em `subscriptions.py:84`: `CategoryRepository` injetada no construtor (nunca instanciada dentro do método)
- [ ] Remover `getattr(matched_pm, "is_credit_card", False)` defensivo em `spents.py:230` (entidade é tipada; se teste precisa de `getattr`, corrigir o mock)
- [ ] Testes: `test_spents_router.py`, `test_incomes_service.py`, `test_subscriptions_service.py`, `test_credit_cards_service.py` + novos testes do `UpdateDataPreparer` com fakes
- [ ] Commit: `refactor(services): extract UpdateDataPreparer from update() family`

### 1.4 `telegram_api/services/session_service.py:35` — `sync_chat_session` (5 `if`s, prof. 3)
**Padrão:** eliminar a duplicação "repo injetado vs default".

```python
@asynccontextmanager
async def _repository_scope(self) -> AsyncIterator[SessionRepositoryProtocol]:
    if self._repository is not None:
        yield self._repository
        return
    async with get_db() as session:
        yield SessionRepository(session)
```

- [ ] Implementar `_repository_scope` + `_apply_sync(repo, chat_id, is_complete, new_session_id)` com guard clauses
- [ ] Enxugar `get_active_session`, `sync_chat_session`, `list_known_chat_ids` (≤ 3 linhas, 0-1 condicional cada)
- [ ] Testes: `test_session_service.py` (caracterizados na Fase 0)
- [ ] Commit: `refactor(telegram): session_service repository scope`

### 1.5 `finance_api/services/import_strategies.py:113` — `SetCategoryBulkStrategy.execute` (5 `if`s)
**Padrão:** dispatch table por `TransactionKind` (`python-pattern-strategy`).

```python
repo = self._repositories_by_kind[tx.kind]  # {EXPENSE: category_repo, INCOME: income_category_repo}
if not await repo.get_by_key(clean_cat):
    return StepOutcome(status=StepOutcomeStatus.ERROR, error_message=f"Categoria '{clean_cat}' não existe")
```

- [ ] Substituir a validação duplicada EXPENSE/INCOME pelo dispatch
- [ ] Extrair `_learn_rule(tx, req)` para o bloco `remember and merchant`
- [ ] Testes: `test_import_strategies.py`
- [ ] Commit: `refactor(imports): kind dispatch in SetCategoryBulkStrategy`

### 1.6 `finance_api/services/balances.py:90` — `_resolve_pm_invoice_period` (4 `if`s, 40 LOC)
⚠️ Arquivo com WIP — **reavaliar após Fase 0.1**; pode já ter sido resolvido.

- [ ] Re-medir após commit do WIP; se mantiver violação, extrair resolução de período por PM para helper puro
- [ ] Usar `DateRange` (Regra 6) onde houver matemática de datas
- [ ] Testes: `test_balances.py`
- [ ] Commit (se necessário): `refactor(balances): extract pm invoice period resolution`

---

## Critérios de aceite da fase (gates)

- [ ] Nenhuma função em `*/services/` com > 3 condicionais (ou justificativa documentada)
- [ ] Zero instanciação de dependência dentro de método nos services tocados
- [ ] Zero `getattr` defensivo contra entidade tipada
- [ ] `ruff C90/PLR0912` sem violação nos arquivos tocados
- [ ] `make format` && `make lint` && `uv run pytest` verdes
- [ ] Nenhuma mudança de contrato HTTP

---

## Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| — | — | — | — |
