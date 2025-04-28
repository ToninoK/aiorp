import pytest
import yarl
from aiohttp import WSMsgType, web

from aiorp.context import ProxyContext


async def ping(request: web.Request) -> web.Response:
    return web.Response(text="pong")


async def yell_path(request: web.Request) -> web.Response:
    return web.Response(text=f"{request.path}!!!")


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            if msg.data == "close":
                await ws.close()
                break
            if msg.data == "error":
                raise Exception("Target error")
            await ws.send_str(f"received: {msg.data}")
        elif msg.type == WSMsgType.BINARY:
            await ws.send_bytes(f"received: {msg.data}".encode())
        elif msg.type == WSMsgType.PING:
            await ws.pong()
        elif msg.type == WSMsgType.ERROR:
            if exc := ws.exception():
                raise exc
    return ws


@pytest.fixture
async def target_ctx(aiohttp_server):
    app = web.Application()
    app.router.add_get("/", ping)
    app.router.add_get("/yell_path", yell_path)
    app.router.add_get("/ws", ws_handler)
    server = await aiohttp_server(app)

    url = yarl.URL(f"http://localhost:{server.port}")
    context = ProxyContext(url=url)

    yield context

    await context.close_session()
