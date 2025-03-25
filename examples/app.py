import logging

from aiohttp import web
from yarl import URL

from aiorp.context import ProxyContext
from aiorp.http_handler import HttpProxyHandler
from aiorp.response import ResponseType

pokeapi_context = ProxyContext(
    url=URL("https://pokeapi.co"), state={"target": "pokeapi"}
)

handler = HttpProxyHandler(
    pokeapi_context,
    rewrite_from="/pokapi",
    rewrite_to="/api/v2",
)

log = logging.getLogger(__name__)


@handler.early
async def proxy_middleware1(context: ProxyContext):
    # Do request processing here
    log.info("Early middleware: Starting pre-processing")
    yield
    log.info("Early middleware: Starting post-processing")
    await context.response.set_response(ResponseType.BASE)
    log.info(context.response.web.status)


@handler.standard
async def proxy_middleware2(context: ProxyContext):
    # Do request processing here
    log.info("Standard middleware: Starting pre-processing")
    yield
    # Do response processing here
    log.info("Standard middleware: Starting post-processing")


async def on_shutdown(app):
    await pokeapi_context.close_session()


application = web.Application()

handler_routes = [
    web.get("/pokapi/pokemon/{name}", handler),
]

application.router.add_routes(handler_routes)
application.on_cleanup.append(on_shutdown)

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

web.run_app(application)
