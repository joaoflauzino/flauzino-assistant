# Fase 6 — Padronização de Módulos em Todo o Repo + Gate de Arquitetura

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** 🟨 Em andamento (2026-11-02 — 6.1 concluída) · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** Fase 0 concluída · **6.1 entra entre 3.4 e 3.5** (antes de 3.5/3.7 e das Fases 4–5) · 6.4 depende de 3.3 · 6.5 depende da Fase 4 concluída
> **Commits previstos:** 5
> **Meta:** o repositório inteiro segue o mesmo critério de organização de módulos, e esse critério é verificado automaticamente (política como código), não por review.

---

## 0. Por que esta fase existe

A Fase 3.7 empacota **um** cluster (`services/import_*`). Sem um critério repetível e um gate automático, cada feature nova pode recriar o mesmo problema com outro prefixo — foi exatamente o que aconteceu com `import_*`. Esta fase fixa o critério (Regra 8 do `python-modular-code-organization`), aplica-o ao inventário atual das 4 APIs e transforma a regra em teste.

**Critério (skill Regra 8):** um grupo de módulos no mesmo diretório que compartilha prefixo/domínio vira **pacote de domínio plano** quando tem **≥ 5 arquivos** ou **≥ 800 LOC**, e as dependências internas formam uma DAG. Abaixo disso, mantém-se plano (Regra 6).

---

## 1. Inventário medido (2026-11-02, produção — testes excluídos)

| Diretório | Arqs | LOC | Cluster detectado | Regra | Ação |
|---|---:|---:|---|---|---|
| `finance_api/services` | 34 | 4.290 | `import_*`: **12 / 1.606** | A | pacote `services/imports/` → **3.7** |
| `finance_api/services` | — | — | `payment_*`: 3 / 211 | A (abaixo do limiar) | manter plano |
| `finance_api/services` | — | — | `classification_*` + `ai_classifier`: 3 / 457 | A (abaixo) | watchlist pós-3.7 |
| `finance_api/importers` | 6 | 797 | `c6_*`: 3 / 506 | A (abaixo) | watchlist (Nubank/Itaú) |
| `telegram_api/handlers` | 8 | 1.235 | `*_handler` repete o pacote | D | renomear → **6.5** |
| `telegram_api/services` | 1 | — | `session_service` repete o pacote | D | renomear → **6.5** |
| `graph_api/services` | 1 | — | `graph_service` repete o pacote | D | renomear → **6.5** |
| `finance_api/utils` | 1 | 13 | pacote com um único módulo | junk drawer | achatar → **6.4** |
| `finance_api/mcp` | 3 | 287 | — | — | manter (bounded context legítimo) |
| `finance_api/models/__init__.py`, `agent_api/services/tools/__init__.py`, `telegram_api/services/__init__.py` | 3 | — | `__all__` em `__init__` interno | E | **3.6 / 5.3** |
| `import_strategies.py` 351 · `http_client.py` 421 · `expense_handler.py` 408 | 3 | — | arquivo > 300 LOC | B | **3.5 / 4.2 / 4.3** |

Fora do escopo deste gate: as 56 funções top-level com `_` (Regra 4) já estão nas Fases 4.5/5.x; e a padronização de *nomes de função* não é organização de módulos.

---

## 2. Tarefas

### 6.1 Gate de arquitetura (política como código) — **checkpoint entre 3.4 e 3.5**
Objetivo: impedir que as fases seguintes (3.5, 3.7, 4.x e 5.x) ou qualquer feature futura reintroduzam o problema. Posicionado **depois** das tarefas que só reduzem dívida (3.1–3.4) e **antes** das mudanças estruturais (3.5 e 3.7) — assim o baseline já nasce menor e cada mudança estrutural seguinte tem prova automática ("antes/depois"), sem editar a allowlist em commits de dívida.

- [x] Criar `tests/architecture/test_module_organization.py` (+ `tests/architecture/__init__.py`)
- [x] Adicionar `"tests"` a `testpaths` no `pyproject.toml` (hoje só as 4 APIs são coletadas) e corrigir `make test-mcp`, que aponta para `tests/finance_api/test_mcp_tools.py` (inexistente — o real é `finance_api/tests/test_mcp_tools.py`)
- [x] Implementar as 5 checagens (somente código de produção; `tests/` e `__pycache__` ignorados):

