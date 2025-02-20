from aiohttp import web
from yarl import URL
from proxy.handler import ProxyHandler
from proxy.options import ProxyOptions
from proxy.request import ProxyRequest
from proxy.response import ProxyResponse


proxy_options = ProxyOptions(url=URL("https://pokeapi.co"), attributes={})

handler = ProxyHandler(proxy_options, rewrite_from="/pokapi", rewrite_to="/api/v2")

@handler.before()
def prepare(request: ProxyRequest):
    print('Modify request')

@handler.after()
def process(response: ProxyResponse):
    print('Modify response')


async def on_shutdown(app):
    await handler.close_session()

app = web.Application()
handler_routes = [
    web.get('/pokapi/pokemon/{name}', handler),
]
app.router.add_routes(handler_routes)
app.on_cleanup.append(on_shutdown)

web.run_app(app)
