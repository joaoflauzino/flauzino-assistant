
from telegram_api.core.metrics import (
    TELEGRAM_MESSAGES_RECEIVED_TOTAL,
    start_metrics_server,
)


def test_start_metrics_server_idempotent():
    # Should not raise even if called multiple times
    start_metrics_server(port=8003)
    start_metrics_server(port=8003)


def test_telegram_metrics_counters():
    before = TELEGRAM_MESSAGES_RECEIVED_TOTAL.labels(type="text")._value.get()
    TELEGRAM_MESSAGES_RECEIVED_TOTAL.labels(type="text").inc()
    after = TELEGRAM_MESSAGES_RECEIVED_TOTAL.labels(type="text")._value.get()
    assert after == before + 1
