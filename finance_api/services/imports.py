from datetime import timedelta
from decimal import Decimal
import hashlib
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from finance_api.core.decorators import handle_service_errors
from finance_api.core.exceptions import EntityConflictError, EntityNotFoundError, ValidationError
from finance_api.core.logger import get_logger
from finance_api.importers.base import ParsedTransaction, StatementType
from finance_api.importers.registry import detect_parser
from finance_api.models.accounts import Account
from finance_api.models.import_batches import ImportBatch
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.accounts import AccountRepository
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.category_rules import CategoryRuleRepository
from finance_api.repositories.credit_cards import CreditCardRepository
from finance_api.repositories.income_categories import IncomeCategoryRepository
from finance_api.repositories.imports import ImportBatchRepository
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.schemas.imports import (
    BulkActionError,
    BulkActionRequest,
    BulkActionResult,
    CommitFailure,
    CommitRequest,
    CommitResult,
    ImportBatchResponse,
    PossibleDuplicateInfo,
    ReclassifyResult,
    StagedTransactionResponse,
    StagedTransactionUpdate,
    SummaryResponse,
)
from finance_api.schemas.incomes import IncomeCreate
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.schemas.spents import SpentCreate
from finance_api.services.ai_classifier import AIClassifierClient
from finance_api.services.classification import ClassificationResult, ClassificationService
from finance_api.services.incomes import IncomeService
from finance_api.services.spents import SpentService

logger = get_logger(__name__)
SP_TZ = ZoneInfo("America/Sao_Paulo")


