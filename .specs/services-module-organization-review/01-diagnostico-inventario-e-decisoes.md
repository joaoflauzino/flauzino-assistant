# Diagnóstico de Organização dos Services — Inventário e Matriz de Decisão

> **Spec de origem:** [00-diagnostic-plan.md](./00-diagnostic-plan.md)
> **Fases executadas:** 0, 1 e 2 (inventário, coesão/dependências, alternativas e recomendação)
> **Status:** 🔵 Diagnóstico concluído — **aguarda revisão humana** (fase 3 bloqueada até aprovação explícita)
> **Escopo medido:** `finance_api/services/` e `agent_api/services/` (produção, sem `__pycache__`)
> **Data da medição:** 2026-11-02
> **Nenhuma mudança de código, de import ou de comportamento foi feita nesta fase.**

---

## 0. Sumário executivo

1. **Nenhum agrupamento atinge o gatilho da Regra 8** (≥ 5 módulos com o mesmo prefixo **ou** ≥ 800 LOC). O maior cluster é `classification*` com 2 módulos/359 LOC; `payment*` tem 3 módulos/211 LOC. Portanto **não há dívida contra o critério vigente**: o gate `tests/architecture/test_module_organization.py` passa com **0 violações** (7 testes, verificado nesta fase).
2. **A percepção de desorganização não vem do número de arquivos, e sim de um único módulo**: `finance_api/services/protocols.py` é um *contract bag* — 13 contratos de 4 features distintas, com `httpx`, models e repositories importados no topo. Ele é o único ponto do diagnóstico com defeito objetivo (não apenas estético).
3. **Nenhum pacote novo deve ser criado.** Os 6 candidatos do §1 da spec devem permanecer planos. O único trabalho estrutural recomendado é uma **separação local sem pacote** em `protocols.py`, com impacto mensurável e comportamento zero-variação.
4. `services/imports/` e `services/tools/` confirmam-se como **referências corretas** de pacote plano (ponto de entrada único, `__init__` sem `__all__`, sem subpacotes, nomes sem repetir o pacote).
5. Recomendação de política: **manter a Regra 8 intacta** e complementá-la com um *checklist de admissão semântica* (documentação, não gate). Uma regra automatizada nova (F) só faz sentido **depois** do split de `protocols.py`, nunca antes — caso contrário congelaria a dívida atual no baseline.

---

## 1. Método e evidências

### 1.1 O que foi medido

| Medida | Como foi obtida |
|---|---|
| LOC por módulo | `wc -l` sobre `*.py` de produção |
| Superfície pública | `grep '^class \|^def \|^async def'` |
| Imports service → service | `grep '^from finance_api.services\|^from agent_api.services'` |
| Consumidores de produção | `grep -rn 'services\.<módulo>'` excluindo o próprio módulo, testes e `__pycache__` |
| Consumidores de teste | `grep -rl 'services\.<módulo>' <api>/tests` |
| Patch targets | `grep 'monkeypatch.setattr\|patch(' <api>/tests` |
| Gate de arquitetura | `uv run pytest tests/architecture/test_module_organization.py -q` → **7 passed** |

### 1.2 Números-base

| Diretório | Módulos de produção | LOC | Observação |
|---|---:|---:|---|
| `finance_api/services/` (raiz) | 21 | 2.594 | 1 `__init__.py` vazio |
| `finance_api/services/imports/` | 14 + `__init__` | 1.695 | pacote plano de referência |
| `finance_api/services/` (total) | 35 | 4.289 | 21 raiz + 14 do pacote |
| `agent_api/services/` (raiz) | 11 + `__init__` | 1.206 | |
| `agent_api/services/tools/` | 7 + `__init__` | 317 | pacote plano de referência |
| `agent_api/services/` (total) | 18 | 1.523 | 11 raiz + 7 das tools |

### 1.3 Clusters por prefixo (semântica exata do gate, Regra A)

| Prefixo | Módulos | LOC | Gatilho (≥5 arqs / ≥800 LOC) |
|---|---:|---:|---|
| `classification_` | 2 (`classification`, `classification_chain`) | 359 | ❌ não |
| `payment_` | 3 (`payment_methods`, `payment_resolution`, `payment_resolution_steps`) | 211 | ❌ não |
| `dashboard_` | 1 | 74 | ❌ não |
| `update_` | 1 | 164 | ❌ não |
| `income_` (`income_categories`) | 1 | 72 | ❌ não |
| `incomes` | 1 | 176 | ❌ não |
| agent: nenhum prefixo repetido | — | — | ❌ não |

**Conclusão:** o gate não é omisso aqui — o repositório simplesmente não tem cluster de prefixo acima do limite. Qualquer pacote criado agora seria decisão **semântica**, não estrutural, e a spec exige justamente provar isso (ou recusar).

---

## 2. Entregável 1 — Inventário de módulos e consumidores

### 2.1 `finance_api/services/` (raiz)

