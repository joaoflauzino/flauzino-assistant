"""Protocols and structural contracts for graph_api services."""

from typing import Any, Protocol

import plotly.graph_objects as go


class ChartBuildStrategy(Protocol):
    """Structural contract for building a Plotly figure from balance records."""

    def build_figure(self, balances: list[dict[str, Any]], title: str) -> go.Figure: ...
