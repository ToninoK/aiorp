import pytest
from aiohttp import ClientSession, web


def ping(request: web.Request) -> web.Response:
    return web.Response(text="pong")


def yell_path(request: web.Request) -> web.Response:
    return web.Response(text=f"{request.path}!!!")


@pytest.fixture
async def simple_server(aiohttp_server):
    app = web.Application()
    app.router.add_get("/", ping)
    app.router.add_get("/first", yell_path)
    app.router.add_get("/second", yell_path)
    return await aiohttp_server(app)


@pytest.fixture
async def http_client():
    session = ClientSession()
    yield session
    await session.close()
