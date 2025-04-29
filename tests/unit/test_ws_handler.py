import pytest
from aiohttp import WSCloseCode, WSMsgType, web
from aiohttp.test_utils import make_mocked_request

from aiorp.base_handler import Rewrite
from aiorp.ws_handler import WsProxyHandler

pytestmark = [pytest.mark.websocket_handler]


def _proxy_app(**kwargs):
    app = web.Application()
    ws_handler = WsProxyHandler(**kwargs)
    app.router.add_get("/", ws_handler)
    app.router.add_get("/sw", ws_handler)

    return app


def test_ws_handler_init_invalid_req_options():
    req_options = {
        "url": "https://somerandom.url.com",
    }
    with pytest.raises(ValueError):
        WsProxyHandler(request_options=req_options)


@pytest.mark.asyncio
async def test_ws_handler_call_no_ctx():
    handler = WsProxyHandler(context=None)
    req = make_mocked_request(method="GET", path="/")
    with pytest.raises(ValueError):
        await handler(req)


@pytest.mark.asyncio
async def test_ws_handler_call(aiohttp_client, ws_target_ctx):
    app = _proxy_app(context=ws_target_ctx)
    client = await aiohttp_client(app)

    async with client.ws_connect("/") as ws:
        await ws.send_str("test")
        msg = await ws.receive()
        await ws.close()

    assert msg.type == WSMsgType.TEXT
    assert msg.data == "received: test"


@pytest.mark.asyncio
async def test_ws_handler_call_with_rewrite(aiohttp_client, ws_target_ctx):
    app = _proxy_app(context=ws_target_ctx, rewrite=Rewrite(rfrom="/sw", rto=""))
    client = await aiohttp_client(app)

    async with client.ws_connect("/sw") as ws:
        await ws.send_str("test")
        msg = await ws.receive()
        await ws.close()

    assert msg.type == WSMsgType.TEXT
    assert msg.data == "received: test"


@pytest.mark.asyncio
async def test_ws_handler_call_timeout(aiohttp_client, ws_target_ctx):
    app = _proxy_app(context=ws_target_ctx, receive_timeout=0.1)
    client = await aiohttp_client(app)

    async with client.ws_connect("/") as ws:
        msg = await ws.receive()
        await ws.close()

    assert msg.type == WSMsgType.CLOSE
    assert msg.data == WSCloseCode.GOING_AWAY


@pytest.mark.asyncio
async def test_ws_handler_target_closed(aiohttp_client, ws_target_ctx):
    app = _proxy_app(context=ws_target_ctx)
    client = await aiohttp_client(app)

    async with client.ws_connect("/") as ws:
        await ws.send_str("close")
        msg = await ws.receive()

    assert msg.type == WSMsgType.CLOSE
    assert msg.data == WSCloseCode.GOING_AWAY


@pytest.mark.asyncio
async def test_ws_handler_target_error(aiohttp_client, ws_target_ctx):
    app = _proxy_app(context=ws_target_ctx)
    client = await aiohttp_client(app)

    async with client.ws_connect("/") as ws:
        await ws.send_str("error")
        msg = await ws.receive()

    assert msg.type == WSMsgType.CLOSE
    assert msg.data == WSCloseCode.GOING_AWAY
