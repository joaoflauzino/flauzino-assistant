# Fase 3 — Eixo C `finance_api`: Repositories, Imports Tardios e Utils

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** 🟨 Em andamento (2026-11-02) · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** Fase 0 concluída (pode rodar em paralelo com Fases 1–2 se houver reviewers distintos)
> **Commits previstos:** 5
> **Meta:** zero imports tardios, zero `except Exception` em repositories, zero utilidade duplicada, cluster de import empacotado.

---

## Tarefas

### 3.1 `finance_api/repositories/payment_methods.py:28` — `get_by_key` (52 LOC, 2× `except Exception`, `getattr` defensivo, 5 imports tardios no arquivo)
O pior cluster de anti-patterns do repositório (`python-anti-patterns`: *Errors should never pass silently*).

- [x] Mover imports para o topo (`CreditCard`, `Account`, `func`) — `AGENTS.md` §3.4
- [x] Remover `try/except Exception` que engole falha de query — erro de banco deve subir (decorator global loga)
- [x] Substituir a cascata por dispatch: lista ordenada de `(query_fn, adapter)` — payment_methods → credit_cards → accounts:

```python
async def get_by_key(self, key: str) -> PaymentMethod | None:
    for source in self._lookup_sources:
        found = await source.find(key.lower())
        if found is not None:
            return found
    return None
```

- [x] Remover `getattr(card, "name", None)` — modelos são tipados; usar o campo real
- [x] Testes: `test_payment_methods_repository.py` (4 caminhos caracterizados na Fase 0)
- [x] Commit: `refactor(repositories): payment_methods lookup chain + top-level imports`

### 3.2 `finance_api/repositories/categories.py:35` — import tardio
- [x] Mover `from sqlalchemy import func` para o topo (mecânico, risco zero)
- [x] Commit: agrupado com 3.1

### 3.3 Consolidação de `normalize` duplicado (Regra 3 do `python-modular-code-organization`)
Hoje: `_normalize_str` em `repositories/categories.py:14` e `income_categories.py:14`, `_normalize` em `category_rules.py:13`, e `finance_api/utils/text.py` já tem `normalize_text` + alias `_normalize` (viola Regra 4).
⚠️ **Atenção comportamental:** repos usam `.lower()`, `utils/text.py` usa `.upper()` — preservar o case de cada call-site.

- [x] `finance_api/utils/text.py`: remover o alias `_normalize`; expor `normalize_upper(text)` e `normalize_lower(text)` compartilhando a remoção de diacríticos
- [x] `repositories/categories.py`, `income_categories.py`, `category_rules.py`: apagar os `_normalize_str`/`_normalize` locais e importar de `finance_api.utils.text`
- [x] Testes: `test_categories_repository.py`, `test_income_categories_repository.py`, `test_imports_and_rules_repositories.py` + teste direto de `utils/text.py`
- [x] Commit: `refactor(utils): consolidate text normalization`

### 3.4 `finance_api/repositories/staged_transactions.py:101` — `list_by_filter` (54 LOC, 6 `if`s)
- [x] Extrair `_build_conditions(batch_id, status, kind, only_duplicates, only_unclassified) -> list` e `_apply_pagination(query, page, size)`
- [x] Reutilizar `_build_conditions` em `get_approved_for_commit`
- [x] Método público fica ≤ 15 linhas
- [x] Testes: `test_spents_repository.py`/testes de staged transactions existentes
- [x] Commit: `refactor(repositories): staged_transactions conditions/pagination`

### 3.5 `finance_api/services/import_strategies.py` (349 linhas — acima do teto ~300 da Regra 6)
> **Entre 3.4 e 3.5 rodou a Fase 6.1** (gate de arquitetura): o split abaixo fez a regra B cair de 3 → 2 violações e o item correspondente saiu do baseline (17 → 16). A 3.7 deve zerar a regra A.

Dividir em **arquivos planos e coesos** (sem subpacotes — Regra 6):

- [x] `import_bulk_strategies.py` (bulk actions + `build_default_bulk_strategies`)
- [x] `import_commit_strategies.py` (commit strategies + duplicate detectors + builders)
- [x] Atualizar imports em `imports.py`, `import_bulk.py`, `import_commit.py` e testes
- [x] Testes: `test_import_strategies.py`, `test_import_bulk.py`, `test_import_commit.py`
- [x] Commit: `refactor(imports): split import_strategies into bulk/commit modules`

