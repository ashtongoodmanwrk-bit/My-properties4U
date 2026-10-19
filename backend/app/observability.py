import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, Request

logger = logging.getLogger("app.request")


class JsonFormatter(logging.Formatter):
    """One JSON object per log line, easy to search in Render's log viewer."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if fields:
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging() -> None:
    app_logger = logging.getLogger("app")
    if app_logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False


def setup_sentry() -> None:
    """Error tracking is only switched on when SENTRY_DSN is set."""
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("ENVIRONMENT", "production"),
        traces_sample_rate=0.0,
        send_default_pii=False,
    )


def setup_observability(app: FastAPI) -> None:
    setup_logging()
    setup_sentry()

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        fields = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        }
        try:
            response = await call_next(request)
        except Exception:
            fields["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)
            logger.exception("request failed", extra={"fields": fields})
            raise
        response.headers["X-Request-ID"] = request_id
        if request.url.path != "/health":  # Render pings this every few seconds
            fields["status"] = response.status_code
            fields["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)
            logger.info("request", extra={"fields": fields})
        return response