| Regra | Checagem | Falha quando | Baseline hoje |
|---|---|---|---|
| **A** | Cluster por prefixo | grupo no mesmo diretório com ≥ 5 módulos **ou** ≥ 800 LOC | `services/import_*` (12/1.606) → 3.7 |
| **B** | Tamanho de arquivo | arquivo de produção > 300 LOC | 3 arquivos → 3.5 / 4.2 / 4.3 |
| **C** | Nome de pacote | diretório cujo nome é keyword Python (`keyword.iskeyword`/`issoftkeyword`) | 0 (previne `services/import/`) |
| **D** | Módulo repete o pacote | `stem == pkg`, `stem.startswith(pkg + "_")` ou `stem.endswith("_" + singular(pkg))` | 10 módulos → 3.7 (some) + 6.5 |
| **E** | Superfície de pacote | `__all__` em `__init__.py` que não é da raiz da API | 3 arquivos → 3.6 / 5.3 |

- [x] Baseline como **allowlist explícita** (dict `caminho → fase que quita`), seguindo o padrão do `per-file-ignores` da Fase 0 — nunca `pytest.skip` genérico
- [x] Mensagem de falha acionável: caminho, regra violada, limiar e a Regra 8 da skill
- [x] Testes do próprio gate (casos sintéticos: cluster que estoura, módulo repetindo pacote, pacote keyword)
- [x] Commit: `test(architecture): enforce module organization rules`

### 6.2 Decisões do inventário (watchlist)
- [ ] Registrar no master plan §2.4 a decisão por cluster: **empacotar** / **manter plano** / **observar**
- [ ] Watchlist com gatilho medido, para reavaliar ao fim da Fase 6:
  - `finance_api/importers/c6_*` → empacotar `importers/c6/` quando chegar a **5 arquivos ou 800 LOC** (provável ao adicionar outro banco)
  - `finance_api/services/classification*` + `ai_classifier.py` → se ficarem órfãos após a 3.7, candidatos a `services/imports/classify.py` + `classification_chain.py`
  - `finance_api/services/payment_*` → abaixo do limiar; só reavaliar se passar de 5 arquivos
- [ ] Sem código nesta tarefa

### 6.3 Padrão de estrutura por API (documento normativo)
- [ ] Criar `08-estrutura-padrao-apis.md` com o shape canônico e as exceções permitidas:
  - **comum às 4 APIs**: `core/`, `routers/`, `services/`, `schemas/`, `tests/`
  - `repositories/` + `models/` quando há persistência (finance, agent, telegram)
  - `handlers/` no `telegram_api` = camada de adapter do Telegram (legítima)
  - `importers/`, `mcp/` no `finance_api` = bounded contexts legítimos
  - `graph_api` sem `models/`/`repositories/` = renderer stateless (registrar como intencional, não como dívida)
  - onde vai código novo de cada tipo (regra de decisão em 5 linhas)
- [ ] Commit: `docs(specs): document canonical API module layout`

### 6.4 Enxugar `finance_api/utils/` (pacote com um único módulo)
- [ ] `git mv finance_api/utils/text.py finance_api/core/text.py` e remover o pacote vazio
- [ ] Atualizar consumidores (`services/classification.py`, `services/classification_chain.py`, testes)
- [ ] **Depois da 3.3** (que consolida `normalize_text`/`_normalize` nesse arquivo) — ordem explícita
- [ ] Testes: `test_classification_service.py`, `test_classification_chain.py`, `test_extractors.py` + teste direto do módulo
- [ ] Commit: `refactor(core): flatten single-module utils package`