| Módulo | LOC | Tipo | Superfície pública | Consumidores de produção | Consumidores de teste | Patch target |
|---|---:|---|---|---|---|---|
| `accounts.py` | 71 | CRUD/negócio | `AccountService` | `routers/accounts`, `core/dependencies` | `test_accounts_service` | — |
| `categories.py` | 66 | CRUD/negócio | `CategoryService` | `routers/categories`, `mcp/tools` | `test_mcp_tools` | — |
| `credit_cards.py` | 95 | CRUD/negócio | `CreditCardService` | `routers/credit_cards`, `core/dependencies` | `test_credit_cards_service` | — |
| `income_categories.py` | 72 | CRUD/negócio | `IncomeCategoryService` | `routers/income_categories`, `core/dependencies` | `test_income_categories_service`, `test_mcp_tools` | `finance_api.routers.income_categories.*` |
| `limits.py` | 91 | CRUD/negócio | `SpendingLimitService` | `routers/limits`, `core/dependencies` | `test_limits`, `test_limits_router` | `finance_api.services.limits.CategoryRepository` |
| `payment_methods.py` | 63 | CRUD/negócio | `PaymentMethodService` | `routers/payment_methods` (via `get_payment_method_service`) | — (coberto por `tests/routers/test_payment_methods.py` via DI override) | `finance_api.routers.payment_methods.get_payment_method_service` |
| `invoices.py` | 225 | negócio | `InvoiceService` | `routers/invoices`, `routers/spents`, `core/dependencies`, `services/{balances,dashboard_strategies,spents}` | `test_invoices`, `test_balances`, `test_dashboard_strategies` | — |
| `incomes.py` | 176 | negócio | `IncomeService` | `routers/incomes`, `core/dependencies`, `services/{imports/presenter, imports/commit_strategies, imports/wiring}` | `test_incomes_service`, `test_incomes_router`, `test_mcp_tools`, `imports/test_facade`, `imports/test_commit_strategies` | `finance_api.services.incomes.PaymentResolutionService` |
| `spents.py` | 258 | negócio + orquestração | `SpentService` | `routers/spents`, `core/dependencies`, `services/imports/{presenter,commit_strategies,wiring}` | `test_spents_service`, `test_spents_router`, `test_category_validation`, `test_payment_method_validation`, `test_mcp_tools`, `imports/test_facade`, `imports/test_commit_strategies` | `finance_api.services.spents.{CategoryRepository,PaymentMethodRepository,PaymentResolutionService}` |
| `subscriptions.py` | 110 | negócio | `SubscriptionService` | `core/subscription_dependencies` | `test_subscriptions`, `test_subscription_dependencies` | — |
| `balances.py` | 178 | consulta/agregação | `BalanceService` | `routers/limits`, `core/dependencies` | `test_balances`, `test_mcp_tools` | — |
| `dashboard_strategies.py` | 74 | estratégia (consulta) | `DashboardPeriodStrategy` (Protocol), `CivilMonthDashboardStrategy`, `InvoicesDashboardStrategy` | `services/spents` | `test_dashboard_strategies` | — |
| `classification.py` | 139 | orquestração de domínio | `ClassificationService`, `resolve_default_payment_type` | `core/dependencies`, `routers/imports` (DI), `services/imports/{wiring,staging}` | `test_classification_service`, `imports/test_facade`, `test_imports_router` | — |
| `classification_chain.py` | 220 | implementações (CoR) | 9 handlers + `build_default_classification_chain` | `services/classification` | `test_classification_chain` | — |
| `extractors.py` | 101 | helpers puros (regex) + composição | 6 extratores + `build_extractor_pipeline`, `get_default_extractor_pipeline` | `services/classification` | `test_extractors` | — |
| `ai_classifier.py` | 99 | adapter HTTP externo | `AIClassifierClient`, `build_classify_payload`, `extract_suggestions` | `services/classification`, `services/imports/{enrichment,wiring,factory}` | `test_ai_classifier`, `imports/test_facade` | — |
| `payment_resolution.py` | 75 | capacidade de domínio compartilhada | `PaymentResolutionService` | `services/{spents,incomes,subscriptions}`, `core/subscription_dependencies` | `test_payment_resolution` | `finance_api.services.spents.PaymentResolutionService` (indireto) |
| `payment_resolution_steps.py` | 73 | implementações (CoR) + contrato | `PaymentResolutionContext`, `PaymentResolutionStep`, `CreditCardPaymentStep`, `AccountPaymentStep`, `resolve_account_payment_type` | `services/payment_resolution` | — (coberto por `test_payment_resolution`) | — |
| `update_preparation.py` | 164 | capacidade de domínio compartilhada | `UpdateDataPreparer`, `apply_payment_target`, 5 steps | `services/{spents,incomes,subscriptions}` | `test_update_preparation` | — |
| `protocols.py` | 169 | **contratos (bag misto)** | 13 `Protocol`/`ABC` + 2 type aliases | **15 arquivos de produção** (ver §3.2) | `test_classification_service`, `test_classification_chain`, `imports/test_bulk_strategies` | — |
| `utils.py` | 75 | helpers puros | 6 funções de agregação | `services/{incomes,balances}` | `test_utils` | — |

### 2.2 `finance_api/services/imports/` (pacote de referência — não é candidato)