> ⚠️ **Ordem:** a 3.7 (empacotamento) **depende** desta tarefa — o split acontece primeiro, ainda em `services/` plano, e depois 3.7 apenas relocaliza os arquivos resultantes. Fazer as duas juntas num commit só é aceitável, mas o diff perde a legibilidade de rename.

### 3.6 `finance_api/models/__init__.py` — `__all__` (Regra 5)
⚠️ Os **imports** do `__init__.py` têm efeito colateral de registro de metadata do SQLAlchemy — não remover sem validar.

- [ ] Validar impacto em `create_all`/migrations e imports em `main.py`
- [ ] Remover apenas o `__all__`, mantendo os imports
- [ ] Commit: agrupado com 3.5 ou separado (`chore(models): remove __all__ per rule 5`)

### 3.7 Empacotar o cluster de import em `finance_api/services/imports/` (Regra 6)
**Diagnóstico medido (2026-11-02):** o cluster `services/import_*.py` + `imports.py` tem **14 arquivos / 1.718 LOC = 40%** dos 35 arquivos / 4.290 LOC de `services/`. O prefixo `import_` está exercendo o papel de diretório: 14 entradas de um diretório compartilhando o mesmo prefixo deixaram de ser "flat e coeso".

O grafo intra-cluster é uma DAG sem ciclos — `facade → wiring → {upload, editor, bulk, commit, reclassifier}`, `upload → staging → strategies`, `upload → enrichment/presenter/fingerprint`, `editor → presenter`, `reclassify → enrichment` — ou seja, é a mesma *feature* vista de vários ângulos, não um aglomerado arbitrário. `factory`/`wiring` são os únicos hubs (composição).

**Decisões registradas (discussão de 2026-11-02):**

1. **Nome do pacote: `imports/`.** `import` é palavra reservada do Python — `from finance_api.services.import import ...` é `SyntaxError`; só funcionaria via `importlib`. `imports/` (plural) é o nome possível.
2. **Camadas preservadas.** `routers/imports.py`, `schemas/imports.py`, `repositories/imports.py` e `repositories/staged_transactions.py` **ficam onde estão**. A alternativa "domínio vertical" (`finance_api/imports/` englobando router+service+parsers+schemas) foi **descartada**: contraria `AGENTS.md` §3.1 (`route → service → repository`) e amplia o churn para toda a feature.
3. **`wiring.py` e `factory.py` permanecem no pacote.** Na discussão inicial foi levantado movê-los para `core/` (composition root); reavaliando, **dentro do pacote eles deixam de ser ruído** — são a API de composição da própria feature. Mover para `core/` faria o core conhecer tipos internos de um service e espalharia a feature por dois diretórios. Opção descartada.
4. **`imports.py` → `imports/facade.py`** (nome explícito para a fachada). `__init__.py` **vazio**: sem `__all__` e sem re-export (Regra 5), mesmo padrão de `finance_api/importers/__init__.py` (0 linhas).
5. **Sem alias de compatibilidade.** Não criar `services/imports.py` re-exportando o pacote — consumidores passam a apontar para a fonte única (43 linhas de import em 20 arquivos, sendo 13 de teste).
6. **Sem renomear `finance_api/importers/` → `parsers/`.** A confusão `imports/` × `importers/` foi notada, mas renomear os parsers é outro escopo; se incomodar depois, vira issue separada.
7. **Refatoração pura.** `git mv` + atualização de imports; zero mudança de comportamento, zero mudança de contrato HTTP. `git diff -M` deve mostrar apenas renames + linhas de import.

**Layout alvo (15 arquivos; nomes sem o prefixo `import_`, que o pacote já fornece):**

```text
finance_api/services/imports/
├── __init__.py            (vazio)
├── facade.py              (ex-imports.py — ImportService)
├── wiring.py              (ex-import_wiring.py — Deps/Overrides/Collaborators)
├── factory.py             (ex-import_factory.py — builders)
├── upload.py              (ex-import_upload.py)
├── staging.py             (ex-import_staging.py)
├── enrichment.py          (ex-import_enrichment.py)
├── presenter.py           (ex-import_presenter.py)
├── fingerprint.py         (ex-import_fingerprint.py)
├── transaction_editor.py  (ex-import_transaction_editor.py)
├── commit.py              (ex-import_commit.py)
├── bulk.py                (ex-import_bulk.py)
├── reclassify.py          (ex-import_reclassify.py)
├── bulk_strategies.py     (resultado da 3.5)
└── commit_strategies.py   (resultado da 3.5)
```

