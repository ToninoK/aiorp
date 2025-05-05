from posixpath import join
from typing import Any, AsyncGenerator

from aiorp import ProxyContext


async def rewrite_shop_path(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    user = ctx.state["user"]
    new_path = join(f"/shops/{user['user_id']}", ctx.request.url.path.lstrip("/"))
    ctx.request.url = ctx.request.url.with_path(new_path)
    yield
