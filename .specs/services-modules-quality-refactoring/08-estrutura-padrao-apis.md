# Estrutura Padrão das 4 APIs

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Fase:** 6.3 (normativo) · **Gate:** [`tests/architecture/test_module_organization.py`](../../tests/architecture/test_module_organization.py)
> **Regras da skill:** `python-modular-code-organization` (Regras 1–8), `python-pep8-guidelines`, `python-zen-of-python`

Este documento é a referência para decidir **onde** cada arquivo novo mora. Ele descreve o shape canônico medido em 2026-11-02, as exceções intencionais e a regra de decisão em 5 linhas.

---

## 1. Shape canônico

### 1.1 Comum às 4 APIs

```text
<api>/
├── main.py            # app FastAPI/PTB, exception handlers, routers
├── settings.py        # pydantic-settings (uma instância `settings`)
├── core/              # cross-cutting: config, logging, métricas, decorators, exceções, clientes HTTP
├── routers/           # só HTTP: validação de payload + delegação ao service
├── schemas/           # Pydantic/dataclasses/enums/TypedDicts (Regra 1)
├── services/          # regra de negócio; orquestra repositories
└── tests/             # espelha a estrutura (tests/services/, tests/routers/, ...)
```

### 1.2 Camadas adicionais por API

| Diretório | finance_api | agent_api | telegram_api | graph_api |
|---|:---:|:---:|:---:|:---:|
| `repositories/` | ✅ | ✅ | ✅ | — |
| `models/` (ORM) | ✅ | ✅ | ✅ | — |
| `handlers/` (adapter Telegram) | — | — | ✅ | — |
| `importers/` (bounded context) | ✅ | — | — | — |
| `mcp/` (bounded context) | ✅ | — | — | — |
| `dependencies.py` (DI do agente) | — | ✅ | — | — |

- **`handlers/` no `telegram_api`** é a camada de adapter do Telegram (traduz `Update`/`Context` para chamadas de service). Não é violação de camadas: é o equivalente ao `routers/` das APIs HTTP.
- **`importers/` no `finance_api`** é um bounded context de parsing de extratos (parsers + registry + schemas), consumido por `services/imports/`.
- **`graph_api` não tem `models/` nem `repositories/`**: é um renderer stateless (recebe balances → devolve imagem). Ausência é intencional, não dívida.

### 1.3 Feature package (Regra 8)

Quando um grupo de módulos no mesmo diretório compartilha prefixo/domínio e atinge **≥ 5 arquivos** ou **≥ 800 LOC**, ele vira um **pacote plano**. Esse é o gatilho automático do gate; um pacote menor só pode ser criado quando uma exceção semântica estiver registrada na seção 3 e aprovada explicitamente:

```text
finance_api/services/imports/     # não "import" (keyword) e não "import_*" espalhado
├── __init__.py                    # vazio: sem __all__, sem re-export (Regra 5)
├── facade.py                      # ponto de entrada público
├── wiring.py / factory.py         # composição fica com a feature
├── upload.py / staging.py / commit.py / bulk.py
```

Regras do pacote: flat por dentro (sem `strategies/`, `impl/`), nomes sem repetir o pacote (`imports/upload.py`, **não** `imports/import_upload.py`), nenhum alias de compatibilidade.

---

### 1.4 Contratos no layout flat (Regra F)

Quando o domínio não tem pacote próprio, o equivalente flat a `<domínio>/protocols.py` é
`<domínio>_protocols.py` no mesmo diretório:

| Situação | Onde declarar | Exemplo |
|---|---|---|
| Contrato usado por uma feature/pacote existente | dentro do pacote | `services/imports/protocols.py` |
| Contrato de um domínio flat específico | `<domínio>_protocols.py` | `services/classification_protocols.py` |
| Contrato compartilhado por 2+ features | módulo nomeado pela capacidade | `services/lookup_protocols.py` |
| Contrato genuinamente transversal | `services/protocols.py` | `CategorizedAmountProtocol` |

**Regra F** (gate [`tests/architecture/test_module_organization.py`](../../tests/architecture/test_module_organization.py)):
`services/protocols.py` e `services/utils.py` não podem importar `httpx`, `*.models.*` nem
`*.repositories.*`. Contratos e helpers transversais precisam continuar leves: se o contrato depende do
modelo de um domínio, ele pertence ao domínio (ou ao pacote da feature), não ao módulo transversal.

