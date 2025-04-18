import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from aiorp.response import ProxyResponse, ResponseType

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.response,
    pytest.mark.unit,
]


@pytest.fixture
async def http_client():
    session = ClientSession()
    yield session
    await session.close()


async def test_proxy_response_set_base(
    http_client,
):  # pylint: disable=redefined-outer-name
    """Test the ProxyResponse class when the response is set to base"""
    with aioresponses() as mocked:
        mocked.get("http://test.com/", body="test")
        resp = await http_client.get("http://test.com/")

        proxy_response = ProxyResponse(resp)
        await proxy_response.set_response(ResponseType.BASE)
        assert proxy_response.web.status == 200
        assert proxy_response.web.headers == resp.headers
        assert proxy_response.web.body == b"test"


async def test_proxy_response_set_stream(
    http_client,
):  # pylint: disable=redefined-outer-name
    """Test the ProxyResponse class when the response is set to stream"""
    with aioresponses() as mocked:
        mocked.get("http://test.com/")
        resp = await http_client.get("http://test.com/")

        proxy_response = ProxyResponse(resp)
        await proxy_response.set_response(ResponseType.STREAM)
        assert proxy_response.web.status == 200
        assert "Transfer-Encoding" in proxy_response.web.headers
        assert proxy_response.web.headers["Transfer-Encoding"] == "chunked"


async def test_proxy_response_response_already_set(
    http_client,
):  # pylint: disable=redefined-outer-name
    """Test the ProxyResponse class when the response is already set"""
    with aioresponses() as mocked:
        mocked.get("http://test.com/", body="test")
        resp = await http_client.get("http://test.com/")

        proxy_response = ProxyResponse(resp)
        await proxy_response.set_response(ResponseType.BASE)

        with pytest.raises(ValueError):
            await proxy_response.set_response(ResponseType.BASE)


async def test_proxy_response_not_set():  # pylint: disable=redefined-outer-name
    """Test the ProxyResponse class when the response is not set"""
    proxy_response = ProxyResponse(None)
    with pytest.raises(ValueError):
        proxy_response.web  # pylint: disable=pointless-statement