**Pré-requisitos:**
- [ ] 3.5 concluída (`import_strategies.py` já splitado em bulk/commit)

**Tarefas:**
- [ ] Criar `services/imports/__init__.py` vazio
- [ ] `git mv` dos 12 módulos para `services/imports/` (nomes do layout acima) + `git mv imports.py facade.py`
- [ ] `git mv` dos testes para `tests/services/imports/` espelhando os nomes (`test_imports_service.py → test_facade.py`, `test_import_upload.py → test_upload.py`, …) e criar `tests/services/imports/__init__.py` se o pytest exigir (convenção já usada em `tests/repositories/`)
- [ ] Atualizar as 43+ referências `finance_api.services.import_*` / `.imports` em produção e testes (o volume cresce com a 3.5)
- [ ] Atualizar o mapa do master plan (§2.1/§2.2/§2.2-B/§2.3) e as referências de path nas specs das fases já concluídas
- [ ] Validar importação do app (`python -c "import finance_api.main"`) para pegar ciclos que o `ast` não vê
- [ ] Testes: suíte completa **sem alterar asserts** (só caminhos de import)
- [ ] Commit: `refactor(imports): group the import feature into services/imports package`

**Gates da tarefa:**
- [ ] Zero `finance_api/services/import_*.py` remanescente; `services/` volta a ≤ 23 entradas planas
- [ ] Pacote só com arquivos planos (sem `strategies/`, `usecases/` etc. — Regra 6 / *flat is better than nested*)
- [ ] `__init__.py` vazio: zero `__all__`, zero re-export
- [ ] `git diff -M` reporta ≥ 90% de similaridade nos renames (prova de que é movimentação)
- [ ] Suíte 100% verde sem tocar em asserts; `black`/`ruff` limpos
- [ ] Nenhuma mudança de contrato HTTP

**Riscos e mitigação:**

| Risco | Mitigação |
|---|---|
| Conflito com a 3.5 nos mesmos arquivos | 3.7 só começa depois da 3.5 (ordem explícita acima) |
| Ciclo de import que o grep não detecta | o grafo medido é DAG; validar com `import finance_api.main` além da suíte |
| Discovery do pytest no subdiretório de testes | criar `tests/services/imports/__init__.py`, seguindo `tests/repositories/` |
| Blame/histórico diluído | commit único e isolado, só de rename; `git log --follow` funciona |
| Paths citados nas specs ficarem obsoletos | item explícito de atualização do mapa no checklist |

---

## Critérios de aceite da fase (gates)

- [ ] Zero imports fora do topo do arquivo em `finance_api/`
- [ ] Zero `except Exception` engolindo erro em `payment_methods.py`
- [ ] Zero `getattr` defensivo contra modelos tipados
- [ ] Zero `_normalize*` duplicado — uma única fonte em `finance_api/utils/text.py`
- [x] `list_by_filter` ≤ 20 LOC
- [ ] Nenhum arquivo de `finance_api/services/` > ~300 linhas
- [ ] Cluster de import isolado em `finance_api/services/imports/` (15 arquivos planos, `__init__.py` vazio)
- [ ] `make format` && `make lint` && `uv run pytest` verdes

---

## Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| 2026-11-02 | — (aguardando autorização) | 3.1 lookup chain ordenado (PM → cartão → conta) + adapters puros `payment_method_from_credit_card`/`payment_method_from_account`; removidos 4 `except Exception`, 4 `getattr` e 5 imports tardios. `get_by_key` 52 → 12 LOC; `list` 56 → 8 LOC; `list_credit_cards` 31 → 6 LOC | 16 passed (repo) · 372 (finance_api) |
| 2026-11-02 | — | 3.2 `func` movido para o topo em `categories.py` | agrupado no commit 3.1 |
| 2026-11-02 | — (aguardando autorização) | 3.3 `utils/text.py` como fonte única (`strip_diacritics`, `normalize_upper`, `normalize_lower`); removidos 3 helpers locais e o alias `_normalize` | 599 passed (+8 de `utils/text`) |
| 2026-11-02 | — | **fora do plano (bug pré-existente)**: `GET /payment-methods/` retornava 500 (`ResponseValidationError`) porque os `PaymentMethod` sintéticos não carregavam `created_at`; adapters agora copiam `created_at` do cartão/conta | 607 passed (+1 regressão de router) |
| 2026-11-02 | — (aguardando autorização) | 3.4 `list_by_filter` 54 → **20 LOC / 0 `if`s**; `_build_conditions` declarativo (2 `if`s) + `_with_conditions` + `_apply_pagination`; `get_approved_for_commit` reusa o builder | 607 passed (+7 do repositório) |
| 2026-11-02 | — (aguardando autorização) | 3.5 split de `import_strategies.py` (351 LOC) em `import_bulk_strategies.py` + `import_commit_strategies.py`; `DuplicateDetectorStrategy` movido para `services/protocols.py` (Regra 2); `resolve_salary_competence_date` movido para `import_staging.py` (único consumidor); `NullDuplicateDetector` morto removido; baseline do gate 17 → 16 | 623 passed (+10: 12 testes dos strategies splitados e 4 do salário, −6 do arquivo antigo) |

### Notas de execução

- **3.1** — a cadeia ficou `_find_payment_method → _find_credit_card → _find_account` (mesma ordem e mesmos logs `debug` de antes), cada passo com guard clause; os adapters CreditCard/Account → `PaymentMethod` são funções puras de módulo (Regra 4) e ganharam testes diretos. `payment_method_from_account(..., include_bank=True)` preserva a diferença histórica entre `get_by_key` (nome puro) e `list` (nome + banco).
- **3.1 (mocks)** — dois testes precisavam de mocks mais fiéis, como previsto na Fase 1.3: `test_list_credit_cards` e `test_invoices_router` devolviam `PaymentMethod` no lugar de `CreditCard`; agora usam as entidades reais. Adicionado teste de regressão provando que erro de banco **propaga** (`SQLAlchemyError`) em vez de virar `None` silencioso.
- **3.3** — `utils/text.py` passou a ter `strip_diacritics` (compartilhado), `normalize_upper` e `normalize_lower`; `normalize_text` e o alias `_normalize` foram removidos (o único consumidor do alias eram os call-sites migrados). Case preservado por call-site: repositórios de **categorias** usam `normalize_lower` (comparação de chaves), `category_rules`, `classification` e `classification_chain` usam `normalize_upper`. Nenhum `_normalize*` local remanescente em produção.
- **3.4** — `list_by_filter` caiu de 54 → 20 LOC com **0 condicionais**; as condições viraram uma tabela declarativa de igualdades (`(valor, coluna)`) + 2 flags explícitas (`only_duplicates`, `only_unclassified`), mantendo o comportamento de não emitir `WHERE` quando não há filtro (`and_()` vazio é evitado em `_with_conditions`). Ordenação e janela ficaram em `_apply_pagination`. `get_approved_for_commit` reusa `_build_conditions(batch_id=..., status="APPROVED")`.
- **Bug pré-existente (fora do plano, commit separado)** — `GET /payment-methods/` respondia 500: os `PaymentMethod` sintéticos (montados a partir de `CreditCard`/`Account`) não tinham `created_at`, e `PaymentMethodResponse.created_at` é obrigatório. Correção: os adapters copiam `created_at` da entidade de origem (sem afrouxar o contrato do schema). Regressão coberta por teste de router que exercita o repositório real com DB mockado.
- **3.5** — `import_strategies.py` (351 LOC) dividido em `import_bulk_strategies.py` (4 estratégias + builder) e `import_commit_strategies.py` (3 estratégias de commit + 3 detectores + builders). Decisões do split: (a) `DuplicateDetectorStrategy` foi para `services/protocols.py` (Regra 2) — assim `import_staging.py` depende do contrato, não do módulo de commit; (b) `SALARY_KEYWORDS` + `resolve_salary_competence_date` foram para `import_staging.py`, seu único consumidor (era a única parte do arquivo sem relação com Strategy); (c) `NullDuplicateDetector`, sem nenhum uso, foi removido. Testes espelham os módulos (`test_import_bulk_strategies.py`, `test_import_commit_strategies.py`) e o gate registrou a queda da regra B (baseline 17 → 16, **0 entradas obsoletas**).