| Módulo | LOC | Papel |
|---|---:|---|
| `facade.py` | 112 | ponto de entrada público (`ImportService`) |
| `wiring.py` | 69 | dataclasses de colaboradores/overrides |
| `factory.py` | 148 | composição da feature |
| `upload.py` | 156 | caso de uso |
| `staging.py` | 165 | caso de uso |
| `commit.py` | 144 | caso de uso |
| `commit_strategies.py` | 158 | estratégias (CoR) |
| `bulk.py` | 83 | caso de uso |
| `bulk_strategies.py` | 139 | estratégias |
| `enrichment.py` | 116 | enriquecimento em lote |
| `reclassify.py` | 73 | caso de uso |
| `transaction_editor.py` | 168 | caso de uso |
| `presenter.py` | 129 | montagem de resposta |
| `fingerprint.py` | 34 | helper puro (hash) |

Direção de dependência confirmada: **`imports/*` → services raiz** (`spents`, `incomes`, `classification`, `ai_classifier`, `protocols`). Nenhum módulo raiz importa `imports/` — a fronteira é unidirecional e correta.

### 2.3 `agent_api/services/` (raiz)

| Módulo | LOC | Tipo | Superfície pública | Consumidores de produção | Consumidores de teste | Patch target |
|---|---:|---|---|---|---|---|
| `agent.py` | 194 | orquestração LLM | `AgentService`, `AgentStateWithCustom` | `dependencies.py`, `services/chat` | `test_agent_service`, `test_agent_service_income`, `test_chat_service`, `test_system_prompt` | `agent_api.services.agent.create_agent` (**13×**) |
| `chat.py` | 113 | orquestração de conversa + persistência | `ChatService` | `dependencies.py`, `routers/{chat,audio,ocr}` | `test_chat_service`, `test_chat_router`, `test_ocr_router` | — |
| `system_prompt.py` | 178 | template/dados de prompt | `PromptMetadata`, `build_system_prompt`, `SYSTEM_PROMPT_TEMPLATE` | `services/agent` | `test_system_prompt` | — |
| `classify.py` | 144 | adapter LLM (classificação em lote) | `ClassifyService` | `dependencies.py`, `routers/classify` | `test_classify_service`, `test_classify_router` | — |
| `finance.py` | 262 | adapter HTTP (`finance_api`) | `FinanceService` | `dependencies.py`, `services/agent`, 6 módulos de `tools/` | 7 arquivos (`test_finance_service*`, `test_agent_service*`, `test_tools*`, `test_system_prompt`) | — |
| `graph.py` | 41 | adapter HTTP (`graph_api`) | `GraphService` | `services/agent`, 6 módulos de `tools/` | 6 arquivos (`test_graph_service`, `test_agent_service*`, `test_tools*`, `test_system_prompt`) | — |
| `base.py` | 10 | base de adapter | `BaseHttpService` | `services/{finance,graph}` | — | — |
| `audio.py` | 60 | adapter externo (faster-whisper) | `transcribe_audio`, `validate_audio_file`, `get_model` | `routers/audio` | `test_audio_service` | `agent_api.services.audio.get_model` (**2×**) |
| `ocr.py` | 108 | adapter externo (Tesseract/OpenCV) | `extract_text`, `preprocess_image`, `run_tesseract`, `validate_image_file` | `routers/ocr` | `test_ocr_service` | `agent_api.services.ocr.pytesseract.*` (**14×**) |
| `protocols.py` | 38 | contratos | `FinanceServiceProtocol` (11 métodos) | **nenhum consumidor de produção** | `test_finance_service` (asserção de tipagem) | — |
| `utils.py` | 58 | helpers puros | `attach_image`, `clean_extracted_text`, `average_confidence`, `build_tx_payload`, `normalize_confidence`, `quote_join` | `services/{agent,classify,ocr,system_prompt}` | `test_utils` | — |

### 2.4 `agent_api/services/tools/` (pacote de referência — não é candidato)

| Módulo | LOC | Tool exposta |
|---|---:|---|
| `registry.py` | 33 | `create_agent_tools` + `TOOL_BUILDERS` (ponto de entrada único) |
| `balance.py` | 43 | `consultar_saldos` |
| `spending.py` | 47 | `registrar_gasto` |
| `income.py` | 45 | `registrar_receita` |
| `summary.py` | 36 | `consultar_balanco_mensal` |
| `limit.py` | 39 | `cadastrar_limite` |
| `graph.py` | 73 | `gerar_grafico` |

Direção: `tools/*` → `{finance, graph}`; `registry` → `tools/*`; `agent` → `registry`. DAG limpo.

### 2.5 Exclusões justificadas

| Item | Motivo |
|---|---|
| `__pycache__/`, `*.pyc` | artefatos gerados |
| `finance_api/tests/**`, `agent_api/tests/**` | não são produção (usados apenas como consumidores) |
| `finance_api/services/imports/`, `agent_api/services/tools/` | já são pacotes planos validados; entram como referência, não como candidatos |
| `telegram_api`, `graph_api`, `importers/`, routers, repositories, schemas, models | fora de escopo por §3 da spec |

---

## 3. Entregável 2 — Mapa de dependências e ciclos

