import pytest
from playwright.sync_api import APIRequestContext, Page, expect

from tests.ui.work_orders_page import WorkOrdersPage


@pytest.fixture
def workspace(page: Page, app_url: str) -> WorkOrdersPage:
    page.goto(app_url)
    screen = WorkOrdersPage(page)
    screen.login()
    expect(screen.workspace).to_be_visible()
    return screen


@pytest.mark.regression
def test_invalid_login_then_recovery(page: Page, app_url: str) -> None:
    page.goto(app_url)
    screen = WorkOrdersPage(page)
    screen.login(password="incorrect")
    expect(screen.error).to_have_text("Invalid credentials")
    expect(screen.workspace).to_be_hidden()
    screen.login()
    expect(screen.workspace).to_be_visible()
    expect(screen.error).to_be_hidden()


@pytest.mark.smoke
def test_ui_create_edit_and_logout(
    workspace: WorkOrdersPage, api: APIRequestContext
) -> None:
    workspace.create("  Inspect pump  ", "  Initial inspection  ", customer="2")
    expect(workspace.feedback).to_have_text("Order 1 created.")
    card = workspace.card(1)
    expect(card.get_by_role("heading")).to_have_text("Inspect pump")
    expect(card.locator(".order-status")).to_have_text("Pending")
    stored = api.get("/api/orders/1")
    assert stored.status == 200
    assert stored.json() == {
        "id": 1, "title": "Inspect pump", "description": "Initial inspection",
        "customer_id": 2, "status": "Pending",
    }
    workspace.edit(1, "Inspect motor", "Updated inspection")
    expect(workspace.feedback).to_have_text("Order 1 saved.")
    expect(card.get_by_role("heading")).to_have_text("Inspect motor")
    assert api.get("/api/orders/1").json() == {
        **stored.json(), "title": "Inspect motor", "description": "Updated inspection",
    }
    workspace.page.get_by_role("button", name="Sign out").click()
    expect(workspace.feedback).to_have_text("Signed out.")
    expect(workspace.workspace).to_be_hidden()
    expect(workspace.page.get_by_role("heading", name="Sign in")).to_be_visible()
    workspace.page.reload()
    expect(workspace.workspace).to_be_hidden()
    expect(workspace.page.get_by_role("heading", name="Sign in")).to_be_visible()


@pytest.mark.regression
@pytest.mark.parametrize("field", ["title", "description"])
def test_required_field_blocks_submission(
    workspace: WorkOrdersPage, api: APIRequestContext, field: str
) -> None:
    workspace.create(
        "" if field == "title" else "Inspection",
        "" if field == "description" else "Synthetic work",
    )
    invalid = workspace.page.get_by_label(field.capitalize(), exact=True)
    assert invalid.evaluate("(element) => element.validity.valueMissing") is True
    expect(workspace.cards).to_have_count(0)
    response = api.get("/api/orders")
    assert response.status == 200
    assert response.json() == []


@pytest.mark.regression
@pytest.mark.parametrize("field", ["title", "description"])
def test_whitespace_input_shows_server_error(
    workspace: WorkOrdersPage, api: APIRequestContext, field: str
) -> None:
    workspace.create(
        "   " if field == "title" else "Inspection",
        "   " if field == "description" else "Synthetic work",
    )
    expect(workspace.error).to_have_text("Invalid request")
    expect(workspace.cards).to_have_count(0)
    response = api.get("/api/orders")
    assert response.status == 200
    assert response.json() == []


@pytest.mark.regression
def test_filter_status_and_empty_state(
    workspace: WorkOrdersPage, api: APIRequestContext
) -> None:
    workspace.create("Pending inspection", "First order")
    expect(workspace.feedback).to_have_text("Order 1 created.")
    workspace.create("Completed inspection", "Second order")
    expect(workspace.feedback).to_have_text("Order 2 created.")
    card = workspace.card(2)
    card.get_by_role("button", name="Start work").click()
    expect(card.locator(".order-status")).to_have_text("In Progress")
    card.get_by_role("button", name="Complete work").click()
    expect(card.locator(".order-status")).to_have_text("Completed")
    expect(card.get_by_role("button")).to_have_count(0)
    assert api.get("/api/orders/2").json()["status"] == "Completed"

    workspace.filter_status("Pending")
    expect(workspace.cards).to_have_count(1)
    expect(workspace.card(1)).to_be_visible()
    workspace.filter_status("Completed")
    expect(workspace.cards).to_have_count(1)
    expect(workspace.card(2)).to_be_visible()
    workspace.filter_status("In Progress")
    expect(workspace.cards).to_have_count(0)
    expect(workspace.page.locator("#empty")).to_be_visible()
    workspace.filter_status("")
    expect(workspace.cards).to_have_count(2)
    expect(workspace.page.locator("#empty")).to_be_hidden()


@pytest.mark.regression
def test_user_text_is_not_interpreted_as_markup(
    workspace: WorkOrdersPage, api: APIRequestContext
) -> None:
    title = "<strong>Plain title</strong>"
    description = "<em>Plain description</em>"
    workspace.create(title, description)
    expect(workspace.feedback).to_have_text("Order 1 created.")
    card = workspace.card(1)
    expect(card.get_by_role("heading")).to_have_text(title)
    expect(card.locator("p").nth(1)).to_have_text(description)
    expect(card.locator("strong, em")).to_have_count(0)
    stored = api.get("/api/orders/1")
    assert stored.status == 200
    assert stored.json()["title"] == title
    assert stored.json()["description"] == description
