import logging

from aiohttp import web
from yarl import URL
from proxy.handler import ProxyHandler
from proxy.options import ProxyOptions
from proxy.request import ProxyRequest
from proxy.response import ProxyResponse, ResponseType

proxy_options = ProxyOptions(url=URL("https://pokeapi.co"), attributes={})

handler = ProxyHandler(proxy_options, rewrite_from="/pokapi", rewrite_to="/api/v2")

log = logging.getLogger(__name__)

@handler.before()
async def prepare(request: ProxyRequest):
    log.info(request.headers)


@handler.after()
async def process(response: ProxyResponse):
    log.info(response.response.headers)


async def on_shutdown(app):
    await proxy_options.close_session()

app = web.Application()
handler_routes = [
    web.get('/pokapi/pokemon/{name}', handler),
]
app.router.add_routes(handler_routes)
app.on_cleanup.append(on_shutdown)
logging.basicConfig(level=logging.DEBUG)

web.run_app(app)
