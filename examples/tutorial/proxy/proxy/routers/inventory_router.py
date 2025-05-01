from typing import Any, AsyncGenerator

from aiohttp import web
from proxy.utils.auth import auth_middleware
from proxy.utils.compression import compression_middleware
from yarl import URL

from aiorp import HTTPProxyHandler, MiddlewarePhase, ProxyContext, ProxyMiddlewareDef

# API key for inventory service
INVENTORY_API_KEY = "inventory-secret-key-456"
INVENTORY_URL = URL("http://localhost:8002")

# Create route table
routes = web.RouteTableDef()

# Create proxy context and handler
inventory_ctx = ProxyContext(url=INVENTORY_URL)
inventory_handler = HTTPProxyHandler(context=inventory_ctx)


# Add authentication middleware for inventory
@inventory_handler.default
async def inventory(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    """Add inventory API key to requests"""
    user = ctx.state["user"]
    shop_id = ctx.request.in_req.match_info["shop_id"]

    if user["user_id"] != shop_id:
        raise web.HTTPForbidden()

    ctx.request.headers["X-API-Key"] = INVENTORY_API_KEY
    yield


# Add main application authentication middleware
inventory_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.EARLY, auth_middleware)
)

# Add compression middleware
inventory_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.LATE, compression_middleware)
)


# Define routes
@routes.route("*", "/shops/{shop_id:[A-Za-z0-9]+}/inventory{tail:.*}")
async def inventory_proxy(request):
    """Proxy all inventory requests"""
    return await inventory_handler(request)
