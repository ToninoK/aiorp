import logging

from aiohttp import web
from yarl import URL

from aiorp.context import ProxyContext
from aiorp.http_handler import HttpProxyHandler, Priority
from aiorp.request import ProxyRequest

pokeapi_context = ProxyContext(
    url=URL("https://pokeapi.co"), attributes={"target": "pokeapi"}
)

handler = HttpProxyHandler(
    pokeapi_context,
    rewrite_from="/pokapi",
    rewrite_to="/api/v2",
)

log = logging.getLogger(__name__)


@handler.before(priority=Priority.HIGHEST)
async def prepare_1(request: ProxyRequest):
    log.info("I execute first")
    log.info(f"Target: {request.proxy_attributes['target']}")


@handler.before(priority=Priority.HIGH)
async def prepare_2(request: ProxyRequest):
    log.info("I execute second")


async def on_shutdown(app):
    await pokeapi_context.close_session()


application = web.Application()

handler_routes = [
    web.get("/pokapi/pokemon/{name}", handler),
]

application.router.add_routes(handler_routes)
application.on_cleanup.append(on_shutdown)

logging.basicConfig(level=logging.DEBUG)

web.run_app(application)