### 3.1 `finance_api/services/` (raiz → raiz e raiz → pacote)

```text
protocols                     (folha de contratos — sem imports de service)
payment_resolution_steps      (folha)
utils                    ───▶ protocols
update_preparation       ───▶ protocols
ai_classifier            ───▶ protocols
extractors               ───▶ protocols
classification_chain     ───▶ protocols
classification           ───▶ ai_classifier, classification_chain, extractors, protocols
invoices                      (folha)
dashboard_strategies     ───▶ invoices
payment_resolution       ───▶ payment_resolution_steps
subscriptions            ───▶ payment_resolution, update_preparation
incomes                  ───▶ payment_resolution, update_preparation, utils
balances                 ───▶ invoices, utils
spents                   ───▶ dashboard_strategies, invoices, payment_resolution, update_preparation
contas/categorias/cartões/limites/métodos de pagamento   (folhas CRUD)
```

```text
imports/*  ───▶  {spents, incomes, classification, ai_classifier, protocols}   (unidirecional)
nunca: services raiz ───▶ imports/*
```

### 3.2 Consumidores de `finance_api/services/protocols.py` (15 arquivos de produção)

`services/{ai_classifier, classification, classification_chain, extractors, update_preparation, utils}`, `services/imports/{bulk, bulk_strategies, commit, commit_strategies, factory, staging, wiring}`, e nos testes `test_classification_service`, `test_classification_chain`, `imports/test_bulk_strategies`.

### 3.3 `agent_api/services/`

```text
base, protocols, utils                      (folhas)
finance, graph        ───▶ base
classify, system_prompt, ocr  ───▶ utils
tools/{balance,spending,income,summary,limit,graph} ───▶ finance, graph
tools/registry        ───▶ tools/*, finance, graph
agent                 ───▶ finance, graph, system_prompt, tools/registry, utils
chat                  ───▶ agent
```

### 3.4 Ciclos

**Nenhum ciclo encontrado em nenhuma das duas APIs.** Verificações realizadas no código, não por nome:

- `finance_api`: as arestas de service formam DAG; as folhas (`protocols`, `payment_resolution_steps`, `invoices`, CRUDs) só recebem dependência. A fronteira `imports/` é unidirecional.
- `agent_api`: `chat → agent → tools/registry → tools/* → {finance,graph}` e `{finance,graph} → base`; `system_prompt`/`classify`/`ocr` só consomem `utils`.
- Nenhum *cycle* latente introduzido por `imports/` ou `tools/`: os pacotes só importam para fora, nunca são importados por seus consumidores.

---

## 4. Entregável 3 — Matriz de decisão por candidato

> As 5 perguntas de §4.2 da spec são respondidas em ordem em cada candidato.
> Nenhum candidato é aprovado para virar pacote: todos ficam abaixo do gatilho da Regra 8.

### C1 — `finance_api`: `classification.py`, `classification_chain.py`, `ai_classifier.py`, `extractors.py`

**Evidências:** 4 módulos / 559 LOC. Consumidores de produção: `classification` (orquestrador + DI + `imports/{wiring,staging}`), `ai_classifier` (também `imports/{enrichment,wiring,factory}`), `chain` e `extractors` (só `classification`). Testes: 6 arquivos.

1. **Mesma razão de mudança?** Parcialmente. `classification`, `chain` e `extractors` mudam com regras/formatos de extrato bancário. `ai_classifier` muda com o **contrato HTTP** de `agent_api`, e é consumido pela feature de importação independentemente da classificação unitária.
2. **Vocabulário compartilhado?** Sim para os 3 primeiros (`schemas/classification.py` é a fonte única). `ai_classifier` compartilha apenas o nome, não o vocabulário: é um cliente HTTP com fallback silencioso.
3. **Direção de dependência?** DAG: `classification → {ai_classifier, chain, extractors} → protocols`.
4. **Ponto de entrada único?** Já existe: `ClassificationService` (injetado por `core/dependencies`, consumido por `routers/imports`).
5. **Melhoraria navegação?** Não: o pacote teria 4 módulos e **nenhum** `wiring`/`factory` próprio (a composição já mora no construtor de `ClassificationService`). Trocaria `services.classification` por `services.classification.service` e criaria um segundo vocabulário de import para o mesmo conceito.

**Opções:** (a) manter plano; (b) `services/classification/{service,chain,extractors,ai_client}.py`; (c) dividir `classification_chain.py` (220 LOC, 9 handlers) em módulos menores.

**Recomendação:** **(a) manter plano.** O cluster é semanticamente coeso, mas está **abaixo do limite** e já tem entry point claro. (c) também é recusado: 220 LOC com 9 handlers de ~20 LOC é coeso, e fragmentar em `chain/` violaria *Flat is better than nested*.
**Impacto se movido (para registro):** ~6 arquivos de produção + 6 de teste; 0 patch targets diretos; quebraria a assinatura `services.classification.ClassificationService` usada em `core/dependencies`, `imports/wiring`, `imports/staging`.

### C2 — `finance_api`: `payment_methods.py`, `payment_resolution.py`, `payment_resolution_steps.py`

