import logging

from aiohttp import web
from yarl import URL

from proxy.context import ProxyContext
from proxy.handler import Priority, ProxyHandler
from proxy.request import ProxyRequest
from proxy.response import ProxyResponse

pokeapi_context = ProxyContext(
    url=URL("https://pokeapi.co"), attributes={"target": "pokeapi"}
)

handler = ProxyHandler(
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


@handler.after()
async def process_1(response: ProxyResponse):
    log.info("I execute third")


async def manual_process_3(response: ProxyResponse):
    log.info("I execute third also asynchronously")


@handler.after(priority=Priority.HIGH)
async def process_2(response: ProxyResponse):
    log.info("I execute fourth")


async def on_shutdown(app):
    await pokeapi_context.close_session()


application = web.Application()

handler.add_after(priority=Priority.HIGHEST, func=manual_process_3)
handler_routes = [
    web.get("/pokapi/pokemon/{name}", handler),
]

application.router.add_routes(handler_routes)
application.on_cleanup.append(on_shutdown)

logging.basicConfig(level=logging.DEBUG)

web.run_app(application)
