from typing import Any, AsyncGenerator

from src.middlewares.auth import auth_middleware
from src.middlewares.compression import compression_middleware
from src.middlewares.rewrite import rewrite_shop_path
from yarl import URL

from aiorp import HTTPProxyHandler, MiddlewarePhase, ProxyContext, ProxyMiddlewareDef

TRANSACTIONS_API_KEY = "transactions-secret-key-123"
TRANSACTIONS_URL = URL("http://localhost:8001")

transactions_ctx = ProxyContext(url=TRANSACTIONS_URL)
transactions_handler = HTTPProxyHandler(context=transactions_ctx)

transactions_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.CLIENT_EDGE, auth_middleware)
)
transactions_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.PROXY, rewrite_shop_path)
)
transactions_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.TARGET_EDGE, compression_middleware)
)


@transactions_handler.proxy
async def transactions_auth(ctx) -> AsyncGenerator[None, Any]:
    """Add transactions API key to requests"""
    ctx.request.headers["X-API-Key"] = TRANSACTIONS_API_KEY
    yield