**Evidências:** 3 módulos / 211 LOC. `payment_methods` tem **1** consumidor (router de CRUD). `payment_resolution` tem **4** (spents, incomes, subscriptions, `core/subscription_dependencies`). `payment_resolution_steps` tem **1** (payment_resolution).

1. **Mesma razão de mudança?** Não. `payment_methods` muda com o CRUD do cadastro; `payment_resolution*` muda com as regras de resolução conta/cartão.
2. **Vocabulário compartilhado?** Apenas lexical. `payment_methods` fala `PaymentMethodCreate/Update`; `payment_resolution` fala `ResolvedPaymentTarget`. Não há import entre eles.
3. **Direção de dependência?** Ambos são folhas independentes: `payment_resolution → payment_resolution_steps`; `payment_methods` não participa.
4. **Ponto de entrada único?** Cada um já é o seu próprio ponto de entrada, com consumidores disjuntos.
5. **Melhoraria navegação?** Não: seria um pacote por prefixo (o padrão "prefixo é uma pasta escrita por extenso"), unindo duas features que nunca se importam.

**Opções:** (a) manter plano; (b) `services/payments/{methods,resolution,resolution_steps}.py`.

**Recomendação:** **(a) manter plano.** Unificar aqui criaria uma falsa fronteira: `payment_resolution` é uma **capacidade de domínio compartilhada** (consumida por 3 services + 1 provider de DI), enquanto `payment_methods` é uma **feature CRUD exposta por router**. Misturar as duas esconde essa distinção — exatamente o oposto do objetivo "localizar um service pela responsabilidade".
**Impacto se movido:** 5 arquivos de produção + 1 teste + `get_payment_method_service` em `routers/payment_methods.py` + `core/subscription_dependencies.py`.

### C3 — `finance_api`: `protocols.py` e `utils.py`

**Evidências:** 2 módulos / 244 LOC. `protocols.py`: 13 contratos + 2 type aliases, **15 consumidores de produção** e 3 de teste. Imports de topo do `protocols.py`: `httpx`, `models/{categories,income_categories,payment_methods,staged_transactions}`, `repositories/staged_transactions`, `schemas/{classification,imports,payment_resolution}`. `utils.py`: 6 funções puras, 2 consumidores de produção.

1. **Mesma razão de mudança?** Sim entre si (contratos/helpers de service), **não internamente**: `protocols.py` agrupa contratos de classificação, importação (bulk/commit/duplicidade), preparação de update, resolução de pagamento e cliente HTTP de IA.
2. **Vocabulário compartilhado?** `utils.py` é coeso (agregação por categoria/mês). `protocols.py` é um **bag**: 4 domínios distintos no mesmo arquivo.
3. **Direção de dependência?** `utils → protocols`. Efeito colateral **objetivo**: um módulo de helpers puros arrasta, via import de `protocols.py`, as camadas `httpx`, `models` e `repositories`. Qualquer teste de `utils` carrega infraestrutura de banco/HTTP só por import de módulo.
4. **Ponto de entrada único?** Não se aplica (módulos de contrato/helper). Mas a fonte única de cada contrato está certa: não há re-export, não há `__all__`, consumidores importam do lugar correto.
5. **Melhoraria navegação?** Aqui sim: separar contratos por feature reduz o "onde declaro isso?" de 1 arquivo-bag para um módulo por domínio, sem criar pacotes nem mudar camadas.

**Achado adicional (violação objetiva de Regra 2):** `BaseClassificationHandler` é um `ABC` **com implementação** (fallback final da cadeia) dentro do módulo de contratos, e suas 8 subclasses vivem em `classification_chain.py`. Contratos e implementação no mesmo arquivo é exatamente o que a Regra 2 proíbe.

**Opções:**
(a) manter como está;
(b) pacote `services/contracts/`;
(c) **separação local sem pacote**: quebrar `protocols.py` em módulos de contrato por domínio, mantendo tudo plano, e deixar no `protocols.py` apenas os contratos genuinamente transversais.

**Recomendação:** **(c)**, em fase posterior e isolada. Priorização por risco/benefício:

| Prio | Movimentação | Módulos afetados | Risco |
|---|---|---|---|
| P1 | `BulkActionStrategy`, `TransactionCommitStrategy`, `DuplicateDetectorStrategy` → `services/imports/protocols.py` (pacote já existe; **todos** os consumidores de produção estão dentro de `imports/`) | 7 prod + 1 teste | baixo |
| P1 | `ClassificationHandlerProtocol`, `MerchantExtractorStep`, `MerchantExtractorPipeline` + mover `BaseClassificationHandler` para junto das subclasses → `services/classification_protocols.py` | 4 prod + 2 testes | baixo |
| P2 | `AIClassifierHttpClientProtocol` → `services/ai_classifier_protocols.py` | 1 prod | baixo, remove `httpx` do bag |
| P2 | `PaymentResolutionServiceProtocol`, `PaymentTargetPayload`, `UpdatePreparationStep`, `*LookupProtocol` → revisar destino junto com `update_preparation.py`/`utils.py` | 4 prod + 1 teste | médio (ainda compartilhados por 2 features) |
| P3 | `CategorizedAmountProtocol` permanece no `protocols.py` residual | 1 prod | — |

