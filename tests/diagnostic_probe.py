"""Explicit-only failing probe; filename is excluded from default discovery."""

import pytest
from playwright.sync_api import Page, expect

from tests.ui.work_orders_page import WorkOrdersPage


@pytest.mark.regression
def test_intentional_browser_failure(page: Page, app_url: str) -> None:
    page.goto(app_url)
    screen = WorkOrdersPage(page)
    screen.login()
    expect(screen.workspace).to_be_visible()
    screen.create("Diagnostic inspection", "Synthetic diagnostic evidence")
    expect(screen.feedback).to_have_text("Order 1 created.")
    page.evaluate("console.error('PRIVATE_CONSOLE_SENTINEL')")
    with page.expect_event("pageerror"):
        page.evaluate(
            "setTimeout(() => { throw new Error('PRIVATE_PAGE_ERROR_SENTINEL'); }, 0)"
        )
    with page.expect_event("requestfailed"):
        page.route("**/diagnostic-network", lambda route: route.abort())
        page.evaluate("fetch('/diagnostic-network').catch(() => {})")
    expect(screen.card(1).locator(".order-status")).to_have_text(
        "INTENTIONAL_FAILURE_EXPECTED", timeout=1000
    )
