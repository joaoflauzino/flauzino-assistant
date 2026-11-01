# Plano Diretor — Refatoração Focada em Qualidade de Código

> Objetivo: eliminar **ifs profundos/encadeados** e **métodos grandes com múltiplas responsabilidades**, aplicando as skills oficiais do repositório (`python-zen-of-python`, `python-pep8-guidelines`, `python-anti-patterns`, `python-pattern-strategy`, `python-pattern-chain-of-responsibility`, `python-pattern-factory`, `python-pattern-repository-service`, `python-fastapi-architecture`, `python-modular-code-organization`).
>
> Branch de trabalho: `feat/refactor` (já contém refatorações anteriores — este plano é incremental e não reescreve o que já foi feito).
>
> **Status:** aguardando aprovação humana antes de qualquer implementação/commit.

---

## 1. Princípios que guiam este plano

1. **Guard Clauses primeiro** (`python-zen-of-python`): retorno antecipado substitui `if` aninhado. Regra do `AGENTS.md` §3.4: **máximo 3 condicionais por função**.
2. **Extract Function / SRP**: cada método faz uma coisa. Métodos > ~40 linhas são candidatos a decomposição.
3. **Substituir cascata por dado** (`python-pattern-strategy`): `if/elif` sobre um mesmo discriminador vira `dict[StrEnum, Strategy]`.
4. **Pipeline sequencial → Chain of Responsibility** quando as condições são etapas de decisão (`python-pattern-chain-of-responsibility`).
5. **Criação condicional → Factory + Registry** (`python-pattern-factory`).
6. **Sem `except Exception: pass`** (`python-anti-patterns`): exceções específicas, logadas e reerguidas; erros de domínio nunca viram `HTTPException` no service.
7. **Read Before Write**: cada extração vem acompanhada do teste de regressão existente.
8. **Nenhuma mudança de comportamento**: refatoração pura. Se um bug for encontrado no caminho, ele é registrado e corrigido em commit separado.

---

## 2. Linha de base medida (working tree atual)

Funções de produção com excesso de tamanho / profundidade / condicionais (AST scan, sem testes):

| Arquivo:linha | Função | LOC | Profundidade | `if`s | Problema central |
|---|---|---:|---:|---:|---|
| `finance_api/importers/c6_credit_card_csv.py:41` | `parse` | 179 | 3 | 20 | 4 responsabilidades: decode, CSV, normalização, montagem de metadata |
| `agent_api/services/tools.py:19` | `create_agent_tools` | 170 | 0 | 3 | 6 tools aninhadas na mesma função fábrica |
| `agent_api/services/agent.py:40` | `get_system_prompt` | 143 | 2 | 2 | fetch de 5 fontes + branch de plataforma + template gigante |
| `finance_api/importers/c6_checking_csv.py:32` | `parse` | 131 | 4 | 12 | idem cartão; duplicação com o parser de cartão |
| `telegram_api/main.py:38` | `main` | 110 | 1 | 8 | middleware + registro de handlers + jobs + shutdown |
| `finance_api/services/imports.py:145` | `_build_staged_transactions` | 74 | 3 | 2 | classificação + dedup + competência + montagem |
| `finance_api/services/imports.py:270` | `create_batch_from_upload` | 70 | 1 | 3 | 8 etapas de orquestração |
| `finance_api/services/payment_resolution.py:42` | `resolve` | 68 | 5 | 8 | fallback em cascata + `inspect` defensivo + `except Exception` |
| `finance_api/services/imports.py:627` | `reclassify_batch` | 68 | 5 | 5 | regra + IA + persistência no mesmo método |
| `finance_api/services/imports.py:427` | `update_transaction` | 55 | 3 | 15 | patch campo-a-campo + validações |
| `agent_api/core/callbacks.py:46` | `on_llm_end` | 53 | 5 | 7 | métricas + extração de tokens + log |
| `telegram_api/core/formatter.py:18` | `markdown_to_telegram_html` | 76 | 1 | 2 | 10 etapas de regex (ok, mas monolítico) |
| `telegram_api/core/formatter.py:96` | `send_agent_reply` | 60 | 4 | 7 | try/except duplicado foto vs texto |
| `telegram_api/handlers/balance_handler.py:64` | `select_category` | 59 | 6 | 7 | 4 ações de callback em cascata |
| `telegram_api/handlers/expense_handler.py:293` | `confirm_expense` | 49 | 4 | 5 | 3 tipos de registro em cascata |
| `finance_api/services/invoices.py:87` | `update_invoice_dates` | 43 | 2 | 6 | patch vs criação + cálculo de vencimento |
| `finance_api/services/imports.py:484` | `bulk_action` | 37 | 4 | 5 | loop com 4 ramos de outcome |