`ABC` com comportamento implementado (ex.: fallback de cadeia) **não é contrato**: vive junto das
subclasses (`classification_chain.py`) e importa apenas o `Protocol` do módulo de contratos.

---

## 2. Regra de decisão (5 linhas)

1. **Contrato de dados** (`BaseModel`, `Enum`, `@dataclass`, `TypedDict`) → `schemas/` (ou `<feature>_schemas.py` no domínio).
2. **Protocolo/ABC** → `protocols.py` do domínio, separado das implementações.
3. **Função pura reutilizável** (texto, data, formatação) → `core/utils.py` ou `<domínio>/utils.py`; nome público, sem `_`.
4. **Acesso a banco** → `repositories/`; **regra de negócio/orquestração** → `services/`; **HTTP** → `routers/`; **Telegram** → `handlers/`.
5. **Feature com ≥ 5 arquivos/≥ 800 LOC do mesmo prefixo** → pacote plano com o nome do domínio (nunca keyword).

---

## 3. Exceções permitidas (registradas, não implícitas)

| Exceção | Onde | Justificativa |
|---|---|---|
| `handlers/` como camada | `telegram_api` | Adapter do Telegram; equivalente ao `routers/` HTTP. |
| `importers/` e `mcp/` | `finance_api` | Bounded contexts legítimos (parsing de extratos e tools MCP). |
| Ausência de `models/`/`repositories/` | `graph_api` | Renderer stateless — não persiste nada. |
| `dependencies.py` na raiz | `agent_api` | Composition root do agente (LLM + clients + services); não é "utils". |
| Pacotes semânticos abaixo do limiar estrutural | `finance_api/services/classification/`, `agent_api/services/clients/` | F1/A1 da reavaliação `.specs/services-module-organization-review/03-reavaliacao-navegabilidade-e-dominios.md`: coesão de feature e fronteira de integração explícitas; aprovados pelo desenvolvedor em 2026-11-02. Esta exceção não autoriza criar pacotes pequenos por prefixo ou simetria. |
| Funções > 40 LOC | `imports/staging.py::_to_staged`, `importers/c6_credit_card_csv.py::_parse_row`, `services/tools/graph.py::build_gerar_grafico` | Mapping campo-a-campo / parser de CSV / docstring-contrato do LLM — ver master plan §2.2-B. |
| `except Exception` de fronteira | `telegram_api/repositories/session_repository.py` (4) | Cache de sessão best-effort: log + rollback + degradação; comportamento fixado em teste. Requer decisão de produto para propagar. |

Qualquer nova exceção precisa entrar **nesta tabela** e, quando aplicável, na allowlist do gate com a fase que a quita.

---

## 4. Nomenclatura (Regra 4 e Regra 8.2)

- Módulo **não repete o nome do pacote**: `handlers/expense.py` (não `expense_handler.py`), `services/session.py` (não `session_service.py`), `imports/upload.py` (não `import_upload.py`).
- Função **standalone nunca começa com `_`**; `_` é reservado a métodos privados de classe.
- `__all__` é proibido em módulos internos; `__init__.py` interno vazio (sem re-export).
- Imports só no topo, em 3 blocos PEP 8 (stdlib → third-party → local), sempre absolutos.

---

## 5. Onde este padrão é verificado

`tests/architecture/test_module_organization.py` roda no `uv run pytest` e falha em violação **nova** das regras A–F:

| Regra | Verifica |
|---|---|
| **A** | cluster de prefixo ≥ 5 arquivos ou ≥ 800 LOC fora de pacote plano |
| **B** | arquivo de produção > 300 LOC |
| **C** | pacote com nome de keyword Python |
| **D** | módulo repetindo o nome do pacote (inclui sufixos `_handler`/`_service`) |
| **E** | `__all__` em `__init__.py` interno |
| **F** | contrato/helper transversal importa `httpx`, `models` ou `repositories` |

A allowlist de dívida é temporária e é apagada na 6.6; a partir daí o gate é estrito.
