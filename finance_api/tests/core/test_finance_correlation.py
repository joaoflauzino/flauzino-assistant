import logging
import uuid
from fastapi import FastAPI
from fastapi.testclient import TestClient

from finance_api.core.correlation import (
    CORRELATION_HEADER,
    clear_request_id,
    get_request_id,
    set_request_id,
)
from finance_api.core.logger import CorrelationIdFilter
from finance_api.core.middlewares import CorrelationIdMiddleware


def test_set_and_get_request_id():
    custom_id = "test-fin-12345"
    set_request_id(custom_id)
    assert get_request_id() == custom_id

    generated_id = set_request_id(None)
    assert generated_id != ""
    assert get_request_id() == generated_id
    uuid.UUID(generated_id)


def test_correlation_id_filter():
    logger = logging.getLogger("test_fin_logger")
    log_filter = CorrelationIdFilter()

    set_request_id("filter-fin-id")
    record = logger.makeRecord("test", logging.INFO, "test.py", 10, "msg", (), None)
    log_filter.filter(record)
    assert record.request_id == "filter-fin-id"

    clear_request_id()
    record_empty = logger.makeRecord("test", logging.INFO, "test.py", 10, "msg", (), None)
    log_filter.filter(record_empty)
    assert record_empty.request_id == "-"


def test_correlation_id_middleware_with_incoming_header():
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"request_id": get_request_id()}

    client = TestClient(app)
    custom_header_id = "fin-trace-id-888"
    response = client.get("/ping", headers={CORRELATION_HEADER: custom_header_id})

    assert response.status_code == 200
    assert response.headers.get(CORRELATION_HEADER) == custom_header_id
    assert response.json()["request_id"] == custom_header_id


def test_correlation_id_middleware_generates_header_if_missing():
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"request_id": get_request_id()}

    client = TestClient(app)
    response = client.get("/ping")

    assert response.status_code == 200
    returned_id = response.headers.get(CORRELATION_HEADER)
    assert returned_id is not None
    assert response.json()["request_id"] == returned_id
    uuid.UUID(returned_id)
