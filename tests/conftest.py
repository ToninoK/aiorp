import pytest
from aiohttp import ClientSession, web


async def ping(request: web.Request) -> web.Response:
    return web.Response(text="pong")


async def yell_path(request: web.Request) -> web.Response:
    return web.Response(text=f"{request.path}!!!")


@pytest.fixture
async def simple_server(aiohttp_server):
    app = web.Application()
    app.router.add_get("/", ping)
    app.router.add_get("/yell_path", yell_path)
    return await aiohttp_server(app)


@pytest.fixture
async def http_client():
    session = ClientSession()
    yield session
    await session.close()
