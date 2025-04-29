import json

from aiorp.context import ProxyContext


async def modify_request(ctx: ProxyContext):
    ctx.request.headers["X-Request-Added-Header"] = "Value"
    ctx.request.params["added_param"] = "I am added"
    yield


async def modify_response(ctx: ProxyContext):
    yield
    await ctx.response.set_response()
    ctx.response.web.headers["X-Response-Added-Header"] = "Value"
    data = json.loads(ctx.response.web.body)
    data["new_field"] = 1234567890
    ctx.response.web.body = json.dumps(data).encode("utf-8")
    ctx.response.web.headers["Content-Length"] = f"{len(ctx.response.web.body)}"
