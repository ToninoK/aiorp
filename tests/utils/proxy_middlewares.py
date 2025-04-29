import json

from aiorp.context import ProxyContext

RESPONSE_MODIFIED_VALUE = 1234567890


async def modify_request(ctx: ProxyContext):
    ctx.request.headers["X-Request-Added-Header"] = "Value"
    ctx.request.params["added_param"] = "I am added"
    await ctx.request.load_content()
    if ctx.request.content:
        data = json.loads(ctx.request.content)
        data["new_field"] = "some new field"
        ctx.request.content = json.dumps(data).encode("utf-8")
        ctx.request.headers["Content-Length"] = str(len(ctx.request.content))
    yield


async def modify_response(ctx: ProxyContext):
    yield
    await ctx.response.set_response()
    ctx.response.web.headers["X-Response-Added-Header"] = "Value"
    if ctx.response.web.body:
        data = json.loads(ctx.response.web.body)
        data["new_field"] = 1234567890
        ctx.response.web.body = json.dumps(data).encode("utf-8")
        ctx.response.web.headers["Content-Length"] = f"{len(ctx.response.web.body)}"


async def modify_both(ctx: ProxyContext):
    ctx.request.headers["X-Request-Added-Header"] = "Value"
    ctx.request.params["added_param"] = "I am added"
    await ctx.request.load_content()
    if ctx.request.content is not None:
        data = json.loads(ctx.request.content)
        data["new_field"] = "some new field"
        ctx.request.content = json.dumps(data).encode("utf-8")
        ctx.request.headers["Content-Length"] = str(len(ctx.request.content))

    yield

    await ctx.response.set_response()
    ctx.response.web.headers["X-Response-Added-Header"] = "Value"
    if ctx.response.web.body:
        data = json.loads(ctx.response.web.body)
        data["new_field"] = RESPONSE_MODIFIED_VALUE
        ctx.response.web.body = json.dumps(data).encode("utf-8")
        ctx.response.web.headers["Content-Length"] = f"{len(ctx.response.web.body)}"