**Duplicação entre parsers C6** (`c6_credit_card_csv.py` × `c6_checking_csv.py`):
- fallback de decodificação (`utf-8-sig`/`utf-8`/`latin-1`);
- `parse_dec` (normalização de `R$`, vírgula/ponto);
- `occurrence_tracker` (detecção de ocorrências repetidas);
- busca de header e mensagens de erro.

---

## 3. Estratégia de priorização

| Fase | Escopo | Impacto | Risco | Ordem |
|---|---|---|---|---|
| 0 | Gates de complexidade + rede de segurança | Alto | Baixo | 1º |
| 1 | `ImportService` (god class de 700 linhas) | Muito alto | Médio | 2º |
| 2 | Parsers C6 (helpers compartilhados + decomposição) | Alto | Médio | 3º |
| 3 | `PaymentResolutionService` (remover cascata/hacks) | Alto | Baixo | 4º |
| 4 | `agent_api` (tools, prompt, classify, callbacks) | Alto | Médio | 5º |
| 5 | `telegram_api` (handlers, formatter, `main`) | Médio-alto | Médio | 6º |
| 6 | Ajustes pontuais (invoices, spents, repositories) | Médio | Baixo | 7º |

Regra de execução: **uma fase = um PR/commit independente**, com testes verdes e diff revisável. Não misturar fases.

---

## 4. Fase 0 — Rede de segurança e gates (primeiro, sem refatorar)

### 4.1 Adicionar gate de complexidade no `ruff`
`pyproject.toml` hoje seleciona `E, F, W, I, UP`. Adicionar `C90` (mccabe) com teto explícito:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "C90"]
[tool.ruff.lint.mccabe]
max-complexity = 10
```

Opcional (segundo gate): `PLR0912` (branches) e `PLR0915` (statements) via `flake8-pyi`/`pylint` rules, se não gerar ruído excessivo. Se gerar, aplicar `# noqa` apenas nos casos já mapeados neste documento e ir zerando fase a fase.

### 4.2 Caracterizar comportamento antes de mexer
Antes de cada extração, garantir que existe teste cobrindo o caminho. Onde não houver:
- **ImportService**: `finance_api/tests/services/test_imports_service.py` já cobre upload, commit, bulk e reclassify — completar cenários de borda (sem `new_pairs`, duplicatas, falha de IA).
- **Parsers C6**: existem `test_c6_parser.py` e `test_c6_credit_card_parser.py` — adicionar fixtures de encoding inválido, valores `1.235,25`, parcela `01/12`, linha de header ausente.
- **Telegram handlers**: mocks de `http_client` e `query` cobrindo cada `callback_data`.
- **Prompt do agente**: snapshot/serialização do texto (não comparar string inteira, mas garantir presença de seções obrigatórias).

### 4.3 Comandos de verificação (após cada fase)
```bash
make format
make lint
uv run pytest finance_api/tests agent_api/tests telegram_api/tests graph_api/tests
```

**Critério de saída da Fase 0:** baseline de testes verde, `ruff C90` configurado e lista de violações congelada (dívida visível).

---

## 5. Fase 1 — `ImportService`: quebrar a god class

**Arquivo:** `finance_api/services/imports.py` (700 linhas, 18 métodos).

**Diagnóstico:** a classe acumula 6 responsabilidades distintas:
1. Upload/parse de lote (`create_batch_from_upload`, `_calc_sha256`, `_calc_fingerprint`, `_build_fingerprint_map`).
2. Staging/classificação/deduplicação (`_build_staged_transactions`, `_enrich_with_batch_ai`).
3. Leitura/apresentação (`list_batches`, `list_transactions`, `_to_tx_response`, `get_summary`).
4. Mutação de transações (`update_transaction`, `_validate_category_for_kind`, `link_transaction`).
5. Ações em lote (`bulk_action`).
6. Efetivação (`commit_approved`, `_resolve_commit_context`, `reclassify_batch`).

