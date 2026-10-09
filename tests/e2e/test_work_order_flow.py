import pytest
from playwright.sync_api import APIRequestContext, Page, expect

from tests.ui.work_orders_page import WorkOrdersPage

@pytest.mark.smoke
@pytest.mark.e2e
def test_api_create_ui_progress_api_verify(
    api: APIRequestContext, page: Page, app_url: str
) -> None:
    payload = {
        "title": "Inspect workshop equipment",
        "description": "Check the synthetic demonstration equipment.",
        "customer_id": 1,
    }
    created = api.post("/api/orders", data=payload)
    assert created.status == 201, created.text()
    order = created.json()
    assert order["status"] == "Pending"
    for field, value in payload.items():
        assert order[field] == value

    page.goto(app_url)
    screen = WorkOrdersPage(page)
    screen.login()
    card = screen.card(order["id"])
    expect(card.get_by_role("heading")).to_have_text(payload["title"])
    expect(card.locator(".order-status")).to_have_text("Pending")

    card.get_by_role("button", name="Start work", exact=True).click()
    expect(card.locator(".order-status")).to_have_text("In Progress")
    progressed = api.get(f'/api/orders/{order["id"]}')
    assert progressed.status == 200, progressed.text()
    assert progressed.json() == {**order, "status": "In Progress"}

    card.get_by_role("button", name="Complete work", exact=True).click()
    expect(card.locator(".order-status")).to_have_text("Completed")
    expect(card.get_by_role("button", name="Save changes")).to_have_count(0)
    completed = api.get(f'/api/orders/{order["id"]}')
    assert completed.status == 200, completed.text()
    assert completed.json() == {**order, "status": "Completed"}
