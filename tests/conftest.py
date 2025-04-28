import pytest
import yarl
from aiohttp import web

from aiorp.context import ProxyContext
from aiorp.http_handler import HTTPProxyHandler
from aiorp.ws_handler import WsProxyHandler
from tests.utils.target import app as target_app
from tests.utils.ws_target import app as ws_target_app


@pytest.fixture
async def target_ctx(aiohttp_server):
    server = await aiohttp_server(target_app())
    url = yarl.URL(f"http://localhost:{server.port}")
    context = ProxyContext(url=url)
    yield context

    await context.close_session()


@pytest.fixture
async def ws_target_ctx(aiohttp_server):
    server = await aiohttp_server(ws_target_app())
    url = yarl.URL(f"http://localhost:{server.port}")
    context = ProxyContext(url=url)
    yield context

    await context.close_session()


@pytest.fixture
def proxy_server(aiohttp_server, target_ctx, ws_target_ctx):
    async def proxy_server_setup(**kwargs):
        application = web.Application()

        http_handler = HTTPProxyHandler(context=target_ctx, **kwargs)
        ws_handler = WsProxyHandler(context=ws_target_ctx, **kwargs)

        application.add_routes(
            [
                web.get("/http", http_handler),
                web.post("/http", http_handler),
                web.get("/ws", ws_handler),
            ]
        )

        return await aiohttp_server(application)

    return proxy_server_setup
