from agent_api.schemas.limit import LimitDetails


def test_limit_details_normalizes_category_and_preserves_amount() -> None:
    limit = LimitDetails(categoria="  MERCADO  ", valor=250.0)

    assert limit.categoria == "mercado"
    assert limit.valor == 250.0
