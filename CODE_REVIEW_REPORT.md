# 🔍 Flauzino Assistant — Comprehensive Code Review

> **Date:** 2026-08-02  
> **Scope:** Full repository audit against `GEMINI.md` standards + refactoring opportunities  
> **Modules reviewed:** `finance_api`, `agent_api`, `telegram_api`, `tests`, infra & config files

---

## 📊 Executive Summary

| Category | Finance API | Agent API | Telegram API | Infra/Config |
|---|:---:|:---:|:---:|:---:|
| Layered Architecture | ⚠️ 2 issues | 🔴 2 issues | 🔴 3 issues | — |
| Exception Handling | ✅ Excellent | 🔴 4 issues | 🔴 6+ issues | — |
| Async / Blocking | ✅ Excellent | 🔴 2 critical | — | — |
| Code Quality / PEP 8 | ⚠️ 2 issues | ⚠️ 3 issues | — | ⚠️ 4 issues |
| Duplicate Code | ⚠️ 1 issue | ⚠️ 1 issue | 🔴 3 issues | — |
| Test Coverage | — | — | 🔴 Major gaps | — |
| Complex Conditionals | ⚠️ 1 issue | ⚠️ 1 issue | — | — |

**Legend:** ✅ Compliant · ⚠️ Minor/Moderate · 🔴 Critical/Major

---

## 🔴 CRITICAL — Must Fix

These issues either block the event loop, violate core architectural rules, or pose security risks.

### 1. Event Loop Blocking in `agent_api` (Performance Killer)

> [!CAUTION]
> Synchronous CPU/IO-heavy calls inside `async def` will block the **entire FastAPI event loop** for all concurrent users.

| File | Lines | Blocking Call |
|---|---|---|
| [audio.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/services/audio.py) | 40-42, 50 | `model.transcribe()` and `os.remove()` |
| [ocr.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/services/ocr.py) | 106, 109 | `pytesseract.image_to_string()` and `image_to_data()` |

**Fix:** Wrap all blocking calls with `asyncio.to_thread()`:
```python
# Before (blocking)
result = model.transcribe(audio_path)

# After (non-blocking)
result = await asyncio.to_thread(model.transcribe, audio_path)
```

---

### 2. `HTTPException` Raised Inside Services (`agent_api`)

> [!WARNING]
> Direct violation of GEMINI.md rule 3.2: *"NUNCA retorne HTTPException diretamente dos Services ou Repositories."*

| File | Lines | Detail |
|---|---|---|
| [chat.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/services/chat.py) | 141, 145 | Raises `HTTPException` directly in service layer |

**Fix:** Replace with custom exceptions (e.g., `EntityNotFoundError`, `ServiceError`) and let global handlers format the HTTP response.

---

### 3. Raw SQL in Handler — `telegram_api`

| File | Lines | Detail |
|---|---|---|
| [main.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/main.py) | 155-161 | Raw `session.execute(text("SELECT DISTINCT chat_id FROM chat_sessions"))` inside a background job |

**Fix:** Add `get_all_active_chat_ids()` to `SessionRepository` and call it from the job.

---

### 4. Pervasive Generic `except Exception` Blocks

> [!WARNING]
> Found across **both** `agent_api` and `telegram_api`. Violates GEMINI.md rule 3.2 — exceptions should be specific and use custom domain exceptions.

**`agent_api` locations:**
| File | Lines |
|---|---|
| [llm.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/services/llm.py) | 22-25, 37-40 |
| [chat.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/services/chat.py) | 55, 107 |

**`telegram_api` locations:**
| File | Lines |
|---|---|
| [expense_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/expense_handler.py) | 326 |
| [message_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/message_handler.py) | 136, 233 |
| [photo_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/photo_handler.py) | 106 |
| [voice_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/voice_handler.py) | 111 |
| [balance_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/balance_handler.py) | 137 |
| [main.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/main.py) | 169, 172 |

**Fix:** Catch specific exceptions (`httpx.RequestError`, `ValueError`, etc.) and use custom domain exceptions from `core/exceptions.py`.

---

## ⚠️ ARCHITECTURAL VIOLATIONS — Should Fix

### 5. Business Logic Leaking Into Routers/Handlers

**`agent_api` — Routers doing service work:**
| File | Lines | Detail |
|---|---|---|
| [ocr.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/routers/ocr.py) | 68-89 | Router constructs LLM prompt and orchestrates validation |
| [audio.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/routers/audio.py) | 43-57 | Router orchestrates audio flow instead of delegating to service |

