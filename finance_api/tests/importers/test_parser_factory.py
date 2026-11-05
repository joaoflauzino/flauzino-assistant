from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.importers.protocols import StatementParser
from finance_api.importers.registry import (
    CheckingAccountTargetResolver,
    CreditCardTargetResolver,
    StatementParserFactory,
    build_default_parser_factory,
    build_default_target_resolvers,
    detect_parser,
)
from finance_api.importers.schemas import ParserKey, StatementType
from finance_api.models.accounts import Account
from finance_api.models.credit_cards import CreditCard
from finance_api.repositories.protocols import (
    AccountRepositoryProtocol,
    CreditCardRepositoryProtocol,
)

SAMPLE_CHECKING_CSV = b"""\xef\xbb\xbfEXTRATO DE CONTA CORRENTE C6 BANK\r
\r
Ag\xc3\xaancia: 1 / Conta: 145118436\r
Extrato gerado em 03/10/2026 - as 13:34:58\r
\r
Extrato de 04/08/2026 a 03/10/2026\r
\r
\r
Data Lan\xc3\xa7amento,Data Cont\xc3\xa1bil,T\xc3\xadtulo,Descri\xc3\xa7\xc3\xa3o,Entrada(R$),Sa\xc3\xadda(R$),Saldo do Dia(R$)\r
05/08/2026,05/08/2026,PGTO FAT CARTAO C6,Fatura de cart\xc3\xa3o,0.00,1000.00,1000.00\r
"""

SAMPLE_CARD_CSV = b"""Data de Compra;Nome no Cart\xc3\xa3o;Final do Cart\xc3\xa3o;Categoria;Descri\xc3\xa7\xc3\xa3o;Parcela;Valor (em US$);Cota\xc3\xa7\xc3\xa3o (em R$);Valor (em R$)
26/05/2026;JOAO L F CASSIANO;1141;Empresa para empresa;DELL;4/12;0;0;235.25
"""


def test_parser_factory_registration_and_creation():
    factory = StatementParserFactory()
    mock_parser = MagicMock(spec=StatementParser)
    factory.register(ParserKey.C6_CHECKING_CSV, lambda: mock_parser)

    created = factory.create_by_key(ParserKey.C6_CHECKING_CSV)
    assert created is mock_parser


def test_parser_factory_unknown_key_raises_validation_error():
    factory = StatementParserFactory()
    with pytest.raises(ValidationError) as exc:
        factory.create_by_key(ParserKey.C6_CHECKING_CSV)
    assert "Parser 'c6_checking_csv' não suportado" in str(exc.value)


def test_parser_factory_detect_and_create():
    factory = build_default_parser_factory()

    checking_parser = factory.detect_and_create(SAMPLE_CHECKING_CSV, "extrato.csv")
    assert checking_parser.name == "c6_checking_csv"
    assert checking_parser.statement_type == StatementType.ACCOUNT

    card_parser = factory.detect_and_create(SAMPLE_CARD_CSV, "fatura.csv")
    assert card_parser.name == "c6_credit_card_csv"
    assert card_parser.statement_type == StatementType.CREDIT_CARD


def test_parser_factory_detect_unrecognized_file_raises_validation_error():
    factory = build_default_parser_factory()
    with pytest.raises(ValidationError) as exc:
        factory.detect_and_create(b"random,invalid,data", "random.txt")
    assert "não reconhecido" in str(exc.value)


def test_detect_parser_backward_compatibility():
    parser = detect_parser(SAMPLE_CHECKING_CSV, "extrato.csv")
    assert parser.name == "c6_checking_csv"


@pytest.mark.asyncio
async def test_checking_account_target_resolver_success():
    account_id = uuid4()
    mock_account = Account(id=account_id, key="c6_checking", name="Conta C6")

    acc_repo = MagicMock(spec=AccountRepositoryProtocol)
    acc_repo.get_by_id = AsyncMock(return_value=mock_account)
    cc_repo = MagicMock(spec=CreditCardRepositoryProtocol)

    resolver = CheckingAccountTargetResolver(account_repo=acc_repo, credit_card_repo=cc_repo)
    target = await resolver.resolve(account_id=account_id, credit_card_id=None)

    assert target.account_id == account_id
    assert target.credit_card_id is None
    assert target.target_key == "c6_checking"
    assert target.target_name == "Conta C6"


@pytest.mark.asyncio
async def test_checking_account_target_resolver_infers_account_from_card():
    account_id = uuid4()
    card_id = uuid4()
    mock_card = CreditCard(
        id=card_id,
        key="c6_card",
        name="Cartão C6",
        account_id=account_id,
        closing_day=1,
        due_day=10,
    )
    mock_account = Account(id=account_id, key="c6_checking", name="Conta C6")

    acc_repo = MagicMock(spec=AccountRepositoryProtocol)
    acc_repo.get_by_id = AsyncMock(return_value=mock_account)
    cc_repo = MagicMock(spec=CreditCardRepositoryProtocol)
    cc_repo.get_by_id = AsyncMock(return_value=mock_card)

    resolver = CheckingAccountTargetResolver(account_repo=acc_repo, credit_card_repo=cc_repo)
    target = await resolver.resolve(account_id=None, credit_card_id=card_id)

    assert target.account_id == account_id
    assert target.credit_card_id is None
    assert target.target_key == "c6_checking"


@pytest.mark.asyncio
async def test_checking_account_target_resolver_missing_account_raises():
    acc_repo = MagicMock(spec=AccountRepositoryProtocol)
    cc_repo = MagicMock(spec=CreditCardRepositoryProtocol)
    resolver = CheckingAccountTargetResolver(account_repo=acc_repo, credit_card_repo=cc_repo)

    with pytest.raises(ValidationError) as exc:
        await resolver.resolve(account_id=None, credit_card_id=None)
    assert "Informe a conta bancária" in str(exc.value)


