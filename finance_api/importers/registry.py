from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.importers.c6_checking_csv import C6CheckingCsvParser
from finance_api.importers.c6_credit_card_csv import C6CreditCardInvoiceCsvParser
from finance_api.importers.protocols import ImportTargetResolver, StatementParser
from finance_api.importers.schemas import (
    ParserKey,
    ResolvedImportTarget,
    StatementType,
)
from finance_api.repositories.accounts import AccountRepositoryProtocol
from finance_api.repositories.credit_cards import CreditCardRepositoryProtocol


# ---------------------------------------------------------------------------
# 1. Chain of Responsibility: Credit Card Resolution Steps
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CardResolutionContext:
    account_id: UUID | None
    credit_card_id: UUID | None
    bank_hint: str | None
    account_repo: AccountRepositoryProtocol
    credit_card_repo: CreditCardRepositoryProtocol


class CardResolutionStep(Protocol):
    async def resolve_card_id(self, ctx: CardResolutionContext) -> UUID | None: ...


class DirectCardIdStep:
    """Prioritizes an explicitly provided credit_card_id."""

    async def resolve_card_id(self, ctx: CardResolutionContext) -> UUID | None:
        return ctx.credit_card_id


class AccountCardFallbackStep:
    """Resolves the first card associated with the provided account_id."""

    async def resolve_card_id(self, ctx: CardResolutionContext) -> UUID | None:
        if not ctx.account_id:
            return None
        cards, _ = await ctx.credit_card_repo.list(account_id=ctx.account_id)
        return cards[0].id if cards else None


class BankHintCardStep:
    """Resolves card matching a bank hint (e.g. 'c6')."""

    async def resolve_card_id(self, ctx: CardResolutionContext) -> UUID | None:
        if not ctx.bank_hint:
            return None
        all_cards, _ = await ctx.credit_card_repo.list(page=1, size=100)
        matched = [c for c in all_cards if ctx.bank_hint.lower() in c.key.lower()]
        return matched[0].id if matched else None


# ---------------------------------------------------------------------------
# 2. Concrete Target Resolvers
# ---------------------------------------------------------------------------
class CreditCardTargetResolver:
    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        credit_card_repo: CreditCardRepositoryProtocol,
        steps: Sequence[CardResolutionStep] | None = None,
    ) -> None:
        self._account_repo = account_repo
        self._credit_card_repo = credit_card_repo
        self._steps = steps or (
            DirectCardIdStep(),
            AccountCardFallbackStep(),
            BankHintCardStep(),
        )

    async def resolve(
        self,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        bank_hint: str | None = None,
    ) -> ResolvedImportTarget:
        ctx = CardResolutionContext(
            account_id=account_id,
            credit_card_id=credit_card_id,
            bank_hint=bank_hint,
            account_repo=self._account_repo,
            credit_card_repo=self._credit_card_repo,
        )

        resolved_card_id: UUID | None = None
        for step in self._steps:
            resolved_card_id = await step.resolve_card_id(ctx)
            if resolved_card_id is not None:
                break

        if not resolved_card_id:
            raise ValidationError("Informe o cartão de crédito para a importação da fatura.")

        card = await self._credit_card_repo.get_by_id(resolved_card_id)
        if not card:
            raise EntityNotFoundError(f"Cartão com ID {resolved_card_id} não encontrado")

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
        if not account_id and credit_card_id:
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


def build_default_target_resolvers(
    account_repo: AccountRepositoryProtocol,
    credit_card_repo: CreditCardRepositoryProtocol,
) -> dict[StatementType, ImportTargetResolver]:
    return {
        StatementType.ACCOUNT: CheckingAccountTargetResolver(account_repo, credit_card_repo),
        StatementType.CREDIT_CARD: CreditCardTargetResolver(account_repo, credit_card_repo),
    }


def detect_parser(content: bytes, filename: str) -> StatementParser:
    return build_default_parser_factory().detect_and_create(content, filename)
