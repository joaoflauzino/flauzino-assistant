"""Strategy Pattern implementations for building Plotly chart figures."""

from typing import Any

import plotly.express as px
import plotly.graph_objects as go

from graph_api.schemas.graphs import ChartMode
from graph_api.services.protocols import ChartBuildStrategy


class LimitsBarChartStrategy:
    """Builds a bar chart comparing configured limits across categories."""

    def build_figure(self, balances: list[dict[str, Any]], title: str) -> go.Figure:
        categories = [b["category_display_name"] for b in balances]
        limits = [b["limit"] for b in balances]
        fig = go.Figure(
            data=[
                go.Bar(
                    name="Limite",
                    x=categories,
                    y=limits,
                    marker_color="cornflowerblue",
                    text=[f"R$ {v:.2f}" for v in limits],
                    textposition="auto",
                )
            ]
        )
        fig.update_layout(
            title=title,
            yaxis_title="Valor (R$)",
            xaxis_title="Categoria",
            template="plotly_white",
        )
        return fig


class BalanceStackedBarChartStrategy:
    """Builds a stacked bar chart comparing spent amounts vs available balance per category."""

    def build_figure(self, balances: list[dict[str, Any]], title: str) -> go.Figure:
        categories = [b["category_display_name"] for b in balances]
        spents = [b["spent"] for b in balances]
        availables = [max(0, b["available"]) for b in balances]
        fig = go.Figure(
            data=[
                go.Bar(
                    name="Gasto",
                    x=categories,
                    y=spents,
                    marker_color="tomato",
                    text=[f"R$ {v:.2f}" if v > 0 else "" for v in spents],
                    textposition="inside",
                    insidetextanchor="middle",
                ),
                go.Bar(
                    name="Saldo Disponível",
                    x=categories,
                    y=availables,
                    marker_color="lightgreen",
                    text=[f"R$ {v:.2f}" if v > 0 else "" for v in availables],
                    textposition="inside",
                    insidetextanchor="middle",
                ),
            ]
        )
        fig.update_layout(
            barmode="stack",
            title=title,
            yaxis_title="Valor (R$)",
            xaxis_title="Categoria",
            template="plotly_white",
            uniformtext_minsize=10,
            uniformtext_mode="show",
        )
        return fig


class ExpensePieChartStrategy:
    """Builds a pie chart showing expense distribution across categories."""

    def build_figure(self, balances: list[dict[str, Any]], title: str) -> go.Figure:
        categories: list[str] = []
        spents: list[float] = []

        for b in balances:
            if b["spent"] > 0:
                categories.append(b["category_display_name"])
                spents.append(b["spent"])

        if not categories:
            fig = go.Figure()
            fig.update_layout(title="Nenhum gasto registrado", template="plotly_white")
            return fig

        fig = px.pie(values=spents, names=categories, title=title, hole=0.3)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(template="plotly_white")
        return fig


def build_default_chart_strategies() -> dict[ChartMode, ChartBuildStrategy]:
    """Builds the default dispatch table mapping ChartMode to chart build strategies."""
    return {
        ChartMode.LIMITES: LimitsBarChartStrategy(),
        ChartMode.SALDO: BalanceStackedBarChartStrategy(),
        ChartMode.PIE: ExpensePieChartStrategy(),
    }
