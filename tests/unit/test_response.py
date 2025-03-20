import pytest
from aiohttp import ClientSession
from aiohttp.test_utils import make_mocked_request
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
    mock_request = make_mocked_request("GET", "/")
    with aioresponses() as mocked:
        mocked.get("http://test.com/", body="test")
        resp = await http_client.get("http://test.com/")

        proxy_response = ProxyResponse(mock_request, resp)
        await proxy_response.set_response(ResponseType.BASE)
        assert proxy_response.response.status == 200
        assert proxy_response.response.headers == resp.headers
        assert proxy_response.response.body == b"test"


async def test_proxy_response_set_stream(
    http_client,
):  # pylint: disable=redefined-outer-name
    """Test the ProxyResponse class when the response is set to stream"""
    mock_request = make_mocked_request("GET", "/")
    with aioresponses() as mocked:
        mocked.get("http://test.com/")
        resp = await http_client.get("http://test.com/")

        proxy_response = ProxyResponse(mock_request, resp)
        await proxy_response.set_response(ResponseType.STREAM)
        assert proxy_response.response.status == 200
        assert "Transfer-Encoding" in proxy_response.response.headers
        assert proxy_response.response.headers["Transfer-Encoding"] == "chunked"


async def test_proxy_response_response_already_set(
    http_client,
):  # pylint: disable=redefined-outer-name
    """Test the ProxyResponse class when the response is already set"""
    mock_request = make_mocked_request("GET", "/")
    with aioresponses() as mocked:
        mocked.get("http://test.com/", body="test")
        resp = await http_client.get("http://test.com/")

        proxy_response = ProxyResponse(mock_request, resp)
        await proxy_response.set_response(ResponseType.BASE)

        with pytest.raises(ValueError):
            await proxy_response.set_response(ResponseType.BASE)


async def test_proxy_response_not_set():  # pylint: disable=redefined-outer-name
    """Test the ProxyResponse class when the response is not set"""
    mock_request = make_mocked_request("GET", "/")
    proxy_response = ProxyResponse(mock_request, None)
    with pytest.raises(ValueError):
        proxy_response.response  # pylint: disable=pointless-statement
