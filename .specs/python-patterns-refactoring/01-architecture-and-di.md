# Fase 1: Arquitetura em Camadas, Repository Protocols (PEP 695) & FastAPI DI

**Skills aplicadas:** `python-fastapi-architecture` e `python-pattern-repository-service`  
**Serviços-alvo:** `finance_api`, `agent_api`, `telegram_api`, `graph_api`

---

## 1. Diagnóstico Detalhado (Estado Atual)

### 1.1. Violação de Camadas e Acoplamento ao ORM
1. **Router acessando Repository direto e levantando `HTTPException`**:
   - Em `finance_api/routers/imports.py` (linhas 134-151), `list_import_rules` e `delete_import_rule` injetam `CategoryRuleRepository` diretamente no router, fazem `[ImportRuleResponse.model_validate(r) for r in rules]` e dão `raise HTTPException(status_code=404, ...)`.
   - Na linha 36 de `finance_api/routers/imports.py`, `upload_statement` faz `raise HTTPException(status_code=400, detail="Arquivo vazio.")` em vez de levantar `ValidationError` do domínio.
2. **Service manipulando `AsyncSession` diretamente**:
   - Em `finance_api/services/imports.py` (linhas 345-347):
     ```python
     self.batch_repo.db.add(batch)
     await self.batch_repo.db.commit()
     await self.batch_repo.db.refresh(batch)
     ```
   - E nas linhas 388 e 398, `ImportService` atravessa outro serviço para acessar o repositório privado dele: `await self.spent_service.repo.get_by_id(...)`.
3. **Instanciação interna de Repository em `agent_api` e `telegram_api`**:
   - Em `agent_api/services/chat.py` (linhas 17-23):
     ```python
     class ChatService:
         def __init__(self, db_session: AsyncSession, agent_service: AgentService):
             self.repository = ChatRepository(db_session)  # ❌ Acoplamento direto!
     ```
   - Em `telegram_api/services/session_service.py`, `SessionService` usa `@staticmethod` e instancia `SessionRepository(session)` dentro de blocos `async with get_db() as session:`.
   - Em `telegram_api/main.py` (linha 174), há SQL puro (`text("SELECT DISTINCT chat_id FROM chat_sessions")`) fora do `SessionRepository`.

### 1.2. Ausência de `Annotated` + `Depends` e de Contratos `Protocol`
- Em `finance_api/core/dependencies.py`, `get_import_service` instancia manualmente 12 classes usando `db: AsyncSession = Depends(get_db)`.
- Os repositórios não possuem uma classe base genérica (`SQLAlchemyRepository[T, ID]`) nem contratos `Protocol` (`RepositoryProtocol[T, ID]`), obrigando os testes unitários de serviço a usar mocks pesados (`mocker.AsyncMock`) em vez de *In-Memory Fake Repositories*.

---

## 2. Solução Implementada (Python 3.13+ Idiomático)

### Passo 1: Base Genérica de Repositório com PEP 695 (`finance_api/repositories/base.py`)

Criamos o contrato estrutural `RepositoryProtocol[T, ID]` e a implementação base `SQLAlchemyRepository[T, ID]` usando a sintaxe nativa de genéricos do Python 3.13.

### Passo 2: Protocolos de Repositório por Domínio
Definimos os contratos `AccountRepositoryProtocol`, `ImportBatchRepositoryProtocol`, `CategoryRuleRepositoryProtocol`, `ChatRepositoryProtocol` e `SessionRepositoryProtocol` para que a camada de `Service` dependa **apenas da abstração** (Dependency Inversion Principle).

### Passo 3: Injeção de Dependências com `Annotated` (`finance_api/core/dependencies.py` e `agent_api/dependencies.py`)

Substituímos a instanciação manual em cascata por *Type Aliases* compostos com `Annotated` (`DBSessionDep`, `AccountRepoDep`, `ImportServiceDep`, `ClassificationServiceDep`, `ChatRepoDep`, etc.).

### Passo 4: Limpeza dos Routers (`finance_api/routers/imports.py`)
1. **Zero `Repository` nos Routers**: `ClassificationService` agora expõe `list_rules()` e `delete_rule()`, levantando `EntityNotFoundError` quando a regra não existir.
2. **Zero `HTTPException` nos Routers**: Quando `content` do upload estiver vazio em `upload_statement`, levanta `ValidationError("Arquivo vazio.")`.
3. **Zero `.model_validate()` manual nos Routers**: Retorna as entidades ORM diretamente do endpoint e deixa o `response_model=list[ImportRuleResponse]` do FastAPI serializar automaticamente.

### Passo 5: Desacoplamento de `ChatService` (`agent_api`) e `SessionService` (`telegram_api`)
1. Em `agent_api/services/chat.py`, `ChatService` recebe `ChatRepositoryProtocol` injetado via `agent_api/dependencies.py`.
2. Em `telegram_api/repositories/session_repository.py`, adicionamos `list_distinct_chat_ids()` (corrigindo inclusive o nome da tabela para `TelegramSession.chat_id`), removendo o SQL cru de `telegram_api/main.py`.

---

## 3. Checklist de Execução e Testes (Fase 1)

- [x] Criar `finance_api/repositories/base.py` com `RepositoryProtocol[T, ID]` e `SQLAlchemyRepository[T, ID]`.
- [x] Adicionar método `update_batch_stats(batch, possible_duplicates, ai_used)` em `ImportBatchRepository` e remover acesso direto a `self.batch_repo.db` de `ImportService`.
- [x] Refatorar `finance_api/core/dependencies.py` e `agent_api/dependencies.py` para usar `Annotated[..., Depends(...)]`.
- [x] Extrair lógica de `rules_router` em `finance_api/routers/imports.py` para a camada de `Service`, removendo `CategoryRuleRepository` e `HTTPException` do router.
- [x] Refatorar `ChatService` em `agent_api/services/chat.py` para receber `ChatRepositoryProtocol` via construtor (`__init__`).
- [x] Mover SQL de `telegram_api/main.py` para `SessionRepository.list_distinct_chat_ids()`.
- [x] Criar pasta `finance_api/tests/fakes/` com `InMemoryAccountRepository` para testes unitários rápidos de serviço sem mocks de SQLAlchemy.
- [x] Rodar `uv run pytest`, `make format` e `make lint`.
