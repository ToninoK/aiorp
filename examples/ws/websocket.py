import yarl
from aiohttp import web

from aiorp.base_handler import Rewrite
from aiorp.context import ProxyContext
from aiorp.ws_handler import WsProxyHandler

ctx = ProxyContext(url=yarl.URL("http://localhost:8181"))
handler = WsProxyHandler(context=ctx, rewrite=Rewrite(rfrom="/ws", rto="/"))

app = web.Application()


async def on_shutdown(app):
    await ctx.close_session()


app.on_shutdown.append(on_shutdown)
app.add_routes([web.get("/ws", handler)])

web.run_app(app)