### 6.5 Renomes: módulo não repete o nome do pacote (Regra 8.2)
- [ ] `telegram_api/handlers/`: `expense_handler.py → expense.py`, `income_handler.py → income.py`, `message_handler.py → message.py`, `photo_handler.py → photo.py`, `voice_handler.py → voice.py`, `command_handler.py → command.py`, `balance_handler.py → balance.py`, `balance_summary_handler.py → balance_summary.py` (+ 7 testes espelhados)
- [ ] `telegram_api/services/session_service.py → session.py` e `graph_api/services/graph_service.py → graph.py` (classes mantêm `SessionService`/`GraphService`)
- [ ] Atualizar imports (`telegram_api/main.py`, `handlers/__init__.py`, `core/middleware.py`, testes)
- [ ] **Depois da Fase 4** (4.4 reescreve voice/photo/message; 4.5 mexe nos nomes de função) e da Fase 5
- [ ] Testes: suíte do `telegram_api` + `test_graph_service.py`, sem alterar asserts
- [ ] Commit: `refactor(telegram): drop redundant module suffixes per rule 8`

### 6.6 Zerar o baseline
- [ ] Re-medir as 5 regras; confirmar que 3.5, 3.6, 3.7, 4.2, 4.3, 5.3, 6.4 e 6.5 quitaram seus itens
- [ ] Remover **toda** a allowlist — o gate passa a ser estrito (nenhuma exceção)
- [ ] Se restar item estruturalmente justificável, registrar no `08-estrutura-padrao-apis.md` **e** na allowlist com justificativa (não deixar implícito)
- [ ] Commit: `chore(architecture): burn down module organization baseline`

---

## 3. Critérios de aceite da fase (gates)

- [ ] `tests/architecture/test_module_organization.py` verde **sem allowlist** (regras A–E)
- [ ] Nenhum pacote com nome de keyword Python
- [ ] Nenhum módulo repetindo o nome do pacote em que vive
- [ ] Nenhum pacote de um único módulo genérico (`utils/`)
- [ ] `services/imports/` é o único pacote de feature criado neste ciclo (3.7) e está plano
- [ ] `08-estrutura-padrao-apis.md` publicado e referenciado pelo master plan
- [ ] Watchlist registrada com gatilho mensurável e data
- [x] `make format` && `make lint` && `uv run pytest` verdes (incluindo o novo `tests/`)

---

## 4. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Allowlist virar dívida permanente ("congelou e esqueceu") | 6.6 é obrigatória, não opcional; cada item aponta a fase que o quita |
| Heurística de prefixo ser burlada por nomes (`importupload.py`) | Regra D complementa A; review usa a Regra 8 da skill; limiar documentado |
| Gate frágil gerar ruído e ser desativado | Só 5 regras medíveis, mensagens acionáveis, allowlist explícita; baseline inicial é de 17 itens (todos já mapeados em fases existentes) |
| Mudar `testpaths` alterar a coleta | Rodar a suíte completa e `make test` no mesmo commit; CI (`.github/workflows/feature.yml`) já executa pytest |
| Renomes da 6.5 conflitarem com Fases 4–5 | Ordem explícita: 6.5 só depois da Fase 5 |
| Escopo virar "reorganizar tudo" | Regra 8 só dispara acima do limiar; camadas (`routers/`, `schemas/`, `repositories/`) nunca se movem |

---

## 5. Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| 2026-11-02 | — (aguardando autorização) | 6.1 `tests/architecture/test_module_organization.py` com as 5 regras (A–E), baseline de **17 itens** (cada um apontando a fase que quita), 7 testes do próprio gate; `tests` entrou no `testpaths` e `make test-mcp` foi corrigido | 614 passed (+7 do gate) |

### Notas de execução

- **6.1** — o baseline foi validado como **exato** na data: 17 violações encontradas = 17 congeladas, 0 entradas obsoletas. A regra A já enxerga o cluster `import_*` (12/1.606) que a 3.7 vai empacotar; a regra B cobre os 3 arquivos grandes que 3.5/4.2/4.3 vão dividir.
- **Comportamento do allowlist** — o gate **só falha em violação nova**; entradas obsoletas não quebram a suíte, de propósito, para não gerar churn de allowlist a cada fase. A 6.6 apaga o allowlist inteiro e o gate passa a ser estrito.
- **Prova de que o gate morde** — criado manualmente um arquivo de 301 LOC em `finance_api/services/`; a suíte falhou com `[B|...__gate_probe.py] 301 LOC (> 300)`; arquivo removido em seguida. As 5 regras também têm testes sintéticos com `tmp_path`.
- **CI** — `tests/` agora é coletado no `uv run pytest`, que é exatamente o que o workflow `.github/workflows/feature.yml` executa.
