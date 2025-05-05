import gzip
from typing import Any, AsyncGenerator

from aiohttp import web

from aiorp.context import ProxyContext


async def compression_middleware(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    """Middleware to compress responses before sending to client"""
    yield

    accept_encoding = ctx.request.in_req.headers.get("Accept-Encoding", "")

    if "gzip" not in accept_encoding.lower():
        return

    if not ctx.response.web_response_set:
        await ctx.response.set_response()

    if ctx.response.web is web.StreamResponse:
        return

    content = ctx.response.web.body

    compressed = gzip.compress(content)

    new_response = web.Response(
        body=compressed,
        status=ctx.response.web.status,
        headers=ctx.response.web.headers,
    )

    new_response.headers["Content-Encoding"] = "gzip"
    new_response.headers["Content-Length"] = str(len(compressed))
    ctx.response._web = new_response
