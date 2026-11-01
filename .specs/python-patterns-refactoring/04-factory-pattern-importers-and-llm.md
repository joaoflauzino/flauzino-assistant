# Fase 4: Factory & Registry Pattern nos Importadores de Extrato e Provedores de LLM

**Skill aplicada:** `python-pattern-factory`  
**Serviços-alvo:** `finance_api` (`finance_api/importers/` e `finance_api/services/imports.py`) e `agent_api` (`agent_api/core/llm.py`)

---

## 1. Diagnóstico Detalhado (Estado Atual)

### 1.1. Importadores de Extrato e Resolução de Conta/Cartão (`finance_api`)
- Em `finance_api/importers/registry.py`, existe uma lista global estática `_PARSERS` e uma função `detect_parser(content, filename)`.
- Porém, em `finance_api/services/imports.py` (linhas 116-148), a lógica que resolve qual **Conta Bancária** ou **Cartão de Crédito** está vinculada ao extrato importado vaza detalhes de implementação específicos do banco (`if "c6" in c.key.lower()`) e do `StatementType` (`if is_credit_card: ... else: ...`) diretamente para dentro do `ImportService`.
- Isso quebra o **Princípio Aberto/Fechado (OCP)**: ao adicionar um extrato do Nubank ou Itaú, será necessário editar o `ImportService` em vez de apenas registrar uma nova família de importador.

### 1.2. Instanciação Rígida de LLM (`agent_api/core/llm.py`)
- Atualmente, `get_llm()` usa `@lru_cache` e retorna uma instância fixa de `ChatOpenAI` com `reasoning_effort="none"` para todos os casos de uso (tanto para o agente conversacional quanto para o classificador em lote `ClassifyService`).
- Uma **LLM Factory com Registry** permite criar perfis ou provedores distintos (`AGENT_CHAT` vs `BATCH_CLASSIFIER`, ou `OpenAI` vs `OpenRouter`/`Anthropic`) mantendo o contrato estrutural `BaseChatModel`.

---

## 2. Solução Proposta (Python 3.13+ Idiomático)

### 2.1. Factory + Registry para Parsers e Target Resolvers (`finance_api/importers/registry.py`)

Seguindo a skill `python-pattern-factory`, transformamos o módulo de importação em uma `StatementImporterFactory` injetável que resolve tanto o `StatementParser` quanto o `ImportTargetResolver` correspondente ao `StatementType`:

