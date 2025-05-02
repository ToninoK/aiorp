from aiohttp import web
from src.routers.inventory_router import inventory_ctx
from src.routers.inventory_router import routes as inventory_routes
from src.routers.transactions_router import routes as transactions_routes
from src.routers.transactions_router import transactions_ctx
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

    configure_contexts(app, [transactions_ctx, inventory_ctx])

    app.router.add_post("/login", login)

    app.add_routes(transactions_routes)
    app.add_routes(inventory_routes)

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="localhost", port=8080)
