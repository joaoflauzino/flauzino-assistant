
import pytest
import asyncio
from agent_api.core.decorators import handle_finance_errors, handle_chat_service_errors
from agent_api.core.exceptions import FinanceServerError, DatabaseError

@pytest.mark.asyncio
async def test_finance_catch_all():
    @handle_finance_errors
    async def buggy_service():
        raise ValueError("Unexpected boom")

    with pytest.raises(FinanceServerError) as exc:
        await buggy_service()
    assert "Unexpected finance error" in str(exc.value)
    assert "Unexpected boom" in str(exc.value)

@pytest.mark.asyncio
async def test_chat_catch_all():
    @handle_chat_service_errors
    async def buggy_service():
        raise KeyError("Missing key")

    with pytest.raises(DatabaseError) as exc:
        await buggy_service()
    assert "Unexpected error in chat service" in str(exc.value)
    assert "Missing key" in str(exc.value)