**`telegram_api` — Handlers doing everything:**
| File | Lines | Detail |
|---|---|---|
| [balance_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/balance_handler.py) | 110-133 | Direct `httpx` calls to MCP server inside handler |
| [message_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/message_handler.py) | 50-77, 167-186 | Handlers directly manage DB sessions, repositories, HTTP clients |
| [photo_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/photo_handler.py) | 27-72 | Same pattern — handler doing session + API orchestration |
| [voice_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/voice_handler.py) | 33-76 | Same pattern |

**Fix:** Create a `ChatSessionService` in `telegram_api` that manages the interaction between the repository and the agent API. Handlers should only parse Telegram updates and delegate.

---

### 6. Tight Coupling — Services Instantiating Repositories (`finance_api`)

| File | Lines | Detail |
|---|---|---|
| [spents.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/finance_api/services/spents.py) | 32, 39, 122, 130 | `CategoryRepository(self.repo.db)` instantiated inside methods |
| [limits.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/finance_api/services/limits.py) | 30, 123, 132 | Same pattern |
| [spents.py (router)](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/finance_api/routers/spents.py) | 52-57 | Router wires up secondary services/repos for service methods |
| [limits.py (router)](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/finance_api/routers/limits.py) | 52-63 | Same pattern |

**Fix:** Inject all dependent repositories via `__init__` constructors and use FastAPI's `Depends` to wire everything up at the router level.

---

## ⚠️ DUPLICATE CODE — Refactoring Opportunities

### 7. Session Flow Duplication (`telegram_api`) — HIGH IMPACT

> [!IMPORTANT]
> The session management flow (fetch session → call agent API → check `is_complete` → update/delete session) is **copy-pasted** across 3 handlers.

| Files | Pattern |
|---|---|
| [message_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/message_handler.py) | lines 50-77, 167-186 |
| [photo_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/photo_handler.py) | lines 27-72 |
| [voice_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/voice_handler.py) | lines 33-76 |

**Fix:** Extract into a `ChatSessionService.process_user_input(chat_id, message, media_type)` method.

---

### 8. Inline Keyboard Builder Duplication (`telegram_api`)

| Files | Detail |
|---|---|
| [expense_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/expense_handler.py) | lines 38-48 — `build_inline_keyboard` |
| [balance_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/balance_handler.py) | lines 20-42 — `build_inline_keyboard` |
| [message_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/message_handler.py) | lines 80-90 & 188-198 — inline keyboard markup building |

**Fix:** Create `telegram_api/core/ui_utils.py` with a single `build_inline_keyboard()` function.

---

### 9. Category/Payment Validation Duplication (`finance_api`)

| File | Lines | Detail |
|---|---|---|
| [spents.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/finance_api/services/spents.py) | 31-41 vs 120-134 | Identical validation in `create` and `update` |

**Fix:** Extract to `async def _validate_category_and_payment_method(...)`.

---

### 10. Finance API Fetch Duplication (`agent_api`)

| File | Lines | Detail |
|---|---|---|
| [llm.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/services/llm.py) | 13-25 vs 28-39 | `get_valid_categories` and `get_valid_payment_methods` are structurally identical |

**Fix:** Consolidate into `_fetch_finance_options(endpoint: str, fallback: str) -> str`.

---

## ⚠️ CODE QUALITY / PEP 8

### 11. Import Order Violations (`agent_api`)

> [!NOTE]
> GEMINI.md rule 3.4: *"Todos os imports devem ser organizados exclusivamente no topo de cada arquivo."*

| File | Lines | Detail |
|---|---|---|
| [chat.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/services/chat.py) | 15-18 | `import os` and `mcp.client` placed after local imports |
| [decorators.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/core/decorators.py) | 97-98 | Exception imports inside function body |
| [audio.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/services/audio.py) | 16, 56 | Imports inside function |

### 12. Missing Type Hints

| File | Lines | Detail |
|---|---|---|
| [spents.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/finance_api/services/spents.py) | 83 | `inv_service` and `pm_repo` missing types in `get_dashboard` |
| [limits.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/finance_api/services/limits.py) | 84 | `pm_repo` and `inv_service` missing types in `get_balance` |
| [handlers.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/core/handlers.py) | 48, 55, 62, 69 | Missing type hints on `exc` param and return types |

---

## 🔴 TEST COVERAGE GAPS

### 13. Untested Areas in `telegram_api`

| Area | Status |
|---|---|
| `telegram_api/core/` | ❌ No tests |
| `telegram_api/models/` | ❌ No tests |
| `telegram_api/repositories/` | ❌ No tests |
| `telegram_api/main.py` | ❌ No tests |
| `telegram_api/handlers/command_handler.py` | ❌ No tests |
| `telegram_api/handlers/photo_handler.py` | ❌ No tests |
| `telegram_api/handlers/voice_handler.py` | ❌ No tests |

### 14. Duplicate Test Fixtures

