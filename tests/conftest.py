import pytest
from aiohttp import web


def ping(request: web.Request) -> web.Response:
    return web.Response(text="pong")


@pytest.fixture
async def simple_server(aiohttp_server):
    app = web.Application()
    app.router.add_get("/", ping)
    return await aiohttp_server(app)
