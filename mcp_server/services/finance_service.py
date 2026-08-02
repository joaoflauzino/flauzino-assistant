import httpx

from mcp_server.core.decorators import handle_service_errors
from mcp_server.core.settings import settings


@handle_service_errors
async def fetch_balance(
    reference_month: str | None = None, categories: list[str] | None = None
) -> list[dict]:
    """Fetches balance data from the Finance API and optionally filters by category."""
    url = f"{settings.FINANCE_SERVICE_URL}/limits/balance"
    if reference_month:
        url += f"?reference_month={reference_month}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    if categories and "todas as categorias" not in [c.lower() for c in categories]:
        filtered_data = [
            b
            for b in data
            if any(
                c.lower() in b["category_display_name"].lower()
                or c.lower() in b["category"].lower()
                for c in categories
            )
        ]
        return filtered_data

    return data
