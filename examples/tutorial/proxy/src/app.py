from aiohttp import web
from src.routers import (
    inventory_ctx,
    inventory_handler,
    transactions_ctx,
    transactions_handler,
)
from src.utils.auth import USERS, create_token

from aiorp import configure_contexts


async def login(request):
    """Handle user login"""
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise web.HTTPBadRequest(reason="Username and password are required")

    user = USERS.get(username)
    if not user or user["password"] != password:
        raise web.HTTPUnauthorized(reason="Invalid username or password")

    token = create_token(username)
    return web.json_response(
        {"token": token, "user": {"username": username, "role": user["role"]}}
    )


def create_app() -> web.Application:
    """Create and configure the application"""
    app = web.Application()

    configure_contexts(app, [inventory_ctx, transactions_ctx])

    app.router.add_post("/login", login)
    app.router.add_route("*", "/transactions{tail:.*}", transactions_handler)
    app.router.add_route("*", "/inventory{tail:.*}", inventory_handler)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="localhost", port=8080)
