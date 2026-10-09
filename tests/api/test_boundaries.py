import pytest
from playwright.sync_api import APIRequestContext, Playwright

PAYLOAD = {"title": "Inspection", "description": "Synthetic work", "customer_id": 1}


@pytest.fixture
def order(api: APIRequestContext) -> dict[str, object]:
    response = api.post("/api/orders", data=PAYLOAD)
    assert response.status == 201, response.text()
    return response.json()


@pytest.mark.regression
@pytest.mark.parametrize("field", ["title", "description", "customer_id"])
def test_missing_create_field(api: APIRequestContext, field: str) -> None:
    payload = {key: value for key, value in PAYLOAD.items() if key != field}
    response = api.post("/api/orders", data=payload)
    assert response.status == 422
    assert response.json()["error"]["message"] == "Invalid request"
    stored = api.get("/api/orders")
    assert stored.status == 200
    assert stored.json() == []


@pytest.mark.regression
@pytest.mark.parametrize("field", ["title", "description"])
@pytest.mark.parametrize("length,expected", [(1, 201), (500, 201), (501, 422)])
def test_text_length_boundaries(
    api: APIRequestContext, field: str, length: int, expected: int
) -> None:
    payload = {**PAYLOAD, field: "x" * length}
    response = api.post("/api/orders", data=payload)
    assert response.status == expected, response.text()
    listing = api.get("/api/orders")
    assert listing.status == 200
    if expected == 201:
        assert response.json()[field] == payload[field]
        assert listing.json() == [response.json()]
    else:
        assert response.json()["error"]["message"] == "Invalid request"
        assert listing.json() == []


@pytest.mark.regression
def test_unknown_customer(api: APIRequestContext) -> None:
    response = api.post("/api/orders", data={**PAYLOAD, "customer_id": 999})
    assert response.status == 422
    assert response.json() == {"error": {"message": "Unknown customer"}}
    listing = api.get("/api/orders")
    assert listing.status == 200
    assert listing.json() == []


@pytest.mark.regression
@pytest.mark.parametrize("operation", ["read", "edit", "status"])
def test_nonexistent_order(api: APIRequestContext, operation: str) -> None:
    if operation == "read":
        response = api.get("/api/orders/999")
    elif operation == "edit":
        response = api.patch(
            "/api/orders/999", data={"title": "Updated", "description": "Updated"}
        )
    else:
        response = api.patch("/api/orders/999/status", data={"status": "In Progress"})
    assert response.status == 404
    assert response.json() == {"error": {"message": "Work order not found"}}


@pytest.mark.regression
def test_invalid_status_value(api: APIRequestContext, order: dict[str, object]) -> None:
    response = api.patch(f'/api/orders/{order["id"]}/status', data={"status": "Cancelled"})
    assert response.status == 422
    assert response.json()["error"]["message"] == "Invalid request"
    stored = api.get(f'/api/orders/{order["id"]}')
    assert stored.status == 200
    assert stored.json() == order
    invalid_filter = api.get("/api/orders?status=Cancelled")
    assert invalid_filter.status == 422


@pytest.mark.regression
@pytest.mark.parametrize(
    "initial,target",
    [
        ("Pending", "Pending"), ("Pending", "Completed"),
        ("In Progress", "Pending"), ("In Progress", "In Progress"),
        ("Completed", "Pending"), ("Completed", "In Progress"),
        ("Completed", "Completed"),
    ],
)
def test_rejected_transition_preserves_state(
    api: APIRequestContext, order: dict[str, object], initial: str, target: str
) -> None:
    path = f'/api/orders/{order["id"]}'
    if initial in ("In Progress", "Completed"):
        assert api.patch(f"{path}/status", data={"status": "In Progress"}).status == 200
    if initial == "Completed":
        assert api.patch(f"{path}/status", data={"status": "Completed"}).status == 200
    before = api.get(path)
    assert before.status == 200
    assert before.json()["status"] == initial
    rejected = api.patch(f"{path}/status", data={"status": target})
    assert rejected.status == 409
    assert rejected.json() == {"error": {"message": "Invalid status transition"}}
    after = api.get(path)
    assert after.status == 200
    assert after.json() == before.json()