**Decomposição proposta (respeitando `route -> service -> repository`):**

| Novo componente | Responsabilidade | Métodos movidos |
|---|---|---|
| `ImportFingerprint` (Value Object / helper puro) | sha256, fingerprint, mapa | `_calc_sha256`, `_calc_fingerprint`, `_build_fingerprint_map` |
| `StagingBuilder` (domain service) | classificar + deduplicar + montar `StagedTransaction` | `_build_staged_transactions` |
| `BatchEnrichmentService` | enriquecimento por IA (usado no upload **e** no reclassify) | `_enrich_with_batch_ai` + trecho de `reclassify_batch` |
| `ImportBatchPresenter` | montar respostas (batch, tx, duplicate info) | `_build_batch_response`, `_to_tx_response` |
| `ImportCommitService` | commit + resolução de contexto + contadores | `commit_approved`, `_resolve_commit_context` |
| `ImportReclassifyService` | regra + IA + persistência | `reclassify_batch` |
| `ImportBatchRepository` (já existe) | contagens e consultas | manter |

`ImportService` fica como **fachada/coordenador** fino: upload, listagem, update, bulk, summary. Injeção via `__init__` (sem `Depends` pesado novo; os defaults continuam construindo as dependências atuais).

**Destaques de refatoração local:**

1. `create_batch_from_upload` (8 etapas) → pipeline explícito:
```python
parser = self._detect_parser(file_bytes, filename)
target = await self._resolve_target(parser.statement_type, account_id, credit_card_id)
file_sha256 = self._fingerprints.sha256(file_bytes)
await self._ensure_not_duplicated(file_sha256, filename)
parsed = parser.parse(file_bytes, filename)
batch = await self._create_batch(parsed, target, file_sha256, filename)
return await self._stage_and_finalize(batch, parsed, target, parser)
```

2. `update_transaction` (15 `if`s campo-a-campo) → aplicar o anti-pattern fix do `python-anti-patterns`:
   - `data.model_dump(exclude_unset=True)` para patch declarativo;
   - validações por `dict[field, validator]` ou funções `_validate_kind`, `_validate_status`, `_validate_category`;
   - regra de "limpar categoria" vira método `_normalize_kind`.

3. `reclassify_batch` + `_enrich_with_batch_ai` duplicam montagem de payload/categorias → extrair `BatchEnrichmentService.build_payload()` e `apply_suggestions()`, reutilizado pelos dois fluxos.

4. `commit_approved` com `if/elif` sobre `CommitOutcomeStatus` → contadores via `Counter` + slice de despacho, ou `dict[status, attr]`.

**Testes:** `tests/services/test_imports_service.py`, `test_import_strategies.py`, `test_dashboard_strategies.py` (regressão). Criar testes unitários para os novos componentes com fakes (sem banco).

**Critério de saída:** `imports.py` < ~250 linhas; nenhuma função > 40 linhas / > 3 condicionais; testes verdes; `ruff C90` sem violação nesses arquivos.

---

## 6. Fase 2 — Parsers C6: eliminar duplicação e decompor `parse`

**Arquivos:** `finance_api/importers/c6_credit_card_csv.py`, `finance_api/importers/c6_checking_csv.py`.

**Padrões:** Extract Function + Extract Class + Template Method (sem herança pesada; helpers puros são preferíveis) + Value Objects.

**Novo módulo `finance_api/importers/c6_common.py`:**
```python
def decode_with_fallback(content: bytes) -> str: ...
def parse_brl_decimal(value: str | None) -> Decimal: ...
class OccurrenceTracker:
    def next_index(self, key: tuple) -> int: ...
def find_header_index(lines: list[str], predicate: Callable[[str], bool]) -> int: ...
```

