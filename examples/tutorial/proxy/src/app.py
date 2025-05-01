from aiohttp import web
from src.routers.inventory_router import inventory_ctx
from src.routers.inventory_router import routes as inventory_routes
from src.routers.transactions_router import routes as transactions_routes
from src.routers.transactions_router import transactions_ctx
from src.utils.auth import login_handler

from aiorp import configure_contexts

# Create route table
routes = web.RouteTableDef()


# Define routes
@routes.post("/login")
async def login(request):
    """Handle user login"""
    return await login_handler(request)


def create_app() -> web.Application:
    """Create and configure the application"""
    app = web.Application()

    # Configure aiorp contexts
    configure_contexts(app, [transactions_ctx, inventory_ctx])

    # Add routes
    app.add_routes(routes)

    # Setup routers
    app.add_routes(transactions_routes)
    app.add_routes(inventory_routes)

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="localhost", port=8080)
