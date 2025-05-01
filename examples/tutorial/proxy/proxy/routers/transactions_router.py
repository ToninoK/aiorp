from typing import Any, AsyncGenerator

from aiohttp import web
from proxy.utils.auth import auth_middleware
from proxy.utils.compression import compression_middleware
from yarl import URL

from aiorp import HTTPProxyHandler, MiddlewarePhase, ProxyContext, ProxyMiddlewareDef

# API key for transactions service
TRANSACTIONS_API_KEY = "transactions-secret-key-123"
TRANSACTIONS_URL = URL("http://localhost:8001")

# Create route table
routes = web.RouteTableDef()

# Create proxy context and handler
transactions_ctx = ProxyContext(url=TRANSACTIONS_URL)
transactions_handler = HTTPProxyHandler(context=transactions_ctx)


# Add authentication middleware for transactions
@transactions_handler.default
async def transactions_auth(ctx) -> AsyncGenerator[None, Any]:
    """Add transactions API key to requests"""
    ctx.request.headers["X-API-Key"] = TRANSACTIONS_API_KEY
    yield


# Add main application authentication middleware
transactions_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.EARLY, auth_middleware)
)

# Add compression middleware
transactions_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.LATE, compression_middleware)
)


# Define routes
@routes.route("*", "/transactions{tail:.*}")
async def transactions_proxy(request):
    """Proxy all transactions requests"""
    return await transactions_handler(request)
