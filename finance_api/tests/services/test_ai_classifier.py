"""Unit tests for the AI classifier client and its pure payload helpers."""

from typing import Any

import httpx
import pytest

from finance_api.services.ai_classifier import (
    AIClassifierClient,
    build_classify_payload,
    extract_suggestions,
)

TRANSACTIONS = [{"id": "1", "merchant": "CEMIG", "amount": 150.0}]
EXPENSE_CATEGORIES = [{"key": "moradia", "display_name": "Moradia"}]
INCOME_CATEGORIES = [{"key": "salario", "display_name": "Salário"}]


class FakeHttpClient:
    """Minimal async HTTP client double that records the posted payload."""

    def __init__(self, response: httpx.Response | None = None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def post(self, url: str, json: dict[str, Any], timeout: float) -> httpx.Response:
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        if self._error is not None:
            raise self._error
        if self._response is None:
            raise RuntimeError("Fake HTTP client has no response configured")
        return self._response


def build_response(
    status_code: int = 200, body: Any = None, text: str | None = None
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=body if text is None else None,
        text=text,
        request=httpx.Request("POST", "http://agent/classify/transactions"),
    )


def build_client(
    response: httpx.Response | None = None,
    error: Exception | None = None,
) -> tuple[AIClassifierClient, FakeHttpClient]:
    fake = FakeHttpClient(response=response, error=error)
    return AIClassifierClient(client=fake), fake


def test_build_classify_payload_matches_the_endpoint_contract():
    payload = build_classify_payload(TRANSACTIONS, EXPENSE_CATEGORIES, INCOME_CATEGORIES)

    assert payload == {
        "transactions": TRANSACTIONS,
        "expense_categories": EXPENSE_CATEGORIES,
        "income_categories": INCOME_CATEGORIES,
    }


def test_extract_suggestions_converts_confidence_and_skips_missing_values():
    body = {
        "suggestions": [
            {"id": 1, "category": "moradia", "confidence": 0.9},
            {"id": 2, "category": None, "confidence": None},
        ]
    }

    assert extract_suggestions(body) == {
        "1": ("moradia", 0.9),
        "2": (None, None),
    }


def test_extract_suggestions_tolerates_a_response_without_suggestions():
    assert extract_suggestions({}) == {}


@pytest.mark.asyncio
async def test_classify_batch_returns_suggestions_when_the_service_succeeds():
    body = {"suggestions": [{"id": 1, "category": "moradia", "confidence": 0.8}]}
    client, fake = build_client(build_response(body=body))

    suggestions, ai_used = await client.classify_batch(
        TRANSACTIONS,
        EXPENSE_CATEGORIES,
        INCOME_CATEGORIES,
    )

    assert ai_used is True
    assert suggestions == {"1": ("moradia", 0.8)}
    assert fake.calls[0]["url"].endswith("/classify/transactions")
    assert fake.calls[0]["json"]["transactions"] == TRANSACTIONS


@pytest.mark.asyncio
async def test_classify_batch_skips_the_request_when_there_are_no_transactions():
    client, fake = build_client(build_response(body={"suggestions": []}))

    suggestions, ai_used = await client.classify_batch([], EXPENSE_CATEGORIES, INCOME_CATEGORIES)

    assert (suggestions, ai_used) == ({}, False)
    assert fake.calls == []


@pytest.mark.asyncio
async def test_classify_batch_reports_failure_on_unexpected_status():
    client, _ = build_client(build_response(status_code=503, text="unavailable"))

    suggestions, ai_used = await client.classify_batch(
        TRANSACTIONS, EXPENSE_CATEGORIES, INCOME_CATEGORIES
    )

    assert (suggestions, ai_used) == ({}, False)


@pytest.mark.asyncio
async def test_classify_batch_reports_failure_on_transport_errors():
    client, _ = build_client(error=httpx.ConnectError("connection refused"))

    suggestions, ai_used = await client.classify_batch(
        TRANSACTIONS, EXPENSE_CATEGORIES, INCOME_CATEGORIES
    )

    assert (suggestions, ai_used) == ({}, False)


@pytest.mark.asyncio
async def test_classify_batch_reports_failure_on_malformed_json():
    client, _ = build_client(build_response(body=None, text="not json"))

    suggestions, ai_used = await client.classify_batch(
        TRANSACTIONS, EXPENSE_CATEGORIES, INCOME_CATEGORIES
    )

    assert (suggestions, ai_used) == ({}, False)
