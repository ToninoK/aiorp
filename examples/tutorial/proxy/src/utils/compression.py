import gzip
from typing import Any, AsyncGenerator

from aiohttp import web

from aiorp.context import ProxyContext


async def compression_middleware(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    """Middleware to compress responses before sending to client"""
    # Let the request go through first
    yield

    # Check if client accepts gzip encoding
    accept_encoding = ctx.request.in_req.headers.get("Accept-Encoding", "")

    if "gzip" not in accept_encoding.lower():
        return

    if not ctx.response.web_response_set:
        await ctx.response.set_response()

    # Get the response content
    if hasattr(ctx.response.web, "body"):
        content = ctx.response.web.body
    else:
        # For streaming responses, we can't compress
        return
    # Only compress if content is large enough to benefit from compression
    if len(content) < 1024:  # Less than 1KB
        return

    # Compress the content
    compressed = gzip.compress(content)

    # Create new response with compressed content
    new_response = web.Response(
        body=compressed,
        status=ctx.response.web.status,
        headers=ctx.response.web.headers,
    )

    # Set compression headers
    new_response.headers["Content-Encoding"] = "gzip"
    new_response.headers["Content-Length"] = str(len(compressed))
    # Update the response
    ctx.response._web = new_response