| Files | Detail |
|---|---|
| [test_expense_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/tests/telegram_api/handlers/test_expense_handler.py) (29-44) | Identical `mock_update`/`mock_context` fixtures |
| [test_message_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/tests/telegram_api/handlers/test_message_handler.py) (10-37) | Same fixtures duplicated |

**Fix:** Move shared fixtures to `tests/telegram_api/conftest.py`.

---

## ⚠️ INFRASTRUCTURE & CONFIG ISSUES

### 15. Documentation Drift

| Issue | Detail |
|---|---|
| Model version mismatch | README says `gemini-2.5-flash`, `.env.example` uses `gemini-2.0-flash-exp` |
| Missing MCP Server docs | `mcp_server` is in Docker stack but not documented in README |
| Incomplete `.env` example in README | Missing `ALLOWED_TELEGRAM_USERNAMES`, `MCP_SERVER_URL` |
| Missing `MCP_SERVER_URL` in `.env.example` | Referenced in `docker-compose.yml` but absent from `.env.example` |

### 16. Hardcoded Credentials in Scripts

| File | Detail |
|---|---|
| [backup_db.sh](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/scripts/backup_db.sh) | Hardcoded `pg_dump -U flauzino -d assistant` ignores `.env` variables |
| [backup_db.sh](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/scripts/backup_db.sh) | Hardcoded container name `infra-db-1` is fragile |
| [docker-compose.yml](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/infra/docker-compose.yml) | Fallback password `password` in `DATABASE_URL` |

### 17. Missing Makefile Target

No `run-mcp` target exists despite `mcp_server` being a component.

---

## 🏗️ OTHER REFACTORING OPPORTUNITIES

### 18. God Function: `process_message` (`agent_api`)

| File | Lines | Detail |
|---|---|---|
| [chat.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/services/chat.py) | 29-134 | 100+ line function handling message saving, LLM, balance queries, and MCP graph orchestration |

**Fix:** Split into `_handle_balance_query()` and `_generate_mcp_graph()`.

### 19. Inconsistent Service Return Types (`finance_api`)

| File | Detail |
|---|---|
| [invoices.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/finance_api/services/invoices.py) | `list_previews` returns Pydantic models while other services return SQLAlchemy models |

**Fix:** Standardize — services should return domain models; Pydantic serialization belongs in the router layer.

### 20. Hardcoded Constants (`agent_api`)

| File | Lines | Detail |
|---|---|---|
| [main.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/agent_api/main.py) | 39-40 | `CLEANUP_INTERVAL_SECONDS` and `STALE_SESSION_MAX_AGE_MINUTES` should be in `settings.py` |

### 21. Complex Date Logic (`finance_api`)

| File | Lines | Detail |
|---|---|---|
| [limits.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/finance_api/services/limits.py) | 96-121 | Deeply nested date-checking logic for dashboard balance |

**Fix:** Encapsulate "determine active period" logic inside `InvoiceService`.

---

## ✅ What's Working Well

| Area | Status |
|---|---|
| `finance_api` exception handling | Uses `@handle_service_errors` decorator consistently ✅ |
| `finance_api` async DB access | All `AsyncSession` calls properly `await`-ed ✅ |
| Custom exceptions in `finance_api` | `EntityNotFoundError`, `EntityConflictError`, `DatabaseError` properly defined ✅ |
| Global exception handlers | Centralized in `main.py` as designed ✅ |
| `.specs/` directory usage | Implementation plans are being tracked ✅ |
| `.env.example` exists | Most env vars documented ✅ |

---

## 📋 Prioritized Action Plan

### Phase 1 — Critical Fixes (Safety & Performance)
1. Wrap blocking calls in `agent_api` with `asyncio.to_thread()` (audio + OCR)
2. Remove `HTTPException` from `agent_api/services/chat.py`
3. Replace generic `except Exception` blocks across `agent_api` and `telegram_api`

### Phase 2 — Architecture Alignment
4. Create `ChatSessionService` in `telegram_api` to consolidate handler logic
5. Fix DI in `finance_api` — inject repos via constructors
6. Move raw SQL from `telegram_api/main.py` to repository
7. Move business logic out of `agent_api` routers (audio + OCR)

### Phase 3 — Code Deduplication
8. Extract `build_inline_keyboard` to shared `ui_utils.py`
9. Consolidate `_fetch_finance_options` in `agent_api/services/llm.py`
10. Extract `_validate_category_and_payment_method` in `finance_api`

### Phase 4 — Quality & Documentation
11. Fix import ordering and missing type hints
12. Update README with MCP server docs and correct model version
13. Fix `backup_db.sh` to use env variables
14. Add `run-mcp` to Makefile

### Phase 5 — Test Coverage
15. Create `tests/telegram_api/conftest.py` with shared fixtures
16. Write tests for `telegram_api` repositories, core, and missing handlers
