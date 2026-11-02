# Fase 3 — Eixo C `finance_api`: Repositories, Imports Tardios e Utils

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** ⬜ Não iniciada · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** Fase 0 concluída (pode rodar em paralelo com Fases 1–2 se houver reviewers distintos)
> **Commits previstos:** 4
> **Meta:** zero imports tardios, zero `except Exception` em repositories, zero utilidade duplicada.

---

## Tarefas

### 3.1 `finance_api/repositories/payment_methods.py:28` — `get_by_key` (52 LOC, 2× `except Exception`, `getattr` defensivo, 5 imports tardios no arquivo)
O pior cluster de anti-patterns do repositório (`python-anti-patterns`: *Errors should never pass silently*).

- [ ] Mover imports para o topo (`CreditCard`, `Account`, `func`) — `AGENTS.md` §3.4
- [ ] Remover `try/except Exception` que engole falha de query — erro de banco deve subir (decorator global loga)
- [ ] Substituir a cascata por dispatch: lista ordenada de `(query_fn, adapter)` — payment_methods → credit_cards → accounts:

```python
async def get_by_key(self, key: str) -> PaymentMethod | None:
    for source in self._lookup_sources:
        found = await source.find(key.lower())
        if found is not None:
            return found
    return None
```

- [ ] Remover `getattr(card, "name", None)` — modelos são tipados; usar o campo real
- [ ] Testes: `test_payment_methods_repository.py` (4 caminhos caracterizados na Fase 0)
- [ ] Commit: `refactor(repositories): payment_methods lookup chain + top-level imports`

### 3.2 `finance_api/repositories/categories.py:35` — import tardio
- [ ] Mover `from sqlalchemy import func` para o topo (mecânico, risco zero)
- [ ] Commit: agrupado com 3.1

### 3.3 Consolidação de `normalize` duplicado (Regra 3 do `python-modular-code-organization`)
Hoje: `_normalize_str` em `repositories/categories.py:14` e `income_categories.py:14`, `_normalize` em `category_rules.py:13`, e `finance_api/utils/text.py` já tem `normalize_text` + alias `_normalize` (viola Regra 4).
⚠️ **Atenção comportamental:** repos usam `.lower()`, `utils/text.py` usa `.upper()` — preservar o case de cada call-site.

- [ ] `finance_api/utils/text.py`: remover o alias `_normalize`; expor `normalize_upper(text)` e `normalize_lower(text)` compartilhando a remoção de diacríticos
- [ ] `repositories/categories.py`, `income_categories.py`, `category_rules.py`: apagar os `_normalize_str`/`_normalize` locais e importar de `finance_api.utils.text`
- [ ] Testes: `test_categories_repository.py`, `test_income_categories_repository.py`, `test_imports_and_rules_repositories.py` + teste direto de `utils/text.py`
- [ ] Commit: `refactor(utils): consolidate text normalization`

### 3.4 `finance_api/repositories/staged_transactions.py:101` — `list_by_filter` (54 LOC, 6 `if`s)
- [ ] Extrair `_build_conditions(batch_id, status, kind, only_duplicates, only_unclassified) -> list` e `_apply_pagination(query, page, size)`
- [ ] Reutilizar `_build_conditions` em `get_approved_for_commit`
- [ ] Método público fica ≤ 15 linhas
- [ ] Testes: `test_spents_repository.py`/testes de staged transactions existentes
- [ ] Commit: `refactor(repositories): staged_transactions conditions/pagination`

### 3.5 `finance_api/services/import_strategies.py` (349 linhas — acima do teto ~300 da Regra 6)
Dividir em **arquivos planos e coesos** (sem subpacotes — Regra 6):

- [ ] `import_bulk_strategies.py` (bulk actions + `build_default_bulk_strategies`)
- [ ] `import_commit_strategies.py` (commit strategies + duplicate detectors + builders)
- [ ] Atualizar imports em `imports.py`, `import_bulk.py`, `import_commit.py` e testes
- [ ] Testes: `test_import_strategies.py`, `test_import_bulk.py`, `test_import_commit.py`
- [ ] Commit: `refactor(imports): split import_strategies into bulk/commit modules`

### 3.6 `finance_api/models/__init__.py` — `__all__` (Regra 5)
⚠️ Os **imports** do `__init__.py` têm efeito colateral de registro de metadata do SQLAlchemy — não remover sem validar.

- [ ] Validar impacto em `create_all`/migrations e imports em `main.py`
- [ ] Remover apenas o `__all__`, mantendo os imports
- [ ] Commit: agrupado com 3.5 ou separado (`chore(models): remove __all__ per rule 5`)

---

## Critérios de aceite da fase (gates)

- [ ] Zero imports fora do topo do arquivo em `finance_api/`
- [ ] Zero `except Exception` engolindo erro em `payment_methods.py`
- [ ] Zero `getattr` defensivo contra modelos tipados
- [ ] Zero `_normalize*` duplicado — uma única fonte em `finance_api/utils/text.py`
- [ ] `list_by_filter` ≤ 20 LOC
- [ ] Nenhum arquivo de `finance_api/services/` > ~300 linhas
- [ ] `make format` && `make lint` && `uv run pytest` verdes

---

## Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| — | — | — | — |
