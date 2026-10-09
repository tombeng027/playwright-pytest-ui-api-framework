from playwright.sync_api import Locator, Page


class WorkOrdersPage:
    """Interactions only; scenario assertions stay in the tests."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.workspace = page.locator("#workspace")
        self.error = page.get_by_role("alert")
        self.feedback = page.get_by_role("status")
        self.cards = page.locator("#orders article")

    def login(self, username: str = "demo", password: str = "demo-password") -> None:
        self.page.get_by_label("Username", exact=True).fill(username)
        self.page.get_by_label("Password", exact=True).fill(password)
        self.page.get_by_role("button", name="Sign in", exact=True).click()

    def create(self, title: str, description: str, customer: str = "1") -> None:
        self.page.get_by_label("Title", exact=True).fill(title)
        self.page.get_by_label("Description", exact=True).fill(description)
        self.page.get_by_label("Customer", exact=True).select_option(customer)
        self.page.get_by_role("button", name="Create order", exact=True).click()

    def card(self, order_id: int) -> Locator:
        return self.page.locator(f'article[data-order-id="{order_id}"]')

    def edit(self, order_id: int, title: str, description: str) -> None:
        card = self.card(order_id)
        card.get_by_label("Edit title", exact=True).fill(title)
        card.get_by_label("Edit description", exact=True).fill(description)
        card.get_by_role("button", name="Save changes", exact=True).click()

    def filter_status(self, status: str) -> None:
        with self.page.expect_response(
            lambda response: "/api/orders" in response.url
            and response.request.method == "GET"
        ):
            self.page.get_by_label("Filter by status").select_option(status)
