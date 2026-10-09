"""Function-scoped app/database isolation; no shared cloud or public-site state."""

from __future__ import annotations

import socket
import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Iterator
from urllib.error import URLError
from urllib.request import urlopen

import pytest
import uvicorn
from playwright.sync_api import APIRequestContext, ConsoleMessage, Page, Playwright
from playwright.sync_api import Request as BrowserRequest, Response as BrowserResponse

from demo_app.app import create_app
from demo_app.observability import EventLog


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--demo-defect", action="store_true", default=False,
        help="Explicit demo only: permit Pending -> Completed; regression tests must fail.",
    )
    parser.addoption(
        "--app-log-dir", default="artifacts/logs",
        help="Directory for per-test structured application logs.",
    )


@pytest.fixture(autouse=True)
def browser_observations(request: pytest.FixtureRequest) -> Iterator[None]:
    if "page" not in request.fixturenames:
        yield
        return
    page: Page = request.getfixturevalue("page")
    path: Path = request.getfixturevalue("log_path")
    events = EventLog(path)

    def console(message: ConsoleMessage) -> None:
        if message.type == "error":
            events.browser("browser_console_error")

    def page_error(_error: Exception) -> None:
        events.browser("browser_page_error")

    def failed(request: BrowserRequest) -> None:
        events.browser("browser_network_failure", method=request.method)

    def response(response: BrowserResponse) -> None:
        if response.status >= 400:
            # Read only the server-generated ID; never response bodies or arbitrary headers.
            events.browser(
                "browser_http_error", method=response.request.method,
                status=response.status,
                request_id=response.header_value("x-request-id"),
            )

    handlers = {
        "console": console, "pageerror": page_error,
        "requestfailed": failed, "response": response,
    }
    for event, handler in handlers.items():
        page.on(event, handler)
    try:
        yield
    finally:
        for event, handler in handlers.items():
            page.remove_listener(event, handler)


@pytest.fixture
def log_path(request: pytest.FixtureRequest) -> Path:
    identity = hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:16]
    directory = Path(request.config.getoption("--app-log-dir"))
    if not directory.is_absolute():
        directory = Path(str(request.config.rootpath)) / directory
    path = directory / f"{identity}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    request.node.add_report_section("setup", "application log", str(path))
    return path


@pytest.fixture
def app_url(
    tmp_path: Path, log_path: Path, request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[str]:
    events = EventLog(log_path)
    events.lifecycle("app_starting", request.node.nodeid)
    app = create_app(
        tmp_path / "orders.sqlite3", events,
        allow_pending_completion_defect=request.config.getoption("--demo-defect"),
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, log_level="info", lifespan="off", access_log=False)
    )
    # pytest adds capture handlers after Uvicorn clears them; new connections
    # otherwise treat those handlers as a request to enable raw access logs.
    monkeypatch.setattr(logging.getLogger("uvicorn.access"), "disabled", True)
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [listener]}, daemon=True
    )
    url = f"http://127.0.0.1:{port}"
    try:
        thread.start()
        deadline = time.monotonic() + 10
        last_error: URLError | TimeoutError | None = None
        while time.monotonic() < deadline:
            if not thread.is_alive():
                pytest.fail("Demo server exited during startup; inspect captured logs")
            try:
                with urlopen(f"{url}/health", timeout=0.5) as response:
                    if response.status == 200:
                        break
            except (URLError, TimeoutError) as error:
                last_error = error
            # Bounded readiness polling, not browser/test synchronization.
            threading.Event().wait(0.05)
        else:
            pytest.fail(f"Demo server not ready after 10 seconds: {last_error}")
        events.lifecycle("app_ready", request.node.nodeid)
        yield url
    finally:
        server.should_exit = True
        if thread.ident is not None:
            thread.join(timeout=5)
        listener.close()
        if thread.is_alive():
            events.lifecycle("app_stop_failed", request.node.nodeid, failed=True)
            pytest.fail("Demo server did not stop within 5 seconds")
        events.lifecycle("app_stopped", request.node.nodeid)


@pytest.fixture
def api(playwright: Playwright, app_url: str) -> Iterator[APIRequestContext]:
    client = playwright.request.new_context(base_url=app_url)
    try:
        response = client.post(
            "/api/login", data={"username": "demo", "password": "demo-password"}
        )
        assert response.status == 200, response.text()
        yield client
    finally:
        client.dispose()
