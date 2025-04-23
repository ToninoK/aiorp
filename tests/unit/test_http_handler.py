import unittest.mock
from unittest.mock import MagicMock

import pytest
import yarl
from aiohttp.test_utils import make_mocked_request
from aiohttp.web_exceptions import HTTPUnauthorized

from aiorp.base_handler import Rewrite
from aiorp.context import ProxyContext
from aiorp.http_handler import HttpProxyHandler
from aiorp.response import ResponseType

pytestmark = [
    pytest.mark.http_handler,
    pytest.mark.unit,
]


@pytest.fixture
async def simple_context(simple_server):
    url = yarl.URL(f"http://localhost:{simple_server.port}")
    context = ProxyContext(url=url)
    yield context
    await context.close_session()


def get_sample_middleware(order: int):
    async def sample_middleware(context: ProxyContext):
        print(f"Pre-yield: {order}")
        yield
        print(f"Post-yield: {order}")

    return sample_middleware


async def ctx_modifying_middleware(context: ProxyContext):
    context.request.headers["X-Added-Header"] = "12345"
    context.request.params["added_param"] = "I am added"
    yield
    await context.response.set_response(ResponseType.BASE)
    context.response.web.headers["X-Added-Response-Header"] = "12345"


async def error_raising_middleware(context: ProxyContext):
    raise HTTPUnauthorized(reason="Unauthorized")
    yield  # pylint: disable=unreachable


def test_handler_init_invalid_conn_opts():
    connection_options = {
        "method": "GET",
        "url": "http://smth.com/test",
    }
    with pytest.raises(ValueError):
        HttpProxyHandler(connection_options=connection_options)


@pytest.mark.asyncio
async def test_handler_call_no_ctx():
    handler = HttpProxyHandler()
    req = make_mocked_request(method="GET", path="/test")
    with pytest.raises(ValueError):
        await handler(req)


@pytest.mark.asyncio
async def test_handler_call(simple_context):
    handler = HttpProxyHandler(context=simple_context)
    req = make_mocked_request(method="GET", path="/first")
    resp = await handler(req)

    assert resp.text == "/first!!!"


@pytest.mark.asyncio
async def test_handler_rewrite_call(simple_context):
    rewrite = Rewrite(rfrom="/simple", rto="/first")
    handler = HttpProxyHandler(context=simple_context, rewrite=rewrite)
    req = make_mocked_request(method="GET", path="/simple")
    resp = await handler(req)

    assert resp.text == "/first!!!"


@pytest.mark.asyncio
async def test_handler_middleware_called(simple_context):
    handler = HttpProxyHandler(context=simple_context)
    middleware = MagicMock()
    handler.middleware()(middleware)
    req = make_mocked_request(method="GET", path="/first")
    await handler(req)

    middleware.assert_called()


@unittest.mock.patch("builtins.print")
@pytest.mark.asyncio
async def test_handler_call_order(mock_print, simple_context):
    handler = HttpProxyHandler(context=simple_context)
    middleware_early = get_sample_middleware(0)
    middleware_late = get_sample_middleware(1000)

    handler.late(middleware_late)
    handler.early(middleware_early)

    req = make_mocked_request(method="GET", path="/first")
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
async def test_handler_manipulates_ctx(simple_context):
    handler = HttpProxyHandler(context=simple_context)
    handler.middleware()(ctx_modifying_middleware)

    req = make_mocked_request(method="GET", path="/first")
    resp = await handler(req)

    assert "X-Added-Header" in simple_context.request.headers
    assert "added_param" in simple_context.request.params
    assert "X-Added-Response-Header" in simple_context.response.web.headers
    assert "X-Added-Response-Header" in resp.headers


@pytest.mark.asyncio
async def test_handler_raises_err(simple_context):
    handler = HttpProxyHandler(context=simple_context)
    handler.middleware()(error_raising_middleware)

    req = make_mocked_request(method="GET", path="/first")
    with pytest.raises(HTTPUnauthorized):
        await handler(req)