@pytest.mark.asyncio
async def test_checking_account_target_resolver_not_found_raises():
    acc_id = uuid4()
    acc_repo = MagicMock(spec=AccountRepositoryProtocol)
    acc_repo.get_by_id = AsyncMock(return_value=None)
    cc_repo = MagicMock(spec=CreditCardRepositoryProtocol)

    resolver = CheckingAccountTargetResolver(account_repo=acc_repo, credit_card_repo=cc_repo)
    with pytest.raises(EntityNotFoundError) as exc:
        await resolver.resolve(account_id=acc_id, credit_card_id=None)
    assert f"Conta com ID {acc_id} não encontrada" in str(exc.value)


@pytest.mark.asyncio
async def test_credit_card_target_resolver_success():
    account_id = uuid4()
    card_id = uuid4()
    mock_card = CreditCard(
        id=card_id,
        key="c6_carbon",
        name="C6 Carbon",
        account_id=account_id,
        closing_day=1,
        due_day=10,
    )

    acc_repo = MagicMock(spec=AccountRepositoryProtocol)
    cc_repo = MagicMock(spec=CreditCardRepositoryProtocol)
    cc_repo.get_by_id = AsyncMock(return_value=mock_card)

    resolver = CreditCardTargetResolver(account_repo=acc_repo, credit_card_repo=cc_repo)
    target = await resolver.resolve(account_id=account_id, credit_card_id=card_id)

    assert target.account_id == account_id
    assert target.credit_card_id == card_id
    assert target.target_key == "c6_carbon"
    assert target.target_name == "C6 Carbon"


@pytest.mark.asyncio
async def test_credit_card_target_resolver_auto_resolves_card_from_account():
    account_id = uuid4()
    card_id = uuid4()
    mock_card = CreditCard(
        id=card_id,
        key="c6_carbon",
        name="C6 Carbon",
        account_id=account_id,
        closing_day=1,
        due_day=10,
    )

    acc_repo = MagicMock(spec=AccountRepositoryProtocol)
    cc_repo = MagicMock(spec=CreditCardRepositoryProtocol)
    cc_repo.list = AsyncMock(return_value=([mock_card], 1))
    cc_repo.get_by_id = AsyncMock(return_value=mock_card)

    resolver = CreditCardTargetResolver(account_repo=acc_repo, credit_card_repo=cc_repo)
    target = await resolver.resolve(account_id=account_id, credit_card_id=None)

    assert target.credit_card_id == card_id
    assert target.account_id == account_id


@pytest.mark.asyncio
async def test_credit_card_target_resolver_resolves_bank_hint():
    account_id = uuid4()
    card_id = uuid4()
    mock_card = CreditCard(
        id=card_id,
        key="c6_mastercard",
        name="C6 Black",
        account_id=account_id,
        closing_day=1,
        due_day=10,
    )

    acc_repo = MagicMock(spec=AccountRepositoryProtocol)
    cc_repo = MagicMock(spec=CreditCardRepositoryProtocol)
    cc_repo.list = AsyncMock(return_value=([mock_card], 1))
    cc_repo.get_by_id = AsyncMock(return_value=mock_card)

    resolver = CreditCardTargetResolver(account_repo=acc_repo, credit_card_repo=cc_repo)
    target = await resolver.resolve(account_id=None, credit_card_id=None, bank_hint="c6")

    assert target.credit_card_id == card_id
    assert target.account_id == account_id
    assert target.target_key == "c6_mastercard"


@pytest.mark.asyncio
async def test_credit_card_target_resolver_missing_card_raises():
    acc_repo = MagicMock(spec=AccountRepositoryProtocol)
    cc_repo = MagicMock(spec=CreditCardRepositoryProtocol)
    cc_repo.list = AsyncMock(return_value=([], 0))

    resolver = CreditCardTargetResolver(account_repo=acc_repo, credit_card_repo=cc_repo)
    with pytest.raises(ValidationError) as exc:
        await resolver.resolve(account_id=None, credit_card_id=None, bank_hint="inexistente")
    assert "Informe o cartão de crédito para a importação da fatura" in str(exc.value)


@pytest.mark.asyncio
async def test_credit_card_target_resolver_not_found_raises():
    card_id = uuid4()
    acc_repo = MagicMock(spec=AccountRepositoryProtocol)
    cc_repo = MagicMock(spec=CreditCardRepositoryProtocol)
    cc_repo.get_by_id = AsyncMock(return_value=None)

    resolver = CreditCardTargetResolver(account_repo=acc_repo, credit_card_repo=cc_repo)
    with pytest.raises(EntityNotFoundError) as exc:
        await resolver.resolve(account_id=None, credit_card_id=card_id)
    assert f"Cartão com ID {card_id} não encontrado" in str(exc.value)


def test_build_default_target_resolvers():
    acc_repo = MagicMock(spec=AccountRepositoryProtocol)
    cc_repo = MagicMock(spec=CreditCardRepositoryProtocol)
    resolvers = build_default_target_resolvers(acc_repo, cc_repo)

    assert StatementType.ACCOUNT in resolvers
    assert StatementType.CREDIT_CARD in resolvers
    assert isinstance(resolvers[StatementType.ACCOUNT], CheckingAccountTargetResolver)
    assert isinstance(resolvers[StatementType.CREDIT_CARD], CreditCardTargetResolver)