**Critério de sucesso do (c):** `protocols.py` residual deixa de importar `httpx`, `models.*` e `repositories.*`; `utils.py` passa a depender apenas de contratos leves.
**Impacto se movido:** 15 imports de produção + 3 de teste (finance apenas; `agent_api` não é afetado).
**Recusado:** (b) `services/contracts/` — seria um pacote cujo único conteúdo é "contratos de todo mundo", repetindo o problema do bag com mais um nível de aninhamento.

### C4 — `agent_api`: `agent.py`, `chat.py`, `system_prompt.py`

**Evidências:** 3 módulos / 485 LOC. `agent` tem 13 patch targets (`create_agent`), 4 arquivos de teste e 2 consumidores de produção. `chat` tem 3 routers + DI + 3 testes. `system_prompt` tem 1 consumidor e 1 teste.

1. **Mesma razão de mudança?** Não: `chat` muda com sessão/persistência; `agent` com framework de LLM/tools; `system_prompt` com o texto das regras de negócio.
2. **Vocabulário compartilhado?** Sim no nível `AssistantResponse`, não no nível de responsabilidade.
3. **Direção de dependência?** `chat → agent → system_prompt → utils`. Clara e acíclica.
4. **Ponto de entrada único?** Sim: `ChatService` (router) e `AgentService` (DI). Cada um já é o seu entry point.
5. **Melhoraria navegação?** Não: 3 módulos/485 LOC, abaixo do limite, com nomes que já dizem exatamente o que fazem; `services.agent` é o nome mais previsível possível.

**Opções:** (a) manter plano; (b) `services/conversation/{agent,chat,prompt}.py`.

**Recomendação:** **(a) manter plano.** Além do critério de tamanho, o custo de movimentação é o mais alto do diagnóstico: **13 patch targets** em `agent_api.services.agent.create_agent` e 3 routers que importam `ChatService` diretamente. Zero ganho de coesão.
**Impacto se movido:** 2 prod (`dependencies.py`, `chat.py`) + 3 routers + 6 arquivos de teste (incluindo reescrita dos 13 patch targets).

### C5 — `agent_api`: `audio.py`, `ocr.py`

**Evidências:** 2 módulos / 168 LOC, consumidos **exclusivamente** por `routers/{audio,ocr}` como funções de módulo (não classes). 16 patch targets nos módulos de service (14 em `ocr`, 2 em `audio`) + 1 patch de router (`routers.ocr.extract_text`).

1. **Mesma razão de mudança?** Não: engines diferentes (faster-whisper vs Tesseract/OpenCV), exceções diferentes (`InvalidAudioError`/`AudioProcessingError` vs `InvalidImageError`/`OCRProcessingError`) e decorators diferentes.
2. **Vocabulário compartilhado?** Mínimo: apenas "arquivo de entrada + validação + extração". `ocr` usa 2 helpers de `services/utils.py`; `audio` usa nenhum.
3. **Direção de dependência?** Independentes, ambos folhas (só `core/*` e, no caso do OCR, `services/utils`).
4. **Ponto de entrada único?** Cada router é o entry point do seu adapter.
5. **Melhoraria navegação?** Não: um pacote `media/` sugeriria um domínio compartilhado inexistente e encareceria 16 patch targets.

**Recomendação:** **(a) manter plano.** São **adapters independentes**, não um domínio de mídia. Se um dia houver orquestração comum (ex.: pipeline áudio→texto→OCR), aí sim o agrupamento terá razão de negócio — hoje não tem.
**Impacto se movido:** 2 routers + 2 arquivos de teste + 16 patch targets.

### C6 — `agent_api`: `finance.py`, `graph.py`, `tools/`

**Evidências:** `finance` 262 LOC (7 arquivos de teste), `graph` 41 LOC (6 arquivos de teste), `tools/` 7 módulos + 317 LOC com `registry.py` como factory única.

1. **Mesma razão de mudança?** `finance`/`graph` mudam com contratos das APIs downstream; cada tool muda com o contrato exposto ao LLM (docstring = prompt).
2. **Vocabulário compartilhado?** Sim, entre tools e clients (as tools são a única superfície que consome ambos).
3. **Direção de dependência?** Correta e já validada: `tools → clients`, `registry → tools`, `agent → registry`. Sem ciclo.
4. **Ponto de entrada único?** Sim, e bem feito: `tools/registry.create_agent_tools` é o único lugar que enumera tools.
5. **Melhoraria navegação?** Não: `tools/` já é o padrão-alvo da Regra 8 (flat, sem repetir prefixo, `__init__` sem `__all__`, composição dentro da feature).

**Recomendação:** **manter como está.** Único ajuste opcional, fora do escopo desta fase: `tools/graph.py` e `services/graph.py` compartilham o nome com responsabilidades diferentes (tool `gerar_grafico` vs cliente HTTP de `graph_api`); um rename puro `tools/graph.py → tools/chart.py` reduziria a ambiguidade. Custo: 1 import em `registry.py` + 2 arquivos de teste. **Requer aprovação explícita e não é recomendado como prioridade.**
**Opção recusada:** `services/clients/{finance,graph,base}.py` (3 módulos/313 LOC) — abaixo do limite da Regra 8, custo de 8 arquivos de teste (com sobreposição) e ganho apenas cosmético.

