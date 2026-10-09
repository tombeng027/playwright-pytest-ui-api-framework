import pytest
from playwright.sync_api import APIRequestContext, Playwright


@pytest.mark.regression
def test_invalid_transition_preserves_order(api: APIRequestContext) -> None:
    created = api.post(
        "/api/orders",
        data={"title": "Check pump", "description": "Synthetic inspection", "customer_id": 1},
    )
    assert created.status == 201, created.text()
    order = created.json()
    rejected = api.patch(f'/api/orders/{order["id"]}/status', data={"status": "Completed"})
    assert rejected.status == 409, (
        f"TRANSITION_GUARD: expected 409, got {rejected.status}"
    )
    assert rejected.json() == {"error": {"message": "Invalid status transition"}}
    stored = api.get(f'/api/orders/{order["id"]}')
    assert stored.status == 200
    assert stored.json() == order


@pytest.mark.regression
def test_blank_title_does_not_create_order(api: APIRequestContext) -> None:
    rejected = api.post(
        "/api/orders",
        data={"title": "   ", "description": "Synthetic inspection", "customer_id": 1},
    )
    assert rejected.status == 422
    assert rejected.json()["error"]["message"] == "Invalid request"
    listing = api.get("/api/orders")
    assert listing.status == 200
    assert listing.json() == []


@pytest.mark.smoke
def test_anonymous_access_and_logout_invalidation(
    api: APIRequestContext, playwright: Playwright, app_url: str
) -> None:
    anonymous = playwright.request.new_context(base_url=app_url)
    try:
        denied = anonymous.get("/api/orders")
        assert denied.status == 401
        assert denied.json() == {"error": {"message": "Login required"}}
    finally:
        anonymous.dispose()
    # Copy the session before logout to verify server-side revocation, not only cookie removal.
    previous_session = playwright.request.new_context(
        base_url=app_url, storage_state=api.storage_state()
    )
    try:
        assert previous_session.get("/api/orders").status == 200
        assert api.post("/api/logout").status == 204
        assert previous_session.get("/api/orders").status == 401
    finally:
        previous_session.dispose()