**Decomposição de `parse`** (cartão 179 → ~40 linhas orquestrando):
- `_decode(content) -> str`
- `_extract_lines(text) -> list[str]`
- `_find_header(lines) -> int`
- `_read_rows(lines, header_idx) -> list[dict]`
- `_parse_transaction(row, tracker) -> ParsedTransaction | None` (retorna `None` para linhas ignoráveis)
- `_extract_metadata(lines, filename, dates, card_names) -> StatementMetadata`

O mesmo template para o checking. Depois, avaliar extrair uma classe base `BaseC6CsvParser` com o esqueleto `parse()` e hooks `_header_predicate`, `_parse_row`, `_build_metadata` (Template Method) — só se a duplicação restante justificar e sem prejudicar legibilidade.

**Atenção:** `parse_dec` fica **fora** do loop e vira helper compartilhado (hoje é redefinido a cada iteração no checking).

**Testes:** `tests/importers/test_c6_parser.py`, `test_c6_credit_card_parser.py` + novos casos de borda. Adicionar teste comparando os dois parsers no mesmo helper.

**Critério de saída:** nenhum `parse` > 40 linhas; zero duplicação de `parse_dec`/decode/tracker; testes verdes.

---

## 7. Fase 3 — `PaymentResolutionService`: remover cascata e hacks defensivos

**Arquivo:** `finance_api/services/payment_resolution.py` (`resolve`, 68 linhas, profundidade 5).

**Problemas:**
- `try/except Exception` em volta de lookups de repositório → viola `AGENTS.md` §3.2 e `python-anti-patterns` (swallowed exceptions).
- `inspect.iscoroutine(...)` e `hasattr(card, "id")` → defesa contra mocks/async errado vazando para produção.
- Cascata "cartão → conta → fallback" implementada com `if`s sequenciais.

**Refatoração:**
1. **Chain of Responsibility** (`python-pattern-chain-of-responsibility`), como já descrito no `02-chain-of-responsibility-classification.md`, com handlers `DirectCardHandler` → `AccountHandler` → `FallbackHandler`.
2. Repositórios retornam entidades tipadas; remover `inspect`/`hasattr`. Se um teste precisa disso, o problema é o mock — corrigir o teste.
3. Erros de banco **não** são engolidos: apenas `EntityNotFound`/`None` seguem para o próximo handler; exceções inesperadas sobem (decorator global loga).
4. Extrair `PAYMENT_TYPE_BY_ACCOUNT` como `dict`/`frozenset` (já existe `VALID_ACCOUNT_PAYMENT_TYPES`) e uma função pura `_resolve_account_payment_type`.

**Testes:** `tests/services/test_payment_resolution.py` (já existe) — cobrir cartão, conta, fallback, hint e tipo inválido. Remover mocks que dependem de `inspect`.

**Critério de saída:** `resolve` sem `try/except Exception`, ≤ 3 condicionais, sem `inspect`; testes verdes.

---

## 8. Fase 4 — `agent_api`: tools, prompt, classify, callbacks

### 8.1 `agent_api/services/tools.py` — `create_agent_tools` (170 linhas)
**Problema:** 6 closures de tool + lista final na mesma função.
**Refatoração:** um módulo/classe por tool (`tools/balance.py`, `tools/spending.py`, `tools/income.py`, `tools/limit.py`, `tools/graph.py`) cada um expondo `build_*_tool(finance_service, graph_service) -> BaseTool`. `create_agent_tools` passa a ser um **Factory Registry**:
```python
TOOL_BUILDERS: tuple[Callable[..., BaseTool], ...] = (
    build_consultar_saldos, build_registrar_gasto, build_registrar_receita,
    build_consultar_balanco_mensal, build_cadastrar_limite, build_gerar_grafico,
)
def create_agent_tools(...) -> list[BaseTool]:
    return [build(finance_service, graph_service) for build in TOOL_BUILDERS]
```
Preservar `@tool` + `@handle_tool_errors` e docstrings (o LLM depende delas).

### 8.2 `agent_api/services/agent.py` — `get_system_prompt` (143 linhas)
**Problema:** 5 awaits + tratamento de erro + branch de plataforma + template monolítico.
**Refatoração:**
- `PromptMetadata` (dataclass) + `_load_prompt_metadata()` com `asyncio.gather` e fallback em um único `try` (log uma vez).
- **Strategy/dispatch** para plataforma: `PLATFORM_INSTRUCTIONS: dict[str, str]` (`telegram`, `web`, default).
- Template como constante `SYSTEM_PROMPT_TEMPLATE` + `format_prompt(metadata, platform_instructions)`.
- `get_system_prompt` final: 1 load + 1 lookup + 1 format (≤ 10 linhas).

