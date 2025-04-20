import pytest
from aiohttp import ClientSession, web


def ping(request: web.Request) -> web.Response:
    return web.Response(text="pong")


@pytest.fixture
async def simple_server(aiohttp_server):
    app = web.Application()
    app.router.add_get("/", ping)
    return await aiohttp_server(app)


@pytest.fixture
async def http_client():
    session = ClientSession()
    yield session
    await session.close()
