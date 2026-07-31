import plotly.express as px
import plotly.graph_objects as go

from core.decorators import handle_service_errors
from core.exceptions import GraphGenerationError


@handle_service_errors
async def generate_balance_bar_chart(
    balances: list[dict], title: str, mode: str = "saldo"
) -> bytes:
    """Generates a bar chart image comparing limits vs expenses by category."""
    categories: list[str] = []
    limits: list[float] = []
    spents: list[float] = []
    availables: list[float] = []

    for b in balances:
        categories.append(b["category_display_name"])
        limits.append(b["limit"])
        spents.append(b["spent"])
        availables.append(max(0, b["available"]))

    if mode == "limites":
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
    else:
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

    try:
        return fig.to_image(format="png", width=800, height=500)
    except Exception as e:
        raise GraphGenerationError(f"Failed to render bar chart: {str(e)}")


@handle_service_errors
async def generate_expense_pie_chart(balances: list[dict], title: str) -> bytes:
    """Generates a pie chart image showing expense distribution by category."""
    categories: list[str] = []
    spents: list[float] = []

    for b in balances:
        if b["spent"] > 0:
            categories.append(b["category_display_name"])
            spents.append(b["spent"])

    if not categories:
        fig = go.Figure()
        fig.update_layout(title="Nenhum gasto registrado", template="plotly_white")
        try:
            return fig.to_image(format="png", width=800, height=500)
        except Exception as e:
            raise GraphGenerationError(f"Failed to render empty chart: {str(e)}")

    fig = px.pie(values=spents, names=categories, title=title, hole=0.3)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(template="plotly_white")

    try:
        return fig.to_image(format="png", width=800, height=500)
    except Exception as e:
        raise GraphGenerationError(f"Failed to render pie chart: {str(e)}")
