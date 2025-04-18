import aiohttp
import pytest
from aiohttp.test_utils import make_mocked_request
from yarl import URL

from aiorp.context import ProxyContext


async def test_session_factory():
    context = ProxyContext(
        url=URL("http://test.com"),
        session_factory=lambda: aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(connect=10)
        ),
    )
    assert context.session is not None
    assert isinstance(context.session, aiohttp.ClientSession)
    assert context.session.timeout.connect == 10


async def test_context_no_session_factory():
    context = ProxyContext(url=URL("http://test.com"))
    assert context.session is not None


async def test_context_close_session():
    context = ProxyContext(url=URL("http://test.com"))
    session = context.session
    assert session is not None
    await context.close_session()
    assert session.closed


async def test_context_set_request():
    mock_request = make_mocked_request(method="GET", path="/test")
    context = ProxyContext(url=URL("http://test.com"))
    with pytest.raises(ValueError):
        context.request  # pylint: disable=pointless-statement

    context._set_request(mock_request)
    assert context.request is not None


async def test_context_set_response():
    context = ProxyContext(url=URL("http://test.com"))
    with pytest.raises(ValueError):
        context.response  # pylint: disable=pointless-statement

    # set response and assert that it is not None
