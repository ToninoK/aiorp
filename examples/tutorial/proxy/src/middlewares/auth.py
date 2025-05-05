from typing import Any, AsyncGenerator

from aiohttp import web
from src.utils.auth import verify_token

from aiorp import ProxyContext


async def auth_middleware(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    """Middleware to handle authentication for proxy requests"""
    auth_header = ctx.request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise web.HTTPUnauthorized(reason="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)
        if ctx.state is None:
            ctx.state = {}
        ctx.state["user"] = payload
        yield
    except web.HTTPUnauthorized as e:
        raise e
    except Exception as e:
        raise web.HTTPUnauthorized(reason=str(e))