@pytest.mark.regression
@pytest.mark.parametrize("initial", ["Pending", "In Progress", "Completed"])
def test_edit_rules(
    api: APIRequestContext, order: dict[str, object], initial: str
) -> None:
    path = f'/api/orders/{order["id"]}'
    if initial in ("In Progress", "Completed"):
        assert api.patch(f"{path}/status", data={"status": "In Progress"}).status == 200
    if initial == "Completed":
        assert api.patch(f"{path}/status", data={"status": "Completed"}).status == 200
    update = {"title": "  Updated title  ", "description": "  Updated description  "}
    response = api.patch(path, data=update)
    stored = api.get(path)
    assert stored.status == 200
    if initial == "Completed":
        assert response.status == 409
        assert response.json() == {"error": {"message": "Completed orders cannot be edited"}}
        assert stored.json() == {**order, "status": initial}
    else:
        assert response.status == 200
        assert stored.json() == {
            **order, "status": initial, "title": "Updated title",
            "description": "Updated description",
        }
        assert response.json() == stored.json()


@pytest.mark.regression
@pytest.mark.parametrize("field", ["title", "description"])
@pytest.mark.parametrize("value", ["", "   ", "x" * 501], ids=["empty", "spaces", "too-long"])
def test_invalid_edit_preserves_order(
    api: APIRequestContext, order: dict[str, object], field: str, value: str
) -> None:
    path = f'/api/orders/{order["id"]}'
    update = {"title": "Updated", "description": "Updated", field: value}
    response = api.patch(path, data=update)
    assert response.status == 422
    stored = api.get(path)
    assert stored.status == 200
    assert stored.json() == order


@pytest.mark.regression
def test_customer_cannot_change(
    api: APIRequestContext, order: dict[str, object]
) -> None:
    path = f'/api/orders/{order["id"]}'
    response = api.patch(
        path, data={"title": "Updated", "description": "Updated", "customer_id": 2}
    )
    assert response.status == 422
    stored = api.get(path)
    assert stored.status == 200
    assert stored.json() == order


@pytest.mark.regression
def test_invalid_login_does_not_establish_session(
    playwright: Playwright, app_url: str
) -> None:
    client = playwright.request.new_context(base_url=app_url)
    try:
        response = client.post(
            "/api/login", data={"username": "demo", "password": "incorrect"}
        )
        assert response.status == 401
        assert response.json() == {"error": {"message": "Invalid credentials"}}
        assert client.get("/api/orders").status == 401
    finally:
        client.dispose()


@pytest.mark.regression
@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("GET", "/api/customers", None),
        ("GET", "/api/orders/1", None),
        ("POST", "/api/orders", PAYLOAD),
        ("PATCH", "/api/orders/1", {"title": "Updated", "description": "Updated"}),
        ("PATCH", "/api/orders/1/status", {"status": "In Progress"}),
        ("POST", "/api/logout", None),
    ],
)
def test_protected_endpoints_reject_anonymous_requests(
    api: APIRequestContext, order: dict[str, object], playwright: Playwright,
    app_url: str, method: str, path: str, payload: dict[str, object] | None,
) -> None:
    assert order["id"] == 1
    client = playwright.request.new_context(base_url=app_url)
    try:
        response = client.fetch(path, method=method, data=payload)
        assert response.status == 401
        assert response.json() == {"error": {"message": "Login required"}}
    finally:
        client.dispose()
    stored = api.get("/api/orders")
    assert stored.status == 200
    assert stored.json() == [order]


@pytest.mark.regression
@pytest.mark.parametrize("extra", [{"status": "Completed"}, {"id": 99}])
def test_create_rejects_server_owned_fields(
    api: APIRequestContext, extra: dict[str, object]
) -> None:
    rejected = api.post("/api/orders", data={**PAYLOAD, **extra})
    assert rejected.status == 422
    stored = api.get("/api/orders")
    assert stored.status == 200
    assert stored.json() == []


@pytest.mark.regression
def test_api_filters_by_status(api: APIRequestContext, order: dict[str, object]) -> None:
    created = api.post("/api/orders", data={**PAYLOAD, "title": "Second inspection"})
    assert created.status == 201
    second = created.json()
    progressed = api.patch(
        f'/api/orders/{second["id"]}/status', data={"status": "In Progress"}
    )
    assert progressed.status == 200
    for status, expected in [
        ("Pending", [order]),
        ("In Progress", [{**second, "status": "In Progress"}]),
        ("Completed", []),
    ]:
        listing = api.get("/api/orders", params={"status": status})
        assert listing.status == 200
        assert listing.json() == expected