class ImportService:
    def __init__(
        self,
        batch_repo: ImportBatchRepository,
        tx_repo: StagedTransactionRepository,
        rule_repo: CategoryRuleRepository,
        classification_service: ClassificationService,
        account_repo: AccountRepository,
        credit_card_repo: CreditCardRepository,
        spent_service: SpentService,
        income_service: IncomeService,
        category_repo: CategoryRepository,
        income_category_repo: IncomeCategoryRepository,
        ai_client: AIClassifierClient | None = None,
    ):
        self.batch_repo = batch_repo
        self.tx_repo = tx_repo
        self.rule_repo = rule_repo
        self.classification_service = classification_service
        self.account_repo = account_repo
        self.credit_card_repo = credit_card_repo
        self.spent_service = spent_service
        self.income_service = income_service
        self.category_repo = category_repo
        self.income_category_repo = income_category_repo
        self.ai_client = ai_client or AIClassifierClient()

    def _calc_sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _calc_fingerprint(
        self,
        target_key: str,
        tx: ParsedTransaction,
    ) -> str:
        date_str = tx.occurred_at.date().isoformat()
        amt_str = f"{tx.amount:.2f}"
        installment_str = (
            f"{tx.current_installment}/{tx.total_installments}" if tx.current_installment else "1"
        )
        raw = f"{target_key}|{date_str}|{amt_str}|{tx.direction}|{tx.raw_title.upper().strip()}|{installment_str}|{tx.occurrence_index}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def _resolve_target_name_and_key(
        self, account_id: UUID | None, credit_card_id: UUID | None
    ) -> tuple[str, str | None]:
        """Retorna (target_key, target_name) para fingerprint e exibição."""
        if credit_card_id:
            card = await self.credit_card_repo.get_by_id(credit_card_id)
            if not card:
                raise EntityNotFoundError(f"Cartão com ID {credit_card_id} não encontrado")
            return card.key, card.name
        if account_id:
            acc = await self.account_repo.get_by_id(account_id)
            if not acc:
                raise EntityNotFoundError(f"Conta com ID {account_id} não encontrada")
            return acc.key, acc.name
        return "unassigned", None

    @handle_service_errors
    async def create_batch_from_upload(
        self,
        file_bytes: bytes,
        filename: str,
        account_id: UUID | None = None,
        credit_card_id: UUID | None = None,
    ) -> ImportBatchResponse:
        parser = detect_parser(file_bytes, filename)
        is_credit_card = getattr(parser, "statement_type", None) == StatementType.CREDIT_CARD

        # Auto-resolução inteligente de Cartão e Conta
        if is_credit_card:
            if not credit_card_id and account_id:
                cards, _ = await self.credit_card_repo.list(account_id=account_id)
                if cards:
                    credit_card_id = cards[0].id
            if credit_card_id and not account_id:
                card = await self.credit_card_repo.get_by_id(credit_card_id)
                if card:
                    account_id = card.account_id
            if not credit_card_id:
                # Tenta buscar cartão com o mesmo banco do parser (ex: c6)
                all_cards, _ = await self.credit_card_repo.list(page=1, size=100)
                matched = [c for c in all_cards if "c6" in c.key.lower()]
                if matched:
                    credit_card_id = matched[0].id
                    account_id = matched[0].account_id
        else:
            if credit_card_id and not account_id:
                card = await self.credit_card_repo.get_by_id(credit_card_id)
                if card:
                    account_id = card.account_id
                credit_card_id = None

        if not account_id and not credit_card_id:
            raise ValidationError("Informe a conta bancária ou cartão para a importação.")

        target_key, target_name = await self._resolve_target_name_and_key(
            account_id, credit_card_id
        )

        file_sha256 = self._calc_sha256(file_bytes)
        existing_batch = await self.batch_repo.get_by_sha256(file_sha256)
        if existing_batch:
            raise EntityConflictError(
                f"Este arquivo ('{filename}') já foi importado anteriormente em {existing_batch.created_at.strftime('%d/%m/%Y %H:%M')}."
            )

        parsed = parser.parse(file_bytes, filename)

        # Calcula fingerprints de todas as transações
        fp_map: list[tuple[ParsedTransaction, str]] = []
        for tx in parsed.transactions:
            fp = self._calc_fingerprint(target_key, tx)
            fp_map.append((tx, fp))

        all_fps = [fp for _, fp in fp_map]
        existing_fps = await self.tx_repo.get_existing_fingerprints(all_fps)

        new_pairs = [(tx, fp) for tx, fp in fp_map if fp not in existing_fps]
        duplicate_rows_count = len(parsed.transactions) - len(new_pairs)

        # Cria lote no banco
        batch = ImportBatch(
            account_id=account_id,
            credit_card_id=credit_card_id,
            parser=parser.name,
            filename=filename,
            file_sha256=file_sha256,
            period_start=parsed.metadata.period_start,
            period_end=parsed.metadata.period_end,
            total_rows=len(parsed.transactions),
            new_rows=len(new_pairs),
            duplicate_rows=duplicate_rows_count,
            possible_duplicates=0,
            ai_used=False,
        )
        batch = await self.batch_repo.create(batch)

        if not new_pairs:
            # Todas eram duplicadas
            counts = await self.batch_repo.get_counts_by_status(batch.id)
            res = ImportBatchResponse.model_validate(batch)
            res.account_name = target_name
            if credit_card_id:
                res.credit_card_id = credit_card_id
                res.credit_card_name = target_name
            res.counts = counts
            return res

        # Classificação Camadas 1 & 2 e Detecção de Duplicatas Manuais
        staged_list: list[StagedTransaction] = []
        possible_duplicates_count = 0

        for tx, fp in new_pairs:
            clf: ClassificationResult = await self.classification_service.classify_transaction(
                tx.raw_title,
                tx.raw_description,
                tx.direction,
                tx.amount,
                bank_category=getattr(tx, "bank_category", None),
                is_credit_card=is_credit_card,
            )

            # Detecção de duplicata com lançamento manual
            dup_spent_id = None
            dup_income_id = None
            if clf.kind == "EXPENSE":
                match_sp = await self.tx_repo.find_possible_duplicate_spent(
                    account_id=account_id,
                    amount=tx.amount,
                    tx_date=tx.occurred_at.date(),
                    credit_card_id=credit_card_id,
                )
                if match_sp:
                    dup_spent_id = match_sp.id
                    possible_duplicates_count += 1
            elif clf.kind == "INCOME":
                match_inc = await self.tx_repo.find_possible_duplicate_income(
                    account_id=account_id,
                    amount=tx.amount,
                    tx_date=tx.occurred_at.date(),
                )
                if match_inc:
                    dup_income_id = match_inc.id
                    possible_duplicates_count += 1

            comp_date = None
            if clf.kind == "INCOME":
                tx_dt = tx.occurred_at.date()
                norm_raw = f"{tx.raw_title} {tx.raw_description or ''}".upper()
                is_salary_like = any(
                    k in norm_raw
                    for k in [
                        "SALARIO",
                        "SALÁRIO",
                        "FOLHA",
                        "PRO-LABORE",
                        "REMUNERACAO",
                        "VENCIMENTO",
                        "PPR",
                        "PLR",
                    ]
                )
                if is_salary_like and tx_dt.day <= 7:
                    first_of_month = tx_dt.replace(day=1)
                    comp_date = first_of_month - timedelta(days=1)
                else:
                    comp_date = tx_dt

            staged = StagedTransaction(
                batch_id=batch.id,
                account_id=account_id,
                credit_card_id=credit_card_id,
                occurred_at=tx.occurred_at,
                posted_at=tx.posted_at,
                raw_title=tx.raw_title,
                raw_description=tx.raw_description,
                raw_row=tx.raw_row,
                merchant=clf.merchant,
                amount=tx.amount,
                direction=tx.direction,
                kind=clf.kind,
                payment_type=clf.payment_type,
                suggested_category=clf.suggested_category,
                suggestion_source=clf.suggestion_source,
                confidence=clf.confidence,
                category=clf.suggested_category,  # Pré-preenchido com sugestão se houver
                description=clf.description[:50],
                location=clf.location,
                status="PENDING",
                fingerprint=fp,
                current_installment=getattr(tx, "current_installment", None),
                total_installments=getattr(tx, "total_installments", None),
                card_last_digits=getattr(tx, "card_last_digits", None),
                competence_date=comp_date,
                possible_duplicate_of_spent_id=dup_spent_id,
                possible_duplicate_of_income_id=dup_income_id,
            )
            staged_list.append(staged)

        # ---------------------------------------------------------
        # Camada 3: LLM em lote via agent_api para o que sobrou sem categoria
        # ---------------------------------------------------------
        ai_candidates = [
            st
            for st in staged_list
            if st.kind in ("EXPENSE", "INCOME") and not st.suggested_category
        ]

        ai_used = False
        if ai_candidates:
            try:
                exp_cats, _ = await self.category_repo.list(page=1, size=200)
                inc_cats, _ = await self.income_category_repo.list(page=1, size=200)

                exp_list = [{"key": c.key, "display_name": c.display_name} for c in exp_cats]
                inc_list = [{"key": c.key, "display_name": c.display_name} for c in inc_cats]

                payload_items = [
                    {
                        "id": str(idx),
                        "merchant": st.merchant,
                        "raw_title": st.raw_title,
                        "raw_description": st.raw_description,
                        "direction": st.direction,
                        "amount": float(st.amount),
                    }
                    for idx, st in enumerate(ai_candidates)
                ]

                suggestions_map, ai_success = await self.ai_client.classify_batch(
                    transactions=payload_items,
                    expense_categories=exp_list,
                    income_categories=inc_list,
                )
                if ai_success:
                    ai_used = True
                    for idx, cand in enumerate(ai_candidates):
                        sug = suggestions_map.get(str(idx))
                        if sug:
                            sug_cat = sug.get("category")
                            conf = sug.get("confidence")
                            cand.suggested_category = sug_cat
                            cand.category = sug_cat
                            cand.suggestion_source = "LLM"
                            cand.confidence = Decimal(str(conf)) if conf else Decimal("0.750")
            except Exception as e:
                logger.warning(f"Failed to run AI classification on import batch: {e}")

        # Salva transações
        await self.tx_repo.create_many(staged_list)

        # Atualiza batch com ai_used e possible_duplicates
        batch.possible_duplicates = possible_duplicates_count
        batch.ai_used = ai_used
        self.batch_repo.db.add(batch)
        await self.batch_repo.db.commit()
        await self.batch_repo.db.refresh(batch)

        counts = await self.batch_repo.get_counts_by_status(batch.id)
        res = ImportBatchResponse.model_validate(batch)
        res.account_name = target_name
        if credit_card_id:
            res.credit_card_id = credit_card_id
            res.credit_card_name = target_name
        res.counts = counts
        return res

    @handle_service_errors
    async def list_batches(self) -> list[ImportBatchResponse]:
        batches = await self.batch_repo.list_all()
        results = []
        for b in batches:
            res = ImportBatchResponse.model_validate(b)
            if b.account_id:
                acc = await self.account_repo.get_by_id(b.account_id)
                res.account_name = acc.name if acc else None
            if b.credit_card_id:
                card = await self.credit_card_repo.get_by_id(b.credit_card_id)
                if card:
                    res.credit_card_id = card.id
                    res.credit_card_name = card.name
                    if not res.account_name:
                        res.account_name = card.name
            res.counts = await self.batch_repo.get_counts_by_status(b.id)
            results.append(res)
        return results

    async def _to_tx_response(self, tx: StagedTransaction) -> StagedTransactionResponse:
        res = StagedTransactionResponse.model_validate(tx)
        res.amount = float(tx.amount)
        res.confidence = float(tx.confidence) if tx.confidence is not None else None
        res.current_installment = tx.current_installment
        res.total_installments = tx.total_installments
        res.card_last_digits = tx.card_last_digits

        # Resolve possible duplicate info se houver
        if tx.possible_duplicate_of_spent_id:
            sp = await self.spent_service.repo.get_by_id(tx.possible_duplicate_of_spent_id)
            if sp:
                res.possible_duplicate = PossibleDuplicateInfo(
                    type="spent",
                    id=sp.id,
                    label=sp.item_bought,
                    amount=sp.amount,
                    date=sp.created_at.date(),
                )
        elif tx.possible_duplicate_of_income_id:
            inc = await self.income_service.repo.get_by_id(tx.possible_duplicate_of_income_id)
            if inc:
                res.possible_duplicate = PossibleDuplicateInfo(
                    type="income",
                    id=inc.id,
                    label=inc.description,
                    amount=inc.amount,
                    date=inc.received_at.date(),
                )
        return res

    @handle_service_errors
    async def list_transactions(
        self,
        batch_id: UUID | None = None,
        status: str | None = None,
        kind: str | None = None,
        only_duplicates: bool = False,
        only_unclassified: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedResponse[StagedTransactionResponse]:
        items, total = await self.tx_repo.list_by_filter(
            batch_id=batch_id,
            status=status,
            kind=kind,
            only_duplicates=only_duplicates,
            only_unclassified=only_unclassified,
            page=page,
            size=size,
        )
        tx_responses = [await self._to_tx_response(tx) for tx in items]
        return PaginatedResponse.create(tx_responses, total, page, size)

    @handle_service_errors
    async def update_transaction(
        self, tx_id: UUID, data: StagedTransactionUpdate
    ) -> StagedTransactionResponse:
        tx = await self.tx_repo.get_by_id(tx_id)
        if not tx:
            raise EntityNotFoundError(f"Transação {tx_id} não encontrada")

        if tx.status == "COMMITTED":
            raise ValidationError("Transação já foi efetivada e não pode ser alterada.")

        if data.kind is not None:
            if data.kind not in ("EXPENSE", "INCOME", "TRANSFER", "INVOICE_PAYMENT", "REFUND"):
                raise ValidationError(f"Tipo '{data.kind}' inválido.")
            tx.kind = data.kind
            # Se mudou para TRANSFER ou INVOICE_PAYMENT, limpa categoria
            if tx.kind in ("TRANSFER", "INVOICE_PAYMENT", "REFUND"):
                tx.category = None

        if data.description is not None:
            tx.description = data.description.strip()[:50]

        if data.location is not None:
            tx.location = data.location.strip() or None

        if data.competence_date is not None:
            tx.competence_date = data.competence_date

        if data.category is not None:
            clean_cat = data.category.strip().lower() if data.category else None
            if clean_cat:
                if tx.kind == "EXPENSE":
                    c = await self.category_repo.get_by_key(clean_cat)
                    if not c:
                        raise ValidationError(f"Categoria de despesa '{clean_cat}' não existe.")
                elif tx.kind == "INCOME":
                    ic = await self.income_category_repo.get_by_key(clean_cat)
                    if not ic:
                        raise ValidationError(f"Categoria de receita '{clean_cat}' não existe.")
            tx.category = clean_cat

        if data.status is not None:
            if data.status not in ("PENDING", "APPROVED", "IGNORED"):
                raise ValidationError(f"Status '{data.status}' inválido para transição direta.")
            if data.status == "APPROVED":
                if tx.kind in ("EXPENSE", "INCOME") and not tx.category:
                    raise ValidationError(
                        f"Selecione uma categoria para aprovar uma transação do tipo {tx.kind}."
                    )
            tx.status = data.status

        # Aprendizado de regra se solicitado
        if data.remember and tx.category and tx.merchant and tx.kind in ("EXPENSE", "INCOME"):
            await self.rule_repo.upsert_rule(
                pattern=tx.merchant,
                direction=tx.direction,
                kind=tx.kind,
                category=tx.category,
                source="LEARNED",
            )

        saved = await self.tx_repo.save(tx)
        return await self._to_tx_response(saved)

    @handle_service_errors
    async def bulk_action(self, req: BulkActionRequest) -> BulkActionResult:
        updated = 0
        skipped = 0
        errors: list[BulkActionError] = []

        for tx_id in req.ids:
            tx = await self.tx_repo.get_by_id(tx_id)
            if not tx:
                errors.append(BulkActionError(id=tx_id, error="Transação não encontrada"))
                continue
            if tx.status == "COMMITTED":
                skipped += 1
                continue

            try:
                if req.action == "approve":
                    # Pula se for duplicata suspeita (o usuário deve revisar individualmente)
                    if tx.possible_duplicate_of_spent_id or tx.possible_duplicate_of_income_id:
                        skipped += 1
                        continue
                    if tx.kind in ("EXPENSE", "INCOME") and not tx.category:
                        skipped += 1
                        continue
                    tx.status = "APPROVED"
                    if req.remember and tx.category and tx.merchant:
                        await self.rule_repo.upsert_rule(
                            pattern=tx.merchant,
                            direction=tx.direction,
                            kind=tx.kind,
                            category=tx.category,
                            source="LEARNED",
                        )
                elif req.action == "ignore":
                    tx.status = "IGNORED"
                elif req.action == "reopen":
                    tx.status = "PENDING"
                elif req.action == "set_category":
                    if not req.category:
                        skipped += 1
                        continue
                    clean_cat = req.category.strip().lower()
                    if tx.kind == "EXPENSE":
                        c = await self.category_repo.get_by_key(clean_cat)
                        if not c:
                            errors.append(
                                BulkActionError(
                                    id=tx_id, error=f"Categoria '{clean_cat}' não existe"
                                )
                            )
                            continue
                    elif tx.kind == "INCOME":
                        ic = await self.income_category_repo.get_by_key(clean_cat)
                        if not ic:
                            errors.append(
                                BulkActionError(
                                    id=tx_id, error=f"Categoria '{clean_cat}' não existe"
                                )
                            )
                            continue
                    tx.category = clean_cat
                    if req.remember and tx.merchant:
                        await self.rule_repo.upsert_rule(
                            pattern=tx.merchant,
                            direction=tx.direction,
                            kind=tx.kind,
                            category=clean_cat,
                            source="LEARNED",
                        )
                else:
                    errors.append(
                        BulkActionError(id=tx_id, error=f"Ação desconhecida: {req.action}")
                    )
                    continue

                await self.tx_repo.save(tx)
                updated += 1
            except Exception as e:
                errors.append(BulkActionError(id=tx_id, error=str(e)))

        return BulkActionResult(updated=updated, skipped=skipped, errors=errors)

    @handle_service_errors
    async def link_transaction(self, tx_id: UUID) -> StagedTransactionResponse:
        tx = await self.tx_repo.get_by_id(tx_id)
        if not tx:
            raise EntityNotFoundError(f"Transação {tx_id} não encontrada")

        if not tx.possible_duplicate_of_spent_id and not tx.possible_duplicate_of_income_id:
            raise ValidationError("Esta transação não possui duplicata identificada para vincular.")

        if tx.possible_duplicate_of_spent_id:
            tx.committed_spent_id = tx.possible_duplicate_of_spent_id
        if tx.possible_duplicate_of_income_id:
            tx.committed_income_id = tx.possible_duplicate_of_income_id

        tx.status = "LINKED"
        saved = await self.tx_repo.save(tx)
        return await self._to_tx_response(saved)

    @handle_service_errors
    async def commit_approved(self, req: CommitRequest) -> CommitResult:
        approved_items = await self.tx_repo.get_approved_for_commit(req.batch_id)
        committed_spents = 0
        committed_incomes = 0
        processed_without_record = 0
        failed: list[CommitFailure] = []

        # Cache de contas e cartões para resolver payment_method
        account_cache: dict[UUID, Account] = {}
        card_cache: dict[UUID, Any] = {}

        for tx in approved_items:
            try:
                acc = None
                if tx.account_id:
                    if tx.account_id not in account_cache:
                        a = await self.account_repo.get_by_id(tx.account_id)
                        if a:
                            account_cache[tx.account_id] = a
                    acc = account_cache.get(tx.account_id)

                card = None
                if tx.credit_card_id:
                    if tx.credit_card_id not in card_cache:
                        c = await self.credit_card_repo.get_by_id(tx.credit_card_id)
                        if c:
                            card_cache[tx.credit_card_id] = c
                    card = card_cache.get(tx.credit_card_id)

                if card:
                    pm_key = card.key
                    pt_val = "CREDIT"
                    acc_id = tx.account_id or card.account_id
                else:
                    pm_key = acc.key if acc else "outros"
                    pt_val = (
                        tx.payment_type
                        if tx.payment_type in ("PIX", "DEBIT", "CASH", "TRANSFER", "OTHER")
                        else "DEBIT"
                    )
                    acc_id = tx.account_id

                if tx.kind == "EXPENSE":
                    if not tx.category:
                        failed.append(CommitFailure(id=tx.id, error="Despesa sem categoria"))
                        continue

                    spent_data = SpentCreate(
                        category=tx.category,
                        amount=float(tx.amount),
                        item_bought=tx.description[:50],
                        payment_method=pm_key,
                        payment_type=pt_val,
                        account_id=acc_id,
                        credit_card_id=tx.credit_card_id,
                        location=tx.location,
                        created_at=tx.occurred_at,
                        is_installment=False,
                        current_installment=tx.current_installment,
                        total_installments=tx.total_installments,
                    )
                    created_spent = await self.spent_service.create(spent_data)
                    tx.committed_spent_id = created_spent.id
                    tx.status = "COMMITTED"
                    await self.tx_repo.save(tx)
                    committed_spents += 1

                elif tx.kind == "INCOME":
                    if not tx.category:
                        failed.append(CommitFailure(id=tx.id, error="Receita sem categoria"))
                        continue

                    income_data = IncomeCreate(
                        description=tx.description[:100],
                        amount=float(tx.amount),
                        category=tx.category,
                        payment_method=pm_key,
                        account_id=acc_id,
                        received_at=tx.occurred_at,
                        competence_date=tx.competence_date or tx.occurred_at.date(),
                    )
                    created_income = await self.income_service.create(income_data)
                    tx.committed_income_id = created_income.id
                    tx.status = "COMMITTED"
                    await self.tx_repo.save(tx)
                    committed_incomes += 1

                elif tx.kind in ("TRANSFER", "INVOICE_PAYMENT", "REFUND"):
                    # Não gera lançamento financeiro duplicado
                    tx.status = "COMMITTED"
                    await self.tx_repo.save(tx)
                    processed_without_record += 1

            except Exception as e:
                logger.error(f"Failed to commit tx {tx.id}: {e}", exc_info=True)
                failed.append(CommitFailure(id=tx.id, error=str(e)))

        return CommitResult(
            committed_spents=committed_spents,
            committed_incomes=committed_incomes,
            processed_without_record=processed_without_record,
            failed=failed,
        )

    @handle_service_errors
    async def reclassify_batch(self, batch_id: UUID | None = None) -> ReclassifyResult:
        candidates = await self.tx_repo.list_for_reclassification(batch_id)
        if not candidates:
            return ReclassifyResult(total_reclassified=0, applied_rules=0, applied_ai=0)

        applied_rules = 0
        ai_candidates = []

        for tx in candidates:
            # 1. Tenta por regra
            rule = await self.rule_repo.find_matching_rule(tx.merchant, tx.direction)
            if rule and rule.category:
                tx.category = rule.category
                tx.suggested_category = rule.category
                tx.suggestion_source = "RULE" if rule.source == "SEED" else "MEMORY"
                tx.confidence = Decimal("0.950") if rule.hits >= 2 else Decimal("0.850")
                await self.rule_repo.increment_hits(rule.id)
                await self.tx_repo.save(tx)
                applied_rules += 1
            else:
                ai_candidates.append(tx)

        applied_ai = 0
        if ai_candidates:
            try:
                exp_cats, _ = await self.category_repo.list(page=1, size=200)
                inc_cats, _ = await self.income_category_repo.list(page=1, size=200)

                exp_list = [{"key": c.key, "display_name": c.display_name} for c in exp_cats]
                inc_list = [{"key": c.key, "display_name": c.display_name} for c in inc_cats]

                payload_items = [
                    {
                        "id": str(tx.id),
                        "merchant": tx.merchant,
                        "raw_title": tx.raw_title,
                        "raw_description": tx.raw_description,
                        "direction": tx.direction,
                        "amount": float(tx.amount),
                    }
                    for tx in ai_candidates
                ]

                suggestions_map, ai_success = await self.ai_client.classify_batch(
                    transactions=payload_items,
                    expense_categories=exp_list,
                    income_categories=inc_list,
                )
                if ai_success:
                    for tx in ai_candidates:
                        sug = suggestions_map.get(str(tx.id))
                        if sug and sug.get("category"):
                            sug_cat = sug.get("category")
                            conf = sug.get("confidence")
                            tx.suggested_category = sug_cat
                            tx.category = sug_cat
                            tx.suggestion_source = "LLM"
                            tx.confidence = Decimal(str(conf)) if conf else Decimal("0.750")
                            await self.tx_repo.save(tx)
                            applied_ai += 1
            except Exception as e:
                logger.warning(f"Reclassification AI step failed: {e}")

        return ReclassifyResult(
            total_reclassified=applied_rules + applied_ai,
            applied_rules=applied_rules,
            applied_ai=applied_ai,
        )

    @handle_service_errors
    async def get_summary(self) -> SummaryResponse:
        _, pending_count = await self.tx_repo.list_by_filter(status="PENDING", size=1)
        _, approved_count = await self.tx_repo.list_by_filter(status="APPROVED", size=1)
        return SummaryResponse(pending=pending_count, approved=approved_count)
