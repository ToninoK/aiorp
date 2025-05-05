from typing import Any, AsyncGenerator

from aiohttp import web
from src.utils.auth import auth_middleware
from src.utils.compression import compression_middleware
from yarl import URL

from aiorp import HTTPProxyHandler, MiddlewarePhase, ProxyContext, ProxyMiddlewareDef

# API key for transactions service
TRANSACTIONS_API_KEY = "transactions-secret-key-123"
TRANSACTIONS_URL = URL("http://localhost:8001")

# Create route table
routes = web.RouteTableDef()

# Create src.context and handler
transactions_ctx = ProxyContext(url=TRANSACTIONS_URL)
transactions_handler = HTTPProxyHandler(context=transactions_ctx)


# Add authentication middleware for transactions
@transactions_handler.proxy
async def transactions_auth(ctx) -> AsyncGenerator[None, Any]:
    """Add transactions API key to requests"""
    user = ctx.state["user"]
    shop_id = ctx.request.in_req.match_info["shop_id"]

    if user["user_id"] != shop_id:
        raise web.HTTPForbidden()

    ctx.request.headers["X-API-Key"] = TRANSACTIONS_API_KEY
    yield


# Add main application authentication middleware
transactions_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.CLIENT_EDGE, auth_middleware)
)

# Add compression middleware
transactions_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.TARGET_EDGE, compression_middleware)
)


# Define routes
@routes.route("*", "/shops/{shop_id:.*}/transactions{tail:.*}")
async def transactions_proxy(request):
    """Proxy all transactions requests"""
    return await transactions_handler(request)
