import unittest.mock
from unittest.mock import MagicMock

import pytest
from aiohttp.test_utils import make_mocked_request
from aiohttp.web_exceptions import HTTPUnauthorized

from aiorp.base_handler import Rewrite
from aiorp.context import ProxyContext
from aiorp.http_handler import HTTPProxyHandler
from aiorp.response import ResponseType

pytestmark = [
    pytest.mark.http_handler,
    pytest.mark.unit,
]


def _get_sample_middleware(order: int):
    async def sample_middleware(context: ProxyContext):
        print(f"Pre-yield: {order}")
        yield
        print(f"Post-yield: {order}")

    return sample_middleware


async def _ctx_modifying_middleware(context: ProxyContext):
    context.request.headers["X-Added-Header"] = "12345"
    context.request.params["added_param"] = "I am added"
    yield
    await context.response.set_response(ResponseType.BASE)
    context.response.web.headers["X-Added-Response-Header"] = "12345"


async def _error_raising_middleware(context: ProxyContext):
    raise HTTPUnauthorized(reason="Unauthorized")
    yield  # pylint: disable=unreachable


def test_handler_init_invalid_req_opts():
    request_options = {
        "method": "GET",
        "url": "http://smth.com/test",
    }
    with pytest.raises(ValueError):
        HTTPProxyHandler(request_options=request_options)


@pytest.mark.asyncio
async def test_handler_call_no_ctx():
    handler = HTTPProxyHandler()
    req = make_mocked_request(method="GET", path="/test")
    with pytest.raises(ValueError):
        await handler(req)


@pytest.mark.asyncio
async def test_handler_call(target_ctx):
    handler = HTTPProxyHandler(context=target_ctx)
    req = make_mocked_request(method="GET", path="/yell_path")
    resp = await handler(req)

    assert resp.text == "/yell_path!!!"


@pytest.mark.asyncio
async def test_handler_rewrite_call(target_ctx):
    rewrite = Rewrite(rfrom="/simple", rto="/yell_path")
    handler = HTTPProxyHandler(context=target_ctx, rewrite=rewrite)
    req = make_mocked_request(method="GET", path="/simple")
    resp = await handler(req)

    assert resp.text == "/yell_path!!!"


@pytest.mark.asyncio
async def test_handler_middleware_called(target_ctx):
    handler = HTTPProxyHandler(context=target_ctx)
    middleware = MagicMock()
    handler.proxy(middleware)
    req = make_mocked_request(method="GET", path="/yell_path")
    await handler(req)
    middleware.assert_called()


@unittest.mock.patch("builtins.print")
@pytest.mark.asyncio
async def test_handler_call_order(mock_print, target_ctx):
    handler = HTTPProxyHandler(context=target_ctx)
    middleware_client_edge = _get_sample_middleware(0)
    middleware_target_edge = _get_sample_middleware(1000)

    handler.target_edge(middleware_target_edge)
    handler.client_edge(middleware_client_edge)

    req = make_mocked_request(method="GET", path="/yell_path")
    await handler(req)

    call_args = [call[0][0] for call in mock_print.call_args_list]
    expected = [
        "Pre-yield: 0",
        "Pre-yield: 1000",
        "Post-yield: 1000",
        "Post-yield: 0",
    ]

    assert call_args == expected


@pytest.mark.asyncio
async def test_handler_manipulates_ctx(target_ctx):
    handler = HTTPProxyHandler(context=target_ctx)
    handler.proxy(_ctx_modifying_middleware)

    req = make_mocked_request(method="GET", path="/yell_path")
    resp = await handler(req)

    assert "X-Added-Response-Header" in resp.headers


@pytest.mark.asyncio
async def test_handler_raises_err(target_ctx):
    handler = HTTPProxyHandler(context=target_ctx)
    handler.proxy(_error_raising_middleware)

    req = make_mocked_request(method="GET", path="/yell_path")
    with pytest.raises(HTTPUnauthorized):
        await handler(req)