---

## 5. Achados transversais (não são candidatos, mas afetam a decisão)

| # | Achado | Evidência | Efeito | Recomendação |
|---|---|---|---|---|
| A1 | `protocols.py` é um bag de contratos de 4 features | 13 contratos, 15 consumidores, imports de `httpx`/models/repositories | Acoplamento de import e descoberta ruim | Split do C3 (P1) |
| A2 | Contrato + implementação no mesmo arquivo | `BaseClassificationHandler` (ABC com fallback) em `protocols.py`; subclasses em `classification_chain.py` | Viola Regra 2; o fallback é comportamento escondido num módulo de contrato | Mover a ABC para `classification_chain.py` (P1) |
| A3 | Helper puro arrasta infraestrutura | `services/utils.py → protocols.py → httpx, models, repositories` | Testes de helpers carregam camadas de banco/HTTP | Resolvido por A1 |
| A4 | `agent_api/services/protocols.py` sem consumidor de produção | Apenas `tests/services/test_finance_service.py` usa `FinanceServiceProtocol` | Não é dívida (espelha os 11 métodos reais, sem drift), mas é contrato mantido só para teste | Manter; reavaliar se o contrato começar a divergir |
| A5 | Serviços de resolução instanciados a partir de `repo.db` | `spents.py:81` e `incomes.py:70` fazem `PaymentResolutionService(db=getattr(self.repo, "db", None))` | Acoplamento oculto de DI (fora do escopo desta spec) | Registrar para uma spec de DI; **não** tratar aqui |
| A6 | `payment_resolution_steps.py` mistura dataclass + Protocol + 2 implementações | 73 LOC, coeso | Regra 1/2 em sentido estrito, mas o arquivo é pequeno e tem um único consumidor | Manter; sem pacote, separar só quando houver 2º consumidor |

---

## 6. Entregável 4 — Estruturas-alvo

**Nenhum pacote novo é aprovado por este diagnóstico.** Estruturas-alvo de pacote (§7 da Regra 8) ficam indefinidas por ausência de candidato elegível.

Única estrutura-alvo **condicional**, válida somente se o C3 for aprovado numa fase posterior (mantém tudo plano — **não** cria pacote):

```text
finance_api/services/
├── protocols.py                    # residual: apenas contratos transversais
├── classification_protocols.py     # ClassificationHandlerProtocol, MerchantExtractor*
├── ai_classifier_protocols.py      # AIClassifierHttpClientProtocol
├── classification.py               # orquestrador (inalterado em conteúdo)
├── classification_chain.py         # + BaseClassificationHandler (ABC + fallback)
├── extractors.py
├── ai_classifier.py
├── utils.py
└── imports/
    ├── protocols.py                # BulkActionStrategy, TransactionCommitStrategy,
    │                               # DuplicateDetectorStrategy
    └── ...
```

Regras que valem para essa fase, se aprovada: `git mv` puro, sem alias de compatibilidade, sem `__all__`, sem re-export, atualização simultânea de produção + DI + testes + patch targets.

---

## 7. Entregável 5 — Riscos e sequência sugerida

### 7.1 Riscos (de uma eventual fase de movimentação)

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Patch targets quebrados silenciosamente | Média | Alto | `grep 'services\.' nos tests` antes/depois; rodar suíte completa (703 testes) |
| Import circular acidental ao mover contratos | Baixa | Alto | mover contratos **para baixo** na DAG (leaf-ward); validar com `python -c "import finance_api.main"` |
| `services.classification`/`services.agent` referenciados em DI e routers | Média | Médio | `core/dependencies.py`, `core/subscription_dependencies.py`, `agent_api/dependencies.py` no mesmo commit |
| Perda de rastreabilidade do diff | Média | Médio | `git mv` + `git diff -M` por unidade de domínio |
| Divergência de espelhamento dos testes | Média | Baixo | mover o teste junto (`tests/services/...`), nunca deixar arquivo órfão |
| Regressão do gate de arquitetura | Baixa | Médio | rodar `tests/architecture/` a cada movimentação (inclui Regra D — nome repetindo o pacote) |

### 7.2 Sequência sugerida (somente se aprovada)

| Ordem | Unidade | Escopo | Pré-condição |
|---|---|---|---|
| 0 | — | Nada (esta fase termina aqui) | aprovação humana desta spec |
| 1 | C3-P1a | Contratos de importação → `services/imports/protocols.py` | aprovação + suíte verde |
| 2 | C3-P1b | Contratos de classificação + `BaseClassificationHandler` → `classification_protocols.py` / `classification_chain.py` | item 1 verde |
| 3 | C3-P2 | Contratos de IA/pagamento/update; `protocols.py` residual sem `httpx`/models/repositories | item 2 verde |
| 4 | (opcional) | `tools/graph.py → tools/chart.py` | decisão explícita |
| 5 | — | Regra F no gate (ver §8.3) | item 3 concluído |

