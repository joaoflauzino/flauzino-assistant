import logging
import uuid

from telegram_api.core.correlation import (
    clear_request_id,
    get_request_id,
    set_request_id,
)
from telegram_api.core.logger import CorrelationIdFilter


def test_telegram_set_and_get_request_id():
    custom_id = "test-tg-12345"
    set_request_id(custom_id)
    assert get_request_id() == custom_id

    generated_id = set_request_id(None)
    assert generated_id != ""
    assert get_request_id() == generated_id
    uuid.UUID(generated_id)


def test_telegram_correlation_id_filter():
    logger = logging.getLogger("test_tg_logger")
    log_filter = CorrelationIdFilter()

    set_request_id("filter-tg-id")
    record = logger.makeRecord("test", logging.INFO, "test.py", 10, "msg", (), None)
    log_filter.filter(record)
    assert record.request_id == "filter-tg-id"

    clear_request_id()
    record_empty = logger.makeRecord("test", logging.INFO, "test.py", 10, "msg", (), None)
    log_filter.filter(record_empty)
    assert record_empty.request_id == "-"
