"""Commit orchestration for approved staged transactions."""

from typing import Any
from uuid import UUID

from finance_api.core.logger import get_logger
from finance_api.models.accounts import Account
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.protocols import (
    AccountRepositoryProtocol,
    CreditCardRepositoryProtocol,
    StagedTransactionRepositoryProtocol,
)
from finance_api.schemas.enums import CommitOutcomeStatus
from finance_api.schemas.imports import (
    CommitContext,
    CommitFailure,
    CommitRequest,
    CommitResult,
)
from finance_api.services.imports.protocols import TransactionCommitStrategy

logger = get_logger(__name__)

VALID_ACCOUNT_PAYMENT_TYPES = ("PIX", "DEBIT", "CASH", "TRANSFER", "OTHER")
OUTCOME_COUNTERS: dict[str, str] = {
    CommitOutcomeStatus.COMMITTED_SPENT.value: "committed_spents",
    CommitOutcomeStatus.COMMITTED_INCOME.value: "committed_incomes",
    CommitOutcomeStatus.PROCESSED_WITHOUT_RECORD.value: "processed_without_record",
}


class CommitContextResolver:
    """Resolves the payment method and payment type for a staged transaction."""

    def __init__(
        self,
        account_repo: AccountRepositoryProtocol,
        credit_card_repo: CreditCardRepositoryProtocol,
    ) -> None:
        self._account_repo = account_repo
        self._credit_card_repo = credit_card_repo
        self._account_cache: dict[UUID, Account] = {}
        self._card_cache: dict[UUID, Any] = {}

    async def resolve(self, tx: StagedTransaction) -> CommitContext:
        card = await self._get_card(tx.credit_card_id)
        if card:
            return CommitContext(
                payment_method_key=card.key,
                payment_type_value="CREDIT",
                account_id=tx.account_id or card.account_id,
            )
        return await self._resolve_account_context(tx)

    async def _resolve_account_context(self, tx: StagedTransaction) -> CommitContext:
        account = await self._get_account(tx.account_id)
        payment_type = (
            tx.payment_type if tx.payment_type in VALID_ACCOUNT_PAYMENT_TYPES else "DEBIT"
        )
        return CommitContext(
            payment_method_key=account.key if account else "outros",
            payment_type_value=payment_type,
            account_id=tx.account_id,
        )

    async def _get_card(self, card_id: UUID | None) -> Any | None:
        if not card_id:
            return None
        if card_id not in self._card_cache:
            card = await self._credit_card_repo.get_by_id(card_id)
            if card:
                self._card_cache[card_id] = card
        return self._card_cache.get(card_id)

    async def _get_account(self, account_id: UUID | None) -> Account | None:
        if not account_id:
            return None
        if account_id not in self._account_cache:
            account = await self._account_repo.get_by_id(account_id)
            if account:
                self._account_cache[account_id] = account
        return self._account_cache.get(account_id)


class ImportCommitService:
    """Commits approved staged transactions using the configured strategies."""

    def __init__(
        self,
        tx_repo: StagedTransactionRepositoryProtocol,
        context_resolver: CommitContextResolver,
        commit_strategies: dict[str, TransactionCommitStrategy],
    ) -> None:
        self._tx_repo = tx_repo
        self._context_resolver = context_resolver
        self._commit_strategies = commit_strategies

    async def commit(self, req: CommitRequest) -> CommitResult:
        approved_items = await self._tx_repo.get_approved_for_commit(req.batch_id)
        counters = {name: 0 for name in OUTCOME_COUNTERS.values()}
        failed: list[CommitFailure] = []

        for tx in approved_items:
            failure = await self._commit_one(tx, counters)
            if failure:
                failed.append(failure)

        return CommitResult(
            committed_spents=counters["committed_spents"],
            committed_incomes=counters["committed_incomes"],
            processed_without_record=counters["processed_without_record"],
            failed=failed,
        )

    async def _commit_one(
        self, tx: StagedTransaction, counters: dict[str, int]
    ) -> CommitFailure | None:
        try:
            return await self._apply_strategy(tx, counters)
        except Exception as error:
            logger.error(f"Failed to commit tx {tx.id}: {error}", exc_info=True)
            return CommitFailure(id=tx.id, error=str(error))

    async def _apply_strategy(
        self,
        tx: StagedTransaction,
        counters: dict[str, int],
    ) -> CommitFailure | None:
        strategy = self._commit_strategies.get(str(tx.kind))
        if strategy is None:
            return None

        context = await self._context_resolver.resolve(tx)
        outcome = await strategy.commit(tx, context)
        if outcome.status == CommitOutcomeStatus.FAILED:
            return CommitFailure(
                id=tx.id,
                error=outcome.error_message or "Falha ao efetivar transação",
            )

        await self._tx_repo.save(tx)
        counter_name = OUTCOME_COUNTERS.get(outcome.status)
        if counter_name:
            counters[counter_name] += 1
        return None
