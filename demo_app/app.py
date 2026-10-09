"""Minimal work-order application. Not production authentication or deployment."""

from __future__ import annotations

import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Generator, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, StringConstraints

from demo_app.observability import EventLog, RequestLogMiddleware
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo-password"
SESSION_COOKIE = "demo_session"
Status = Literal["Pending", "In Progress", "Completed"]
NonblankText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class LoginInput(BaseModel):
    username: str
    password: str


class OrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: NonblankText
    description: NonblankText
    customer_id: int


class OrderEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: NonblankText
    description: NonblankText


class StatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Status


class Order(BaseModel):
    id: int
    title: str
    description: str
    customer_id: int
    status: Status


class Customer(BaseModel):
    id: int
    name: str


def create_app(
    database_path: Path, events: EventLog | None = None, *,
    allow_pending_completion_defect: bool = False,
) -> FastAPI:
    """Create an app backed by a caller-owned database, never a shared default."""

    @contextmanager
    def database() -> Generator[sqlite3.Connection]:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    with database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                customer_id INTEGER NOT NULL,
                status TEXT NOT NULL
            );
            INSERT OR IGNORE INTO customers VALUES (1, 'Demo Workshop');
            INSERT OR IGNORE INTO customers VALUES (2, 'Sample Services');
            """
        )

    app = FastAPI(title="Synthetic Work Order Demo")
    if events is not None:
        app.add_middleware(RequestLogMiddleware, events=events)
    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, error: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"message": str(error.detail)}},
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_input(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        # Do not copy request bodies (including credentials) into errors.
        issues = [
            {"field": ".".join(map(str, item["loc"])), "message": item["msg"]}
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"error": {"message": "Invalid request", "issues": issues}},
        )

    def authenticated(request: Request) -> None:
        token = request.cookies.get(SESSION_COOKIE)
        with database() as connection:
            session = connection.execute(
                "SELECT token FROM sessions WHERE token = ?", (token,)
            ).fetchone()
        if session is None:
            raise HTTPException(401, "Login required")

    protected = [Depends(authenticated)]

    def read_order(connection: sqlite3.Connection, order_id: int) -> Order:
        row = connection.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Work order not found")
        return Order.model_validate(dict(row))

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(static / "index.html")

    @app.get("/health")
    def health() -> dict[str, str]:
        with database() as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "ok"}

    @app.post("/api/login")
    def login(payload: LoginInput, request: Request, response: Response) -> dict[str, str]:
        if (
            payload.username != DEMO_USERNAME
            or payload.password != DEMO_PASSWORD
        ):
            raise HTTPException(401, "Invalid credentials")
        token = secrets.token_urlsafe(32)
        with database() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token = ?",
                (request.cookies.get(SESSION_COOKIE),),
            )
            connection.execute("INSERT INTO sessions VALUES (?)", (token,))
        response.set_cookie(
            SESSION_COOKIE, token, httponly=True, samesite="strict"
        )
        return {"username": DEMO_USERNAME}

    @app.post("/api/logout", status_code=204, dependencies=protected)
    def logout(request: Request) -> Response:
        with database() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token = ?",
                (request.cookies.get(SESSION_COOKIE),),
            )
        response = Response(status_code=204)
        response.delete_cookie(SESSION_COOKIE)
        return response

    @app.get("/api/customers", dependencies=protected)
    def customers() -> list[Customer]:
        with database() as connection:
            rows = connection.execute("SELECT * FROM customers ORDER BY id").fetchall()
        return [Customer.model_validate(dict(row)) for row in rows]

    @app.post("/api/orders", status_code=201, dependencies=protected)
    def create_order(payload: OrderInput) -> Order:
        with database() as connection:
            if connection.execute(
                "SELECT id FROM customers WHERE id = ?", (payload.customer_id,)
            ).fetchone() is None:
                raise HTTPException(422, "Unknown customer")
            cursor = connection.execute(
                """INSERT INTO orders (title, description, customer_id, status)
                   VALUES (?, ?, ?, 'Pending')""",
                (payload.title, payload.description, payload.customer_id),
            )
            assert cursor.lastrowid is not None
            return read_order(connection, cursor.lastrowid)

    @app.get("/api/orders", dependencies=protected)
    def list_orders(status: Status | None = None) -> list[Order]:
        with database() as connection:
            if status is None:
                rows = connection.execute("SELECT * FROM orders ORDER BY id").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM orders WHERE status = ? ORDER BY id", (status,)
                ).fetchall()
        return [Order.model_validate(dict(row)) for row in rows]

    @app.get("/api/orders/{order_id}", dependencies=protected)
    def get_order(order_id: int) -> Order:
        with database() as connection:
            return read_order(connection, order_id)

    @app.patch("/api/orders/{order_id}", dependencies=protected)
    def edit_order(order_id: int, payload: OrderEdit) -> Order:
        with database() as connection:
            connection.execute("BEGIN IMMEDIATE")
            order = read_order(connection, order_id)
            if order.status == "Completed":
                raise HTTPException(409, "Completed orders cannot be edited")
            connection.execute(
                "UPDATE orders SET title = ?, description = ? WHERE id = ?",
                (payload.title, payload.description, order_id),
            )
            return read_order(connection, order_id)

    @app.patch("/api/orders/{order_id}/status", dependencies=protected)
    def change_status(order_id: int, payload: StatusInput) -> Order:
        transitions = {"Pending": "In Progress", "In Progress": "Completed"}
        with database() as connection:
            connection.execute("BEGIN IMMEDIATE")
            order = read_order(connection, order_id)
            injected_skip = (
                allow_pending_completion_defect
                and order.status == "Pending"
                and payload.status == "Completed"
            )
            if transitions.get(order.status) != payload.status and not injected_skip:
                raise HTTPException(409, "Invalid status transition")
            connection.execute(
                "UPDATE orders SET status = ? WHERE id = ?", (payload.status, order_id)
            )
            return read_order(connection, order_id)

    return app
