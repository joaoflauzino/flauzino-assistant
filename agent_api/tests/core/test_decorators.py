import pytest
from agent_api.core.decorators import handle_finance_errors, handle_service_errors
from agent_api.core.exceptions import ServiceError


@pytest.mark.asyncio
async def test_finance_catch_all():
    @handle_finance_errors
    async def buggy_service():
        raise ValueError("Unexpected boom")

    with pytest.raises(ServiceError) as exc:
        await buggy_service()
    assert "Unexpected finance error" in str(exc.value)
    assert "Unexpected boom" in str(exc.value)


@pytest.mark.asyncio
async def test_service_catch_all():
    @handle_service_errors
    async def buggy_service():
        raise KeyError("Missing key")

    with pytest.raises(ServiceError) as exc:
        await buggy_service()
    assert "Unexpected error" in str(exc.value)
    assert "Missing key" in str(exc.value)
