import json
from pathlib import Path

import pytest
from playwright.sync_api import APIRequestContext, Playwright


@pytest.mark.regression
def test_raw_access_logs_stay_disabled(
    api: APIRequestContext, playwright: Playwright, app_url: str,
    caplog: pytest.LogCaptureFixture, log_path: Path,
) -> None:
    caplog.clear()
    client = playwright.request.new_context(
        base_url=app_url, storage_state=api.storage_state()
    )
    try:
        response = client.get("/api/orders?private=RAW_QUERY_SENTINEL")
        assert response.status == 200
    finally:
        client.dispose()
    records = [record for record in caplog.records if record.name == "uvicorn.access"]
    assert records == [], "pytest capture re-enabled raw Uvicorn access logging"
    structured = log_path.read_text(encoding="utf-8")
    assert "RAW_QUERY_SENTINEL" not in structured
    assert response.headers["x-request-id"] in structured


@pytest.mark.regression
def test_correlated_logs_omit_sensitive_data(
    api: APIRequestContext, log_path: Path
) -> None:
    payload = {
        "title": "PRIVATE_TITLE_SENTINEL",
        "description": "PRIVATE_DESCRIPTION_SENTINEL",
        "customer_id": 1,
    }
    created = api.post(
        "/api/orders?secret=PRIVATE_QUERY_SENTINEL", data=payload,
        headers={"Authorization": "PRIVATE_HEADER_SENTINEL"},
    )
    assert created.status == 201
    order = created.json()
    # Log writes finish as the ASGI call returns; a following request also checks readiness.
    rejected = api.patch(
        f'/api/orders/{order["id"]}/status', data={"status": "Completed"}
    )
    assert rejected.status == 409
    assert api.get(f'/api/orders/{order["id"]}').json() == order
    text = log_path.read_text(encoding="utf-8")
    records = [json.loads(line) for line in text.splitlines()]
    requests = {
        event["request_id"]: event for event in records
        if event["event"] == "http_request"
    }
    success = requests[created.headers["x-request-id"]]
    conflict = requests[rejected.headers["x-request-id"]]
    assert success["route"] == "/api/orders"
    assert success["status"] == 201
    assert success["level"] == "INFO"
    assert conflict["route"] == "/api/orders/{order_id}/status"
    assert conflict["status"] == 409
    assert conflict["level"] == "WARNING"
    for record in (success, conflict):
        assert record["duration_ms"] >= 0
        assert record["timestamp"].endswith("+00:00")
        assert set(record) == {
            "timestamp", "level", "event", "request_id", "method",
            "route", "status", "duration_ms",
        }
    tokens = [cookie["value"] for cookie in api.storage_state()["cookies"]]
    for secret in [
        "demo-password", "PRIVATE_TITLE_SENTINEL", "PRIVATE_DESCRIPTION_SENTINEL",
        "PRIVATE_QUERY_SENTINEL", "PRIVATE_HEADER_SENTINEL", *tokens,
    ]:
        assert secret not in text
    assert any(event["event"] == "app_ready" for event in records)
