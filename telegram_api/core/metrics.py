from prometheus_client import Counter, Histogram, start_http_server

# Telegram Bot metrics
TELEGRAM_MESSAGES_RECEIVED_TOTAL = Counter(
    "flauzino_telegram_messages_received_total",
    "Total de mensagens recebidas pelo bot do Telegram",
    ["type"],  # text, voice, photo, command, callback_query, unauthorized
)

TELEGRAM_MESSAGES_SENT_TOTAL = Counter(
    "flauzino_telegram_messages_sent_total",
    "Total de respostas enviadas pelo bot do Telegram",
    ["status"],  # success, error
)

TELEGRAM_HANDLER_DURATION_SECONDS = Histogram(
    "flauzino_telegram_handler_duration_seconds",
    "Tempo de processamento das mensagens do Telegram em segundos",
    ["type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)


def start_metrics_server(port: int = 8003) -> None:
    """Inicia o servidor HTTP em background para raspagem de métricas do Prometheus."""
    try:
        start_http_server(port)
    except OSError:
        # Se a porta já estiver em uso (por exemplo durante testes), apenas ignora
        pass