### 8.3 `agent_api/services/classify.py` — `classify_transactions` (65 linhas)
**Refatoração:** extrair `_build_tx_payload`, `_sanitize_suggestions(result, tx_dict, expense_keys, income_keys)` (o loop com `if/continue` vira guard clauses) e `_assemble_response`. O `try/except` continua, mas só envolve a chamada do LLM.

### 8.4 `agent_api/core/callbacks.py` — `on_llm_end` (53 linhas)
**Refatoração:** `_extract_token_usage(response) -> TokenUsage` (dataclass), `_record_metrics(model, elapsed, usage)`, `_log_end(...)`. `on_llm_end` fica linear e raso.

**Testes:** `tests/services/test_agent_service.py`, `test_classify_service.py`, `tests/core/test_callbacks_metrics.py`; adicionar teste de registry de tools e de mapeamento de plataforma.

**Critério de saída:** `tools.py` sem função > 20 linhas; `get_system_prompt` ≤ 15 linhas; `on_llm_end` ≤ 20 linhas; testes verdes.

---

## 9. Fase 5 — `telegram_api`: handlers, formatter e bootstrap

### 9.1 `balance_handler.py` — `select_category` (59 linhas, 4 ramos de `callback_data`)
**Refatoração:** dispatch table de ações (`all`, `none`, `cat:*`, `generate`) + funções `_select_all`, `_select_none`, `_toggle_category`, `_generate_graph`. Cada uma curta; `select_category` só resolve a ação e delega.
```python
def _resolve_action(data: str) -> Callable: ...
# ou dict com prefixo + handler específico
```

### 9.2 `expense_handler.py` — `confirm_expense` (49 linhas, 3 tipos de registro)
**Refatoração:** **Strategy/Factory por `purchase_type`** (`avista`/`parcelada`/`assinatura`):
```python
PURCHASE_SAVERS: dict[str, Callable[[dict], Awaitable[None]]] = {
    "a_vista": _save_spent, "parcelada": _save_installment, "assinatura": _save_subscription,
}
```
`confirm_expense` só trata o callback, chama o saver e faz o cleanup/erro.

### 9.3 `formatter.py` — `send_agent_reply` (60 linhas)
**Problema:** bloco `try/except BadRequest` + fallback praticamente duplicado para foto e texto.
**Refatoração:** `_is_parse_error(exc)`, `_send_photo(...)`, `_send_text(...)`, `_send_with_html_fallback(send_fn, formatted, plain)`. `send_agent_reply` só escolhe o canal.
`markdown_to_telegram_html` (76 linhas): opcionalmente, transformar em lista ordenada de `(pattern, replacement)` aplicada por um loop — reduz o corpo e facilita testar cada regra. Baixo risco, ganho de legibilidade.

### 9.4 `telegram_api/main.py` — `main` (110 linhas)
**Refatoração:**
- `auth_middleware` → `telegram_api/core/middleware.py` com `_detect_message_type(update)` extraído.
- `_register_handlers(application)`.
- `_schedule_jobs(application)` e `post_init`/`post_shutdown` enxutos.
- `main` vira: criar app → registrar middleware → registrar handlers → agendar jobs → `run_polling` (≤ 30 linhas).

**Testes:** `tests/handlers/test_balance_handler.py`, `test_expense_handler.py`, `tests/core/test_formatter.py` + novo `test_middleware.py`. Cobrir cada `callback_data` e os fallbacks de formatação.

**Critério de saída:** nenhum handler > 30 linhas; `main` ≤ 30 linhas; testes verdes.

---

## 10. Fase 6 — Ajustes pontuais

