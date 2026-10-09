"""Allowlisted JSON events: no request bodies, headers or exception messages."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class JsonLineHandler(logging.Handler):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            **json.loads(record.getMessage()),
        }
        # Open per event so application instances never retain file handles.
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=True) + "\n")


class EventLog:
    def __init__(self, path: Path) -> None:
        self.logger = logging.Logger("work_order_demo", level=logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(JsonLineHandler(path))
        self.lock = threading.Lock()

    def request(
        self, *, request_id: str, method: str, route: str, status: int,
        duration_ms: float, exception_type: str | None = None,
    ) -> None:
        fields: dict[str, str | int | float] = {
            "event": "http_request", "request_id": request_id,
            "method": method, "route": route, "status": status,
            "duration_ms": round(duration_ms, 3),
        }
        if exception_type is not None:
            fields["exception_type"] = exception_type
        level = logging.ERROR if status >= 500 or exception_type is not None else (
            logging.WARNING if status >= 400 else logging.INFO
        )
        with self.lock:
            self.logger.log(level, json.dumps(fields))

    def lifecycle(self, event: str, test_id: str, *, failed: bool = False) -> None:
        with self.lock:
            self.logger.log(
                logging.ERROR if failed else logging.INFO,
                json.dumps({"event": event, "test_id": test_id}),
            )

    def browser(
        self, event: str, *, method: str | None = None,
        status: int | None = None, request_id: str | None = None,
    ) -> None:
        fields: dict[str, str | int] = {"event": event}
        if method is not None:
            fields["method"] = method
        if status is not None:
            fields["status"] = status
        if request_id is not None:
            fields["request_id"] = request_id
        # Browser observations include expected negative tests; do not label all as defects.
        with self.lock:
            self.logger.log(logging.INFO, json.dumps(fields))


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp, events: EventLog) -> None:
        self.app = app
        self.events = events

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex
        started = time.perf_counter()
        status = 500
        exception_type: str | None = None

        async def correlated_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, correlated_send)
        except Exception as error:
            # Capture only the class name, then preserve the original failure.
            exception_type = type(error).__name__
            raise
        finally:
            route = getattr(scope.get("route"), "path", "<unmatched>")
            self.events.request(
                request_id=request_id, method=scope["method"], route=route,
                status=status, duration_ms=(time.perf_counter() - started) * 1000,
                exception_type=exception_type,
            )
