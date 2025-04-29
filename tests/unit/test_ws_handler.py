import asyncio
from unittest import mock

import pytest
from aiohttp import WSCloseCode, WSMsgType, client, web
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


@pytest.mark.asyncio
async def test_ws_handler_proxy_error(aiohttp_client, ws_target_ctx):
    app = _proxy_app(context=ws_target_ctx)
    client = await aiohttp_client(app)

    with mock.patch("aiorp.ws_handler.WsProxyHandler._proxy_messages") as mock_proxy:
        mock_proxy.side_effect = Exception("proxy error")
        async with client.ws_connect("/") as ws:
            msg = await ws.receive()

    assert msg.type == WSMsgType.CLOSE
    assert msg.data == WSCloseCode.INTERNAL_ERROR


@pytest.mark.asyncio
async def test_ws_handler_task_cancellation(aiohttp_client, ws_target_ctx):
    app = _proxy_app(context=ws_target_ctx)
    cli = await aiohttp_client(app)

    async def mock_proxy_messages(source, target):
        if isinstance(source, client.ClientWebSocketResponse):
            # Client->target task completes quickly
            await asyncio.sleep(0.1)
        else:
            # Target->client task would run longer
            await asyncio.sleep(10.0)

    with mock.patch("aiorp.ws_handler.WsProxyHandler._proxy_messages") as mock_proxy:
        mock_proxy.side_effect = mock_proxy_messages

        async with cli.ws_connect("/") as ws:
            msg = await ws.receive()

    assert msg.type == WSMsgType.CLOSE
    assert msg.data == WSCloseCode.OK


@pytest.mark.asyncio
async def test_ws_handler_task_cancellation_reverse(aiohttp_client, ws_target_ctx):
    app = _proxy_app(context=ws_target_ctx)
    cli = await aiohttp_client(app)

    async def mock_proxy_messages(source, target):
        if isinstance(source, client.ClientWebSocketResponse):
            # Target->client task would run longer
            await asyncio.sleep(10.0)
        else:
            # Client->target task completes quickly
            await asyncio.sleep(0.1)

    with mock.patch("aiorp.ws_handler.WsProxyHandler._proxy_messages") as mock_proxy:
        mock_proxy.side_effect = mock_proxy_messages

        async with cli.ws_connect("/") as ws:
            msg = await ws.receive()

    assert msg.type == WSMsgType.CLOSE
    assert msg.data == WSCloseCode.OK


@pytest.mark.asyncio
async def test_ws_handler_ping_pong(aiohttp_client, ws_target_ctx):
    app = _proxy_app(context=ws_target_ctx)
    cli = await aiohttp_client(app)

    async with cli.ws_connect("/") as ws:
        # WebSocket is working if we can send and receive a message
        await ws.send_bytes(b"test")
        msg = await ws.receive()
        assert msg.type == WSMsgType.BINARY
        assert msg.data == b"received: test"