Cada item: 1 commit isolado, `make format` + `make lint` + `uv run pytest` + `tests/architecture/`, diff revisado por humano, **sem commit/push sem autorização** (`AGENTS.md` §7).

---

## 8. Entregável 6 — Recomendação sobre o critério atual (Regra 8)

### 8.1 O critério responde ao problema?

**Sim para o problema estrutural e não para o problema semântico.** A Regra 8 acertou o único caso real do repositório (`imports/`: 14 módulos / 1.695 LOC, coesos, com `factory`/`wiring` próprios). Os 6 candidatos desta revisão ficam bem abaixo do gatilho — forçar pacotes aqui produziria pastas de 2–4 arquivos com ganho zero de coesão.

### 8.2 Recomendação principal

1. **Manter a Regra 8 intacta** (limiares, gate e baseline). Nada a alterar.
2. **Complementar com um checklist de admissão semântica** (as 5 perguntas de §4.2), documentado em `.specs/services-modules-quality-refactoring/08-estrutura-padrao-apis.md` como **orientação de revisão**, não como gate. Motivo: o critério de tamanho não distingue "cluster coeso" de "mesmo prefixo"; hoje essa distinção só existe na cabeça de quem revisa.
3. **Não usar** "quantidade de arquivos no diretório" nem "simetria entre finance_api e agent_api" como justificativa — nenhum candidato sobrevive a esse teste.

### 8.3 Proposta de gate novo (separada, exige aprovação explícita)

Se o C3 for aprovado, propor a **Regra F** no `tests/architecture/test_module_organization.py`:

> Nenhum módulo de contrato ou helper puro em `services/` pode importar `models.*`, `repositories.*` ou `httpx`.

- Mensurável via AST/import scan.
- **Não deve ser introduzida antes do split**: hoje `protocols.py` viola a regra por definição e o baseline congelaria a dívida (mesmo padrão usado nas fases 6.1–6.6, mas aqui evitável).
- Alteração da Regra 8, do baseline ou do gate **não** está recomendada nesta fase e permanece fora de escopo até aprovação.

---

## 9. Critérios de aceite (§6 da spec)

| Critério | Status | Evidência |
|---|---|---|
| Todos os módulos de produção aparecem no inventário ou têm exclusão justificada | ✅ | §2.1 (21), §2.3 (11), §2.2/§2.4 (pacotes de referência), §2.5 (exclusões) |
| Cada candidato do §1 tem decisão fundamentada, inclusive manter plano | ✅ | §4 — C1–C6, todos com "manter plano" justificado |
| Dependências e consumidores verificados no código; ciclos registrados | ✅ | §3 — adjacência real + §3.4 (zero ciclos) |
| Impacto de imports/DI/testes/monkeypatches descrito por movimentação | ✅ | §4 (bloco "Impacto se movido" em cada candidato) e §7.1 |
| Recomendações preservam `route → service → repository` e contratos públicos | ✅ | Nenhuma movimentação de camada; §6 mantém tudo em `services/` |
| Nenhuma mudança de código/comportamento nesta fase | ✅ | Apenas este documento foi criado; gate e suíte não foram alterados |
| Proposta de alterar regra/gate separada das recomendações estruturais | ✅ | §8.3 é explicitamente condicional e sujeita a aprovação |
| Resultado apresentado para revisão humana antes da fase de implementação | ⏳ | Este documento — fase 3 bloqueada |

**Verificação executada nesta fase:** `uv run pytest tests/architecture/test_module_organization.py -q` → `7 passed` (0 violações), antes de qualquer decisão de movimentação.

---

## 10. Próximo passo (decisão humana)

| Opção | Significado |
|---|---|
| **A (recomendada)** | Aceitar o diagnóstico: nenhum pacote novo; abrir uma spec de implementação **apenas** para o C3 (split de `protocols.py`) + Regra F |
| B | Aceitar o diagnóstico e encerrar: manter tudo plano, sem fase de implementação (só a documentação do checklist em §8.2) |
| C | Rejeitar uma ou mais decisões (ex.: criar `classification/` mesmo abaixo do limiar) — exige justificativa registrada, pois contraria a Regra 8 |

Nenhuma movimentação, rename ou alteração de gate será executada antes de uma decisão explícita em A/B/C.

### 10.1 Decisão registrada

**Opção A aprovada pelo desenvolvedor em 2026-11-02.** Consequências:

- Nenhum pacote novo será criado; C1, C2, C4, C5 e C6 ficam formalmente encerrados como "manter plano".
- Foi criada a spec de implementação do C3 + Regra F: [02-fase-implementacao-c3-protocols-split.md](./02-fase-implementacao-c3-protocols-split.md).
- A implementação **ainda não começou**: depende da aprovação da spec 02 (T1–T7).

### 10.2 Implementação executada (2026-11-02)

T1–T7 da [spec 02](./02-fase-implementacao-c3-protocols-split.md) foram executadas: `protocols.py` reduzido de 169 → 14 LOC, cinco módulos de contrato criados, `BaseClassificationHandler` movido para `classification_chain.py` e Regra F ativa no gate (`tests/architecture` → 9 testes). Suíte completa: **705 passed**. Nenhum commit/push realizado.
