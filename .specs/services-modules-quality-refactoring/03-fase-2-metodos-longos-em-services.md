# Fase 2 — Eixo B: Métodos Longos nos Services

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** ✅ Concluída (2026-11-02) · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** Fase 1 concluída
> **Commits previstos:** 3
> **Meta:** nenhum método de service > 40 LOC sem justificativa documentada.

---

## Tarefas

### 2.1 `finance_api/services/imports.py:57` — `ImportService.__init__` (97 LOC, 16 parâmetros)
**Padrão:** Factory (`python-pattern-factory`).

- [x] Criar `build_default_import_service(...)` (em `finance_api/core/dependencies.py` ou `services/import_factory.py`) montando os 8 colaboradores internos
- [x] Construtor da classe mantém apenas atribuições explícitas (≤ 20 linhas); colaboradores individuais seguem injetáveis (testes não mudam)
- [x] `dependencies.py` do FastAPI passa a usar a factory (elimina wiring duplicado)
- [x] Testes: `test_imports_service.py`, `test_imports_router.py` (regressão de wiring)
- [x] Commit: `refactor(imports): factory for ImportService wiring`

### 2.2 `agent_api/services/ocr.py:63` — `extract_text` (46 LOC)
- [x] Extrair leitura de arquivo (I/O), chamada ao pytesseract e `clean_extracted_text` (puro → `agent_api/services/utils.py`)
- [x] `extract_text` vira orquestração linear ≤ 15 linhas
- [x] Testes: `test_ocr_service.py`
- [x] Commit: agrupado com 2.3–2.5 em `refactor(services): decompose long methods (ocr, incomes, ai_classifier, graph tool)`

### 2.3 `finance_api/services/incomes.py:148` — `get_monthly_summary` (45 LOC)
- [x] Extrair agregações para funções puras (`summarize_incomes`, `summarize_spents`) — testáveis sem banco
- [x] Método público fica: `DateRange` → fetches → agregação → montagem
- [x] Testes: `test_incomes_service.py` + testes novos das funções puras

### 2.4 `finance_api/services/ai_classifier.py:17` — `classify_batch` (43 LOC, prof. 3)
- [x] Separar: montagem do payload (puro) / chamada ao LLM (único `try`) / sanitização das sugestões
- [x] Espelhar o padrão já aplicado em `agent_api/services/classify.py`
- [x] Testes: `test_classification_service.py` / novos testes do classifier

### 2.5 `agent_api/services/tools/graph.py:18,26` — `build_gerar_grafico`/`gerar_grafico` (51/41 LOC)
- [x] Mover montagem de payload/validação para helpers públicos no módulo (Regra 4)
- [x] **Preservar docstring e assinatura do `@tool` intactas** (contrato do LLM)
- [x] Testes: `test_tools.py`

### 2.6 Casos a documentar em vez de decompor (Regra 6 — evitar fragmentação sem ganho)
- [x] Registrar decisão no master plan: `import_staging._to_staged` (45 LOC, 0 `if`, mapping puro) e `importers/c6_credit_card_csv._parse_row` (50 LOC, 2 `if`s) são **aceitos com justificativa** (baixa complexidade cognitiva)
- [x] Se o gate `PLR0915` reclamar: `# noqa` comentado com referência a esta spec

---

## Critérios de aceite da fase (gates)

- [x] Nenhum método de service > 40 LOC sem justificativa documentada (§2.6)
- [x] `ImportService.__init__` ≤ 20 LOC e ≤ ~8 parâmetros diretos
- [x] Docstrings de `@tool` do agent_api inalteradas
- [x] Funções puras novas com testes unitários próprios
- [x] `make format` && `make lint` && `uv run pytest` verdes
- [x] Nenhuma mudança de contrato HTTP

### Notas de execução

