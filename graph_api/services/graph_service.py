"""Graph rendering context service and dependency providers for graph_api."""

from typing import Annotated, Any

from fastapi import Depends

from graph_api.core.decorators import handle_service_errors
from graph_api.core.exceptions import GraphGenerationError
from graph_api.schemas.graphs import ChartMode
from graph_api.services.chart_strategies import build_default_chart_strategies
from graph_api.services.protocols import ChartBuildStrategy


class GraphRendererService:
    """Context class that delegates figure construction to ChartBuildStrategy and renders PNG bytes."""

    def __init__(
        self,
        strategies: dict[ChartMode, ChartBuildStrategy] | None = None,
    ) -> None:
        self._strategies = strategies or build_default_chart_strategies()

    def _resolve_strategy(self, mode: ChartMode | str) -> ChartBuildStrategy:
        try:
            chart_mode = ChartMode(mode)
        except ValueError:
            chart_mode = ChartMode.SALDO

        strategy = self._strategies.get(chart_mode)
        if strategy is None:
            raise GraphGenerationError(f"Unsupported chart mode: '{mode}'")
        return strategy

    @handle_service_errors
    async def render(
        self,
        balances: list[dict[str, Any]],
        title: str,
        mode: ChartMode | str = ChartMode.SALDO,
    ) -> bytes:
        strategy = self._resolve_strategy(mode)
        fig = strategy.build_figure(balances, title)
        try:
            return fig.to_image(format="png", width=800, height=500)
        except Exception as e:
            raise GraphGenerationError(f"Failed to render '{mode}' chart: {e}") from e


def get_graph_renderer_service() -> GraphRendererService:
    """FastAPI dependency provider for GraphRendererService."""
    return GraphRendererService(strategies=build_default_chart_strategies())


GraphRendererServiceDep = Annotated[GraphRendererService, Depends(get_graph_renderer_service)]


@handle_service_errors
async def generate_balance_bar_chart(
    balances: list[dict[str, Any]],
    title: str,
    mode: str = ChartMode.SALDO,
) -> bytes:
    """Generates a bar chart image comparing limits vs expenses by category."""
    renderer = GraphRendererService()
    return await renderer.render(balances=balances, title=title, mode=mode)


@handle_service_errors
async def generate_expense_pie_chart(
    balances: list[dict[str, Any]],
    title: str,
) -> bytes:
    """Generates a pie chart image showing expense distribution by category."""
    renderer = GraphRendererService()
    return await renderer.render(balances=balances, title=title, mode=ChartMode.PIE)
