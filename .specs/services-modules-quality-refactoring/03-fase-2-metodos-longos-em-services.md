# Fase 2 — Eixo B: Métodos Longos nos Services

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** ⬜ Não iniciada · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** Fase 1 concluída
> **Commits previstos:** 3
> **Meta:** nenhum método de service > 40 LOC sem justificativa documentada.

---

## Tarefas

### 2.1 `finance_api/services/imports.py:57` — `ImportService.__init__` (97 LOC, 16 parâmetros)
**Padrão:** Factory (`python-pattern-factory`).

- [ ] Criar `build_default_import_service(...)` (em `finance_api/core/dependencies.py` ou `services/import_factory.py`) montando os 8 colaboradores internos
- [ ] Construtor da classe mantém apenas atribuições explícitas (≤ 20 linhas); colaboradores individuais seguem injetáveis (testes não mudam)
- [ ] `dependencies.py` do FastAPI passa a usar a factory (elimina wiring duplicado)
- [ ] Testes: `test_imports_service.py`, `test_imports_router.py` (regressão de wiring)
- [ ] Commit: `refactor(imports): factory for ImportService wiring`

### 2.2 `agent_api/services/ocr.py:63` — `extract_text` (46 LOC)
- [ ] Extrair leitura de arquivo (I/O), chamada ao pytesseract e `clean_extracted_text` (puro → `agent_api/services/utils.py`)
- [ ] `extract_text` vira orquestração linear ≤ 15 linhas
- [ ] Testes: `test_ocr_service.py`
- [ ] Commit: agrupado com 2.3–2.5 em `refactor(services): decompose long methods (ocr, incomes, ai_classifier, graph tool)`

### 2.3 `finance_api/services/incomes.py:148` — `get_monthly_summary` (45 LOC)
- [ ] Extrair agregações para funções puras (`summarize_incomes`, `summarize_spents`) — testáveis sem banco
- [ ] Método público fica: `DateRange` → fetches → agregação → montagem
- [ ] Testes: `test_incomes_service.py` + testes novos das funções puras

### 2.4 `finance_api/services/ai_classifier.py:17` — `classify_batch` (43 LOC, prof. 3)
- [ ] Separar: montagem do payload (puro) / chamada ao LLM (único `try`) / sanitização das sugestões
- [ ] Espelhar o padrão já aplicado em `agent_api/services/classify.py`
- [ ] Testes: `test_classification_service.py` / novos testes do classifier

### 2.5 `agent_api/services/tools/graph.py:18,26` — `build_gerar_grafico`/`gerar_grafico` (51/41 LOC)
- [ ] Mover montagem de payload/validação para helpers públicos no módulo (Regra 4)
- [ ] **Preservar docstring e assinatura do `@tool` intactas** (contrato do LLM)
- [ ] Testes: `test_tools.py`

### 2.6 Casos a documentar em vez de decompor (Regra 6 — evitar fragmentação sem ganho)
- [ ] Registrar decisão no master plan: `import_staging._to_staged` (45 LOC, 0 `if`, mapping puro) e `importers/c6_credit_card_csv._parse_row` (50 LOC, 2 `if`s) são **aceitos com justificativa** (baixa complexidade cognitiva)
- [ ] Se o gate `PLR0915` reclamar: `# noqa` comentado com referência a esta spec

---

## Critérios de aceite da fase (gates)

- [ ] Nenhum método de service > 40 LOC sem justificativa documentada (§2.6)
- [ ] `ImportService.__init__` ≤ 20 LOC e ≤ ~8 parâmetros diretos
- [ ] Docstrings de `@tool` do agent_api inalteradas
- [ ] Funções puras novas com testes unitários próprios
- [ ] `make format` && `make lint` && `uv run pytest` verdes
- [ ] Nenhuma mudança de contrato HTTP

---

## Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| — | — | — | — |
