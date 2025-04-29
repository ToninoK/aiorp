import pytest
from aiohttp import WSCloseCode, WSMsgType
from aiohttp.test_utils import TestClient

from aiorp.http_handler import MiddlewarePhase, ProxyMiddlewareDef
from aiorp.rewrite import Rewrite
from tests.utils.proxy_middlewares import (
    RESPONSE_MODIFIED_VALUE,
    modify_both,
    modify_request,
    modify_response,
)

pytestmark = [
    pytest.mark.integration,
]


@pytest.mark.http_handler
@pytest.mark.asyncio
async def test_http_handler_proxy(aiohttp_client, proxy_server):

    http_rewrite = Rewrite("/http", "")
    server = await proxy_server(http={"rewrite": http_rewrite})
    client: TestClient = await aiohttp_client(server.app)

    resp = await client.get("/http/yell_path")
    text = await resp.text()

    assert resp.status == 200
    assert text == "/yell_path!!!"

    resp = await client.post("/http/upload")

    assert resp.status == 204


@pytest.mark.http_handler
@pytest.mark.asyncio
async def test_http_handler_proxy_error(aiohttp_client, proxy_server):
    http_rewrite = Rewrite("/http", "")
    server = await proxy_server(http={"rewrite": http_rewrite})
    client: TestClient = await aiohttp_client(server.app)

    resp = await client.get("/http/error")

    assert resp.status == 500
    assert resp.reason == "External API Error"

    resp = await client.get("/http/error/internal")

    assert resp.status == 500
    assert resp.reason == "External API Error"


@pytest.mark.http_handler
@pytest.mark.asyncio
async def test_modify_request(aiohttp_client, proxy_server):

    http_rewrite = Rewrite("/http", "")
    server = await proxy_server(
        http={
            "rewrite": http_rewrite,
            "middlewares": [
                ProxyMiddlewareDef(
                    phase=MiddlewarePhase.STANDARD, middleware=modify_request
                )
            ],
        }
    )
    client: TestClient = await aiohttp_client(server.app)

    # Endpoint returns request data in the json response so we can cross check if
    # the request modification was applied
    resp = await client.post("/http/request/data", json={"test": "iam test data"})
    data = await resp.json()

    assert "new_field" in data["body"]
    assert "X-Request-Added-Header" in data["headers"]
    assert "added_param" in data["params"]


@pytest.mark.http_handler
@pytest.mark.asyncio
async def test_modify_response(aiohttp_client, proxy_server):

    http_rewrite = Rewrite("/http", "")
    server = await proxy_server(
        http={
            "rewrite": http_rewrite,
            "middlewares": [
                ProxyMiddlewareDef(
                    phase=MiddlewarePhase.STANDARD, middleware=modify_response
                )
            ],
        }
    )
    client: TestClient = await aiohttp_client(server.app)

    resp = await client.get("/http/dump/data")
    data = await resp.json()

    assert "new_field" in data
    assert "X-Response-Added-Header" in resp.headers


@pytest.mark.http_handler
@pytest.mark.asyncio
async def test_modify_request_and_response(aiohttp_client, proxy_server):

    http_rewrite = Rewrite("/http", "")
    server = await proxy_server(
        http={
            "rewrite": http_rewrite,
            "middlewares": [
                ProxyMiddlewareDef(
                    phase=MiddlewarePhase.STANDARD, middleware=modify_both
                )
            ],
        }
    )
    client: TestClient = await aiohttp_client(server.app)

    resp = await client.post("/http/request/data", json={"data": "test"})
    data = await resp.json()

    assert "new_field" in data
    assert data["new_field"] == RESPONSE_MODIFIED_VALUE
    assert "X-Response-Added-Header" in resp.headers


@pytest.mark.websocket_handler
@pytest.mark.asyncio
async def test_ws_handler_proxy(aiohttp_client, proxy_server):
    ws_rewrite = Rewrite("/ws", "")
    server = await proxy_server(ws={"rewrite": ws_rewrite})
    client = await aiohttp_client(server.app)

    async with client.ws_connect("/ws") as ws:
        await ws.send_str("Test")
        msg = await ws.receive()

        assert msg.data == "received: Test"

        await ws.send_str("close")
        msg = await ws.receive()
        assert msg.type == WSMsgType.CLOSE
        assert msg.data == WSCloseCode.GOING_AWAY
