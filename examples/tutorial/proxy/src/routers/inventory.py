from typing import Any, AsyncGenerator

from src.middlewares.auth import auth_middleware
from src.middlewares.compression import compression_middleware
from src.middlewares.rewrite import rewrite_shop_path
from yarl import URL

from aiorp import HTTPProxyHandler, MiddlewarePhase, ProxyContext, ProxyMiddlewareDef

INVENTORY_API_KEY = "inventory-secret-key-456"
INVENTORY_URL = URL("http://localhost:8002")

inventory_ctx = ProxyContext(url=INVENTORY_URL)
inventory_handler = HTTPProxyHandler(context=inventory_ctx)


inventory_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.CLIENT_EDGE, auth_middleware)
)
inventory_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.PROXY, rewrite_shop_path)
)
inventory_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.CLIENT_EDGE, compression_middleware)
)


@inventory_handler.proxy
async def inventory(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    """Add inventory API key to requests"""
    ctx.request.headers["X-API-Key"] = INVENTORY_API_KEY
    yield