```python
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.importers.base import StatementParser, StatementType
from finance_api.importers.c6_checking_csv import C6CheckingCsvParser
from finance_api.importers.c6_credit_card_csv import C6CreditCardInvoiceCsvParser
from finance_api.repositories.accounts import AccountRepositoryProtocol
from finance_api.repositories.credit_cards import CreditCardRepositoryProtocol


class ParserKey(StrEnum):
    C6_CHECKING_CSV = "c6_checking_csv"
    C6_CREDIT_CARD_CSV = "c6_credit_card_csv"


@dataclass(frozen=True)
class ResolvedImportTarget:
    account_id: UUID | None
    credit_card_id: UUID | None
    target_key: str
    target_name: str | None


# ---------------------------------------------------------------------------
# 1. Product Interface para Resolução de Destino (Protocol)
# ---------------------------------------------------------------------------
class ImportTargetResolver(Protocol):
    async def resolve(
        self,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        bank_hint: str | None = None,
    ) -> ResolvedImportTarget:
        ...


# ---------------------------------------------------------------------------
# 2. Concrete Products (CreditCardTargetResolver & CheckingAccountTargetResolver)
# ---------------------------------------------------------------------------
class CreditCardTargetResolver:
    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        credit_card_repo: CreditCardRepositoryProtocol,
    ) -> None:
        self._account_repo = account_repo
        self._credit_card_repo = credit_card_repo

    async def resolve(
        self,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        bank_hint: str | None = None,
    ) -> ResolvedImportTarget:
        if not credit_card_id and account_id:
            cards, _ = await self._credit_card_repo.list(account_id=account_id)
            if cards:
                credit_card_id = cards[0].id

        if credit_card_id and not account_id:
            card = await self._credit_card_repo.get_by_id(credit_card_id)
            if card:
                account_id = card.account_id

        if not credit_card_id and bank_hint:
            all_cards, _ = await self._credit_card_repo.list(page=1, size=100)
            matched = [c for c in all_cards if bank_hint.lower() in c.key.lower()]
            if matched:
                credit_card_id = matched[0].id
                account_id = matched[0].account_id

        if not credit_card_id:
            raise ValidationError("Informe o cartão de crédito para a importação da fatura.")

        card = await self._credit_card_repo.get_by_id(credit_card_id)
        if not card:
            raise EntityNotFoundError(f"Cartão com ID {credit_card_id} não encontrado")

        return ResolvedImportTarget(
            account_id=account_id or card.account_id,
            credit_card_id=card.id,
            target_key=card.key,
            target_name=card.name,
        )


class CheckingAccountTargetResolver:
    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        credit_card_repo: CreditCardRepositoryProtocol,
    ) -> None:
        self._account_repo = account_repo
        self._credit_card_repo = credit_card_repo

    async def resolve(
        self,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        bank_hint: str | None = None,
    ) -> ResolvedImportTarget:
        if credit_card_id and not account_id:
            card = await self._credit_card_repo.get_by_id(credit_card_id)
            if card:
                account_id = card.account_id

        if not account_id:
            raise ValidationError("Informe a conta bancária para a importação do extrato.")

        acc = await self._account_repo.get_by_id(account_id)
        if not acc:
            raise EntityNotFoundError(f"Conta com ID {account_id} não encontrada")

        return ResolvedImportTarget(
            account_id=acc.id,
            credit_card_id=None,
            target_key=acc.key,
            target_name=acc.name,
        )


# ---------------------------------------------------------------------------
# 3. Factory com Registry para Parsers de Extrato
# ---------------------------------------------------------------------------
type ParserCreator = Callable[[], StatementParser]


class StatementParserFactory:
    def __init__(self) -> None:
        self._registry: dict[ParserKey, ParserCreator] = {}

    def register(self, key: ParserKey, creator: ParserCreator) -> None:
        """Registra um criador de parser validado pelo Protocol StatementParser."""
        self._registry[key] = creator

    def create_by_key(self, key: ParserKey) -> StatementParser:
        creator = self._registry.get(key)
        if creator is None:
            supported = ", ".join(self._registry.keys())
            raise ValidationError(f"Parser '{key}' não suportado. Opções: [{supported}]")
        return creator()

    def detect_and_create(self, content: bytes, filename: str) -> StatementParser:
        for creator in self._registry.values():
            parser = creator()
            if parser.can_parse(content, filename):
                return parser
        raise ValidationError(
            f"Formato do arquivo '{filename}' não reconhecido. "
            "Atualmente suportamos extrato CSV e fatura de cartão de crédito C6."
        )


def build_default_parser_factory() -> StatementParserFactory:
    factory = StatementParserFactory()
    factory.register(ParserKey.C6_CHECKING_CSV, C6CheckingCsvParser)
    factory.register(ParserKey.C6_CREDIT_CARD_CSV, C6CreditCardInvoiceCsvParser)
    return factory
```

Com isso, o início de `ImportService.create_batch_from_upload` cai de **40 linhas de condicionais aninhadas** para **4 linhas limpas**:

```python
parser = self._parser_factory.detect_and_create(file_bytes, filename)
resolver = self._target_resolvers[parser.statement_type]
target = await resolver.resolve(account_id, credit_card_id, bank_hint="c6")
```

---

### 2.2. Factory + Registry para Modelos LLM (`agent_api/core/llm.py`)

Aplicamos o padrão Factory com `StrEnum` para desacoplar a criação de modelos de linguagem por perfil de uso:

```python
from collections.abc import Callable
from enum import StrEnum

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from agent_api.core.exceptions import LLMProviderError
from agent_api.settings import settings


class LLMProfile(StrEnum):
    CHAT_AGENT = "chat_agent"
    BATCH_CLASSIFIER = "batch_classifier"


type LLMCreator = Callable[[], BaseChatModel]


class LLMFactory:
    def __init__(self) -> None:
        self._registry: dict[LLMProfile, LLMCreator] = {}

    def register(self, profile: LLMProfile, creator: LLMCreator) -> None:
        self._registry[profile] = creator

    def create(self, profile: LLMProfile = LLMProfile.CHAT_AGENT) -> BaseChatModel:
        creator = self._registry.get(profile)
        if creator is None:
            supported = ", ".join(self._registry.keys())
            raise LLMProviderError(f"Perfil de LLM '{profile}' não registrado. Suportados: [{supported}]")
        return creator()
```

---

## 3. Checklist de Execução e Testes (Fase 4)

- [ ] Modernizar `StatementType` em `finance_api/importers/base.py` para herdar de `StrEnum`.
- [ ] Refatorar `finance_api/importers/registry.py` implementando `StatementParserFactory` e os resolvers `CreditCardTargetResolver` e `CheckingAccountTargetResolver`.
- [ ] Injetar `StatementParserFactory` e o dicionário de `ImportTargetResolver` no `ImportService` via `finance_api/core/dependencies.py`.
- [ ] Implementar `LLMFactory` em `agent_api/core/llm.py` mantendo compatibilidade com `get_llm()` para os testes existentes.
- [ ] Executar `uv run pytest` para validar os parsers e o fluxo de upload de extratos.
