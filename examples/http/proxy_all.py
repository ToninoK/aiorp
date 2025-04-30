from aiohttp import web
from yarl import URL

from aiorp import HTTPProxyHandler, ProxyContext, configure_contexts

POKEAPI_URL = URL("https://pokeapi.co")

app = web.Application()

pokeapi_ctx = ProxyContext(POKEAPI_URL)
pokeapi_handler = HTTPProxyHandler(context=pokeapi_ctx)

configure_contexts(app, [pokeapi_ctx])

app.router.add_get("/{path:.*}", pokeapi_handler)

web.run_app(app, host="0.0.0.0", port=8000)
