import os

from prometheus_client import (CollectorRegistry, Counter, Gauge, Histogram,
                               multiprocess)
from prometheus_fastapi_instrumentator import Instrumentator, metrics

# set PROMETHEUS_MULTIPROC_DIR to a directory that Prometheus can read
# to collect metrics from multiple processes

if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
    os.makedirs(os.environ["PROMETHEUS_MULTIPROC_DIR"], exist_ok=True)
    print(f"Prometheus multiprocess directory: {os.environ['PROMETHEUS_MULTIPROC_DIR']}")
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)

else:
    registry = CollectorRegistry()

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "handler", "status", "climbingLocation_id"],
    registry=registry,
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "handler", "climbingLocation_id"],
    registry=registry,
)

QRCODE_COUNTER = Counter(
    "qrcode_requests_total",
    "Total qrcode requests",
    ["climbingLocation_id", "qrcode_type"],
    registry=registry,
)

def http_requests_total(info: metrics.Info) -> None:
    """Increments the counter for total HTTP requests."""
    REQUEST_COUNTER.labels(
        method=info.request.method,
        handler=info.modified_handler,
        status=info.response.status_code,
        climbingLocation_id=info.request.path_params.get("climbingLocation_id", "N/A")
    ).inc()

def http_request_duration_seconds(info: metrics.Info) -> None:
    """Observes the duration of HTTP requests."""
    REQUEST_DURATION.labels(
        method=info.request.method,
        handler=info.modified_handler,
        climbingLocation_id=info.request.path_params.get("climbingLocation_id", "N/A")
    ).observe(info.modified_duration)

def setup_metrics(app):
    instrumentator = Instrumentator(
        excluded_handlers=["/metrics", "/swagger", "/redoc"],
        should_instrument_requests_inprogress=True,
        inprogress_name="http_requests_inprogress",
        inprogress_labels=False,
        registry=registry,
    )
    instrumentator.add(http_requests_total)
    instrumentator.add(http_request_duration_seconds)

    instrumentator.instrument(app)
    instrumentator.expose(app)