1. **`finance_api/services/invoices.py:update_invoice_dates`**: separar `_patch_invoice(invoice, closing, due, status)` de `_create_invoice(...)`, com guard clause para criação. Cálculo de vencimento fica no helper já existente (`resolve_due_reference_month`).
2. **`finance_api/services/spents.py:update`**: aplicar patch declarativo (`model_dump(exclude_unset=True)`) e extrair `_resolve_payment_fields(update_data)`, removendo `if` campo-a-campo.
3. **`finance_api/repositories/staged_transactions.py:list_by_filter`**: já usa lista de condições (bom). Extrair `_build_conditions(...)` e `_apply_pagination(...)`; não é prioridade.
4. **`finance_api/services/imports.py:bulk_action`**: extrair `_apply_strategy(tx, strategy, req)` que retorna um `StepOutcome`, e um reducer de contadores.

---

## 11. Ordem de execução sugerida (commits pequenos)

1. `chore(lint): add complexity gate (ruff C90)` + congelar violações.
2. `test(imports): add characterization tests for edge cases`.
3. `refactor(imports): extract fingerprint/staging/presenter collaborators`.
4. `refactor(imports): extract commit/reclassify/enrichment services`.
5. `refactor(imports): declarative update_transaction patch`.
6. `refactor(importers): extract c6_common helpers`.
7. `refactor(importers): decompose c6 parse methods`.
8. `refactor(payments): replace resolution cascade with CoR`.
9. `refactor(agent): split tools into registry`.
10. `refactor(agent): split system prompt metadata/platform/template`.
11. `refactor(agent): decompose classify and llm callback`.
12. `refactor(telegram): dispatch callback actions and purchase savers`.
13. `refactor(telegram): extract middleware/bootstrap/formatter helpers`.
14. `refactor(finance): split invoice dates and spent patch`.

Cada commit: `make format` + `make lint` + suíte completa verde. **Nenhum commit/push sem autorização explícita** (`AGENTS.md` §7).

---

## 12. Definição de pronto (quality gates)

- [ ] Nenhuma função de produção com **mais de 3 condicionais** (§3.4 do `AGENTS.md`).
- [ ] Nenhuma função de produção com **profundidade de aninhamento ≥ 4**.
- [ ] Nenhuma função de produção com **> 40 linhas**, salvo justificativa documentada.
- [ ] Zero `except Exception: pass`; exceções específicas e domínio puro.
- [ ] `ruff C90 max-complexity=10` sem violações nos arquivos refatorados.
- [ ] Testes unitários para cada colaborador extraído (fakes, sem banco real).
- [ ] `make format`, `make lint` e `uv run pytest` verdes.
- [ ] Diff revisado com o `git diff` apresentado ao usuário antes de qualquer commit.
- [ ] Nenhuma mudança de contrato HTTP externo (a menos que explicitamente acordada).

---

## 13. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Refatoração alterar comportamento sutil (ex.: dedup/parsers) | Testes de caracterização antes; comparar saída dos parsers em fixtures reais; refatorar em passos pequenos |
| Quebrar imports do `ImportService` em `dependencies.py` | Manter a assinatura pública de `ImportService`; criar fakes/injeção com defaults; rodar `test_imports_router.py` |
| Mocks frágeis em `payment_resolution` | Corrigir mocks que simulam async errado em vez de manter `inspect` no código de produção |
| Scope creep | Cada fase é isolada; bugs encontrados viram issue/commit separado |
| Fadiga de revisão | PRs pequenos por fase, na ordem acima |

---

## 14. Referências das skills aplicadas

- `~/.gemini/skills/python-zen-of-python` → guard clauses, flat over nested, explicit over implicit.
- `~/.gemini/skills/python-pep8-guidelines` → limite de 3 condicionais, tipagem, imports.
- `~/.gemini/skills/python-anti-patterns` → atualização declarativa, exceções, I/O vs lógica.
- `~/.gemini/skills/python-pattern-strategy` → dispatch tables para `callback_data`/`purchase_type`.
- `~/.gemini/skills/python-pattern-chain-of-responsibility` → resolução de pagamento e classificação.
- `~/.gemini/skills/python-pattern-factory` → registry de tools e criação condicional.
- `~/.gemini/skills/python-pattern-repository-service` → contratos/fakes e fronteiras de camada.
- `~/.gemini/skills/python-fastapi-architecture` → router/service/repository e exceções de domínio.
- `~/.gemini/skills/python-modular-code-organization` → separação em módulos por responsabilidade e schemas/protocols.
