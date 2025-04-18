import asyncio
from unittest.mock import AsyncMock

import pytest
from aiohttp import web

from aiorp.context import ProxyContext
from aiorp.ws_handler import WsProxyHandler


def test_ws_handler_init():
    with pytest.raises(ValueError):
        WsProxyHandler(connection_options={"url": "http://localhost:8080"})

    with pytest.raises(ValueError):
        WsProxyHandler(
            message_handler=lambda x, y: None,
            client_message_handler=lambda x, y: None,
            web_message_handler=lambda x, y: None,
        )

    with pytest.raises(ValueError):
        WsProxyHandler(
            message_handler=lambda x, y: None,
            client_message_handler=lambda x, y: None,
        )

    with pytest.raises(ValueError):
        WsProxyHandler(
            message_handler=lambda x, y: None,
            web_message_handler=lambda x, y: None,
        )


# pylint: disable=protected-access
@pytest.mark.current
async def test_sock_to_sock_text():
    ws_handler = WsProxyHandler(context=ProxyContext(url="http://localhost:8080"))
    ws_client = AsyncMock()
    ws_target = AsyncMock()
    ws_client.closed = False
    ws_target.closed = False

    # Test TEXT message
    ws_client.receive.side_effect = [
        AsyncMock(type=web.WSMsgType.TEXT, data="test message"),
        AsyncMock(type=web.WSMsgType.CLOSE),
    ]
    await ws_handler._sock_to_sock(ws_client, ws_target)
    ws_target.send_str.assert_called_once_with("test message")
    ws_target.close.assert_called_once()


# pylint: disable=protected-access
async def test_sock_to_sock_binary():
    ws_handler = WsProxyHandler(context=ProxyContext(url="http://localhost:8080"))
    ws_client = AsyncMock()
    ws_target = AsyncMock()
    ws_client.closed = False
    ws_target.closed = False

    # Test BINARY message
    ws_client.receive.side_effect = [
        AsyncMock(type=web.WSMsgType.BINARY, data=b"test data"),
        AsyncMock(type=web.WSMsgType.CLOSE),
    ]
    await ws_handler._sock_to_sock(ws_client, ws_target)
    ws_target.send_bytes.assert_called_once_with(b"test data")
    ws_target.close.assert_called_once()


# pylint: disable=protected-access
async def test_sock_to_sock_ping():
    ws_handler = WsProxyHandler(context=ProxyContext(url="http://localhost:8080"))
    ws_client = AsyncMock()
    ws_target = AsyncMock()
    ws_client.closed = False
    ws_target.closed = False

    # Test PING message
    ws_client.receive.side_effect = [
        AsyncMock(type=web.WSMsgType.PING),
        AsyncMock(type=web.WSMsgType.CLOSE),
    ]
    await ws_handler._sock_to_sock(ws_client, ws_target)
    ws_target.ping.assert_called_once()
    ws_target.close.assert_called_once()


# pylint: disable=protected-access
async def test_sock_to_sock_pong():
    ws_handler = WsProxyHandler(context=ProxyContext(url="http://localhost:8080"))
    ws_client = AsyncMock()
    ws_target = AsyncMock()
    ws_client.closed = False
    ws_target.closed = False

    # Test PONG message
    ws_client.receive.side_effect = [
        AsyncMock(type=web.WSMsgType.PONG),
        AsyncMock(type=web.WSMsgType.CLOSE),
    ]
    await ws_handler._sock_to_sock(ws_client, ws_target)
    ws_target.pong.assert_called_once()
    ws_target.close.assert_called_once()


# pylint: disable=protected-access
async def test_sock_to_sock_timeout():
    ws_handler = WsProxyHandler(context=ProxyContext(url="http://localhost:8080"))
    ws_client = AsyncMock()
    ws_target = AsyncMock()
    ws_target.closed = False

    # Test timeout
    ws_client.receive.side_effect = asyncio.TimeoutError
    await ws_handler._sock_to_sock(ws_client, ws_target)
    ws_target.close.assert_called_once_with(code=1001, message=b"Server disconnected")


# pylint: disable=protected-access
async def test_sock_to_sock_exception():
    ws_handler = WsProxyHandler(context=ProxyContext(url="http://localhost:8080"))
    ws_client = AsyncMock()
    ws_target = AsyncMock()
    ws_target.closed = False
    ws_client.receive.side_effect = Exception("Test exception")

    # Test timeout
    with pytest.raises(Exception):
        await ws_handler._sock_to_sock(ws_client, ws_target)
    ws_target.close.assert_called_once_with(code=1011, message=b"Test exception")


# pylint: disable=protected-access
async def test_close_active_sockets():
    ws_handler = WsProxyHandler(context=ProxyContext(url="http://localhost:8080"))
    ws_client = AsyncMock()
    ws_target = AsyncMock()
    ws_handler._active_sockets = [(ws_client, ws_target)]
    ws_target.closed = False
    ws_client.closed = False

    await ws_handler.close_active_sockets()
    ws_client.close.assert_called_once()
    ws_target.close.assert_called_once()
