import yarl
from aiohttp import web

from aiorp import ProxyContext, Rewrite, WsProxyHandler, configure_contexts

ctx = ProxyContext(url=yarl.URL("http://localhost:8181"))
handler = WsProxyHandler(context=ctx, rewrite=Rewrite(rfrom="/ws", rto="/"))

app = web.Application()
configure_contexts(app, [ctx])

app.add_routes([web.get("/ws", handler)])

web.run_app(app)
