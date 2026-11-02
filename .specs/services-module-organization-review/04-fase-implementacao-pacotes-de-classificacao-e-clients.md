# Implementação — Pacotes de Classificação e Clients

> **Origem:** [03-reavaliacao-navegabilidade-e-dominios.md](./03-reavaliacao-navegabilidade-e-dominios.md), opção A.
> **Aprovação:** “Gostei! Segue implementação!” — aprovação explícita do desenvolvedor para F1 + A1.
> **Status:** implementada; aguardando revisão do desenvolvedor. Alteração exclusivamente estrutural, sem mudança de comportamento.
> **Escopo:** `finance_api/services/classification/` e `agent_api/services/clients/`.
> **Fora de escopo:** `agent_api/services/conversation/` (A2), qualquer outro agrupamento, commit e push.

---

## 1. Árvore-alvo

```text
finance_api/services/
├── classification/
│   ├── __init__.py                 # vazio
│   ├── ai_classifier.py
│   ├── ai_client_protocols.py      # antigo ai_classifier_protocols.py
│   ├── chain.py                    # antigo classification_chain.py
│   ├── extractors.py
│   ├── protocols.py                # antigo classification_protocols.py
│   └── service.py                  # antigo classification.py
└── ...                             # demais services inalterados

agent_api/services/
├── clients/
│   ├── __init__.py                 # vazio
│   ├── base.py
│   ├── finance.py
│   └── graph.py
└── ...                             # demais services, incluindo tools/, inalterados
```

Os imports consumidores migram para a nova fonte. Não haverá módulos antigos de compatibilidade, `__all__` ou reexports.

## 2. Tarefas

| Tarefa | Alterações | Verificação de saída |
|---|---|---|
| T1 — Política | Registrar em `08-estrutura-padrao-apis.md` a exceção semântica aprovada para `classification/` e `clients/`. | Documentação coerente com F1/A1 e sem mudar o gate A–F. |
| T2 — Pacote de classificação | Mover os seis módulos atuais para `services/classification/`; renomear `classification.py` → `service.py`, `classification_chain.py` → `chain.py`, `classification_protocols.py` → `protocols.py` e `ai_classifier_protocols.py` → `ai_client_protocols.py`. Criar `__init__.py` vazio. | Import dos módulos e apps sem ciclo. |
| T3 — Consumidores financeiros | Atualizar imports em `core/dependencies.py`, `services/imports/{enrichment,factory,staging,wiring}.py` e quaisquer consumidores identificados pela busca final. | Nenhuma referência de produção aponta aos caminhos antigos. |
| T4 — Testes financeiros | Mover os testes específicos para `finance_api/tests/services/classification/`, atualizar imports e conservar os casos/assertivas existentes. | Testes de classification, chain, extractor e AI client verdes. |
| T5 — Pacote de clients | Mover `base.py`, `finance.py`, `graph.py` para `agent_api/services/clients/`; criar `__init__.py` vazio. | `FinanceService` e `GraphService` continuam herdando do `BaseHttpService` do novo caminho. |
| T6 — Consumidores e testes do agent | Atualizar imports em dependencies, agent, tools e testes; mover testes unitários dos clients para `agent_api/tests/services/clients/`. | Nenhuma referência de produção aponta aos caminhos antigos; tests de clients/tools/agent verdes. |
| T7 — Fechamento | Rodar import dos dois apps, gate de arquitetura, testes, formatador e linter; revisar `git diff -M`. | Critérios da seção 3 satisfeitos. |

## 3. Critérios de aceite

- Os dois pacotes existem com `__init__.py` vazio e nomes de módulos que não repetem o nome do pacote.
- `conversation/` não é criado; `agent.py`, `chat.py` e `system_prompt.py` permanecem planos.
- Todos os consumidores de produção e testes importam dos novos caminhos; não há alias/reexport antigo.
- Patch targets preservam a semântica e apontam para o módulo onde o símbolo é usado.
- Não há ciclos introduzidos; `import finance_api.main` e `import agent_api.main` funcionam.
- `tests/architecture`, os testes relevantes das duas APIs e a suíte definida pelo projeto passam.
- `make format` e `make lint` passam.
- Nenhum commit ou push é realizado sem solicitação expressa.

## 4. Consumidores conhecidos a atualizar

### `finance_api`

- Produção: `core/dependencies.py`; `services/imports/enrichment.py`, `factory.py`, `staging.py` e `wiring.py`.
- Testes: `test_classification_service.py`, `test_classification_chain.py`, `test_extractors.py`, `test_ai_classifier.py`, `services/imports/test_facade.py` e `tests/routers/test_imports_router.py`.
- As referências nas specs antigas são histórico de implementação; não são imports executáveis. Só serão atualizadas se deixarem de representar claramente o estado histórico.

### `agent_api`

- Produção: `dependencies.py`, `services/agent.py` e os módulos `services/tools/*.py` que usam `FinanceService`/`GraphService`.
- Testes: testes de FinanceService, GraphService, AgentService, system prompt e tools. Os testes unitários dedicados a Finance/Graph serão movidos para `tests/services/clients/`.
- Alvos como `agent_api.services.agent.create_agent` não mudam, pois `agent.py` permanece no lugar.

## 5. Comandos de verificação

```bash
uv run python -c "import finance_api.main"
uv run python -c "import agent_api.main"
uv run pytest tests/architecture -q
uv run pytest finance_api/tests/services/classification finance_api/tests/services/imports/test_facade.py finance_api/tests/routers/test_imports_router.py -q
uv run pytest agent_api/tests/services/clients agent_api/tests/services/test_agent_service.py agent_api/tests/services/test_system_prompt.py agent_api/tests/services/test_tools.py -q
make format
make lint
uv run pytest -q
```

Não iniciar servidores nem executar operações em banco real: esta mudança só altera organização e caminhos de import.

## 6. Evidências de execução

- T1–T6 executadas: pacotes criados, módulos e testes movidos, imports migrados e exceção semântica registrada em `08-estrutura-padrao-apis.md`.
- Busca por imports executáveis nos caminhos antigos: nenhum resultado em `finance_api/` ou `agent_api/`.
- Imports dos apps: `import finance_api.main` e `import agent_api.main` concluídos.
- Testes focados: finance **51 passed**, agent **53 passed**, arquitetura **9 passed**.
- Suíte completa com cobertura: **705 passed**, cobertura global **95%**; os módulos de comportamento movidos ficaram cobertos pelos testes existentes.
- `make format`: concluído; Black deixou 365 arquivos inalterados e Ruff corrigiu 2 ordenações de import.
- `make lint`: concluído; Black e Ruff sem erros.
- `uv run ruff format --check .`: passou; `uv run mypy .`: sem issues em 365 arquivos.
- Frontend inalterado: `npm run lint` e `npx tsc --noEmit` passaram.
- Runtime local: `GET /health` retornou **200** em `finance_api` e `agent_api`; processos encerrados ao final.
- Não foram executados endpoints de mutação, chamadas a LLMs, operações em banco de dados ou testes de Frontend; a refatoração só alterou caminhos de import e nenhum código de Frontend foi modificado.
- Nenhum commit ou push foi realizado.
