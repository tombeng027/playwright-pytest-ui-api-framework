import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from starlette.types import Message, Receive, Scope, Send

from demo_app.observability import EventLog, RequestLogMiddleware


@pytest.mark.regression
def test_unexpected_failure_is_logged_and_propagated(tmp_path: Path) -> None:
    path = tmp_path / "failure.jsonl"

    async def broken_app(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("PRIVATE_EXCEPTION_SENTINEL")

    async def receive() -> Message:
        return {"type": "http.request", "body": b""}

    async def send(message: Message) -> None:
        pytest.fail("Unexpected response from failing application")

    middleware = RequestLogMiddleware(broken_app, EventLog(path))
    def exercise() -> None:
        asyncio.run(middleware(
            {"type": "http", "method": "GET", "path": "/private-path"},
            receive, send,
        ))

    # Playwright's sync session owns a loop on the pytest thread.
    with ThreadPoolExecutor(max_workers=1) as executor:
        with pytest.raises(RuntimeError, match="PRIVATE_EXCEPTION_SENTINEL"):
            executor.submit(exercise).result(timeout=5)
    text = path.read_text(encoding="utf-8")
    event = json.loads(text)
    assert event["status"] == 500
    assert event["level"] == "ERROR"
    assert event["exception_type"] == "RuntimeError"
    assert event["route"] == "<unmatched>"
    assert "PRIVATE_EXCEPTION_SENTINEL" not in text
    assert "/private-path" not in text