- **2.1** — três módulos novos: `services/import_wiring.py` (dataclasses `ImportServiceDeps`, `ImportOverrides` e `ImportCollaborators` — Regra 1), `services/import_factory.py` (factory + builders por colaborador, 0 condicionais, todos ≤ 30 LOC) e `services/imports.py`, que ficou só com a fachada. `__init__` agora recebe `(deps, collaborators)` = **16 LOC / 2 parâmetros** (era 97 LOC / 16 parâmetros). A separação em dois módulos evita o ciclo `imports ⇄ import_factory`. O fixture de `test_imports_service.py` troca apenas a linha de construção por `build_default_import_service(deps, ImportOverrides(ai_client=...))`; `get_import_service` mantém a assinatura pública (o teste de wiring do router não mudou).
- **2.2** — `run_tesseract` (chamada ao pytesseract) fica em `ocr.py`; `clean_extracted_text` e `average_confidence` (puros) foram para `agent_api/services/utils.py`. Os `patch("agent_api.services.ocr.pytesseract...")` existentes continuam válidos.
- **2.3** — `finance_api/services/utils.py` (novo, Regra 3) concentra `sum_amounts`, `group_amounts_by_category`, `compute_savings_rate`, `compute_percentage_used`, `build_category_balance` e `build_monthly_summary`; o `Protocol` de entrada ficou em `services/protocols.py` como `CategorizedAmountProtocol` (Regra 2). Além de `get_monthly_summary` (20 LOC), **`balances._build_balances` (44 → 28 LOC)** também foi decomposto aqui, conforme mapa do master plan §2.2.
- **2.4** — `build_classify_payload`/`extract_suggestions` são públicas e puras; a bifurcação HTTP ficou em `_post` (único `try`, agora `except httpx.HTTPError`) e `_decode` (`except ValueError`). O `except Exception` genérico do caminho LLM foi eliminado; o fallback (`{}, False`) e os logs de warning continuam idênticos.
- **2.5** — `build_chart_command` monta o `Command`/`ToolMessage`; `gerar_grafico` (31 LOC com docstring) devolve a mensagem sem dados por guard clause. Docstring e assinatura da `@tool` **não foram tocadas**. `build_gerar_grafico` mede 41 LOC porque envolve o `@tool` aninhado + docstring congelada — aceito em §2.6.
- **2.6** — decidido manter `import_staging._to_staged` (45 LOC, 0 `if`, 0 aninhamento: mapping campo-a-campo) e `c6_credit_card_csv._parse_row` (50 LOC, 2 `if`, prof. 1) e `tools/graph.build_gerar_grafico` (41 LOC, 1 `if`) como estão: decompor produziria fragmentos sem coesão e arriscaria o contrato do LLM/parser. Nenhum gate do `ruff` (`PLR0912`/`PLR0915`/`C90`) reclama deles, então não foi necessário `# noqa`.
- **Testes** — 582 passed (552 da Fase 1 + 30 novos: 10 de `agent_api/services/utils` + ocr, 13 de `finance_api/services/utils` + balances, 8 do `ai_classifier`, 2 do `build_chart_command`).

---

## Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| 2026-11-02 | — (aguardando autorização) | 2.1 factory de wiring (`import_wiring.py` + `import_factory.py`), `__init__` 97 → 16 LOC | 14 passed (imports service/router) |
| 2026-11-02 | — | 2.2 `run_tesseract` + `clean_extracted_text`/`average_confidence` puros | 21 passed (ocr/utils) |
| 2026-11-02 | — | 2.3 `build_monthly_summary` puro + `get_monthly_summary` 45 → 20 LOC + `_build_balances` 44 → 28 LOC | 20 passed (utils/balances/incomes) |
| 2026-11-02 | — | 2.4 `classify_batch` 43 → 25 LOC, exceções específicas e fallback preservado | 8 passed (`ai_classifier`) |
| 2026-11-02 | — | 2.5 `build_chart_command` extraído; `@tool` intacta | 12 passed (tools) |
| 2026-11-02 | — | 2.6 casos aceitos documentados no master plan §2.6 | 582 passed · black/ruff limpos |
