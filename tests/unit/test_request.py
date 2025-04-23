from unittest import mock

import pytest
from aiohttp.streams import StreamReader
from aiohttp.test_utils import make_mocked_request
from yarl import URL

from aiorp.request import ProxyRequest

TARGET_URL = URL("http://localhost:8080")

pytestmark = [
    pytest.mark.request,
    pytest.mark.unit,
]


def test_proxy_request():
    """Test the ProxyRequest class"""
    mock_request = make_mocked_request("GET", "/")
    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    assert proxy_request.method == "GET"
    assert proxy_request.url.path == "/"


def test_host_header_set():
    """Test that the Host header is set"""
    mock_request = make_mocked_request("GET", "/")
    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    assert proxy_request.headers["Host"] == "localhost"


def test_hop_by_hop_headers_removed():
    """Test that hop by hop headers are removed"""
    hop_by_hop_headers = {
        "connection": "keep-alive",
        "keep-alive": "timeout=5",
        "proxy-authenticate": "Basic",
        "proxy-authorization": "Basic",
        "te": "trailers",
        "trailers": "trailers",
        "transfer-encoding": "chunked",
    }
    mock_request = make_mocked_request("GET", "/", headers=hop_by_hop_headers)
    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    assert "Connection" not in proxy_request.headers
    assert "Keep-Alive" not in proxy_request.headers
    assert "Proxy-Connection" not in proxy_request.headers
    assert "TE" not in proxy_request.headers
    assert "Trailers" not in proxy_request.headers
    assert "Transfer-Encoding" not in proxy_request.headers


def test_user_agent_not_set():
    """Test that the User-Agent header is not set if it is not present"""
    mock_request = make_mocked_request("GET", "/")
    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    assert proxy_request.headers["User-Agent"] == ""


def test_user_agent_set():
    """Test that the User-Agent header is set if it is present"""
    mock_request = make_mocked_request(
        "GET", "/", headers={"User-Agent": "ishouldbehere"}
    )
    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    assert proxy_request.headers["User-Agent"] == "ishouldbehere"


def test_x_forwarded_headers_set():
    """Test that the X-Forwarded-For header is set"""
    headers = {"X-Forwarded-For": "127.0.0.1, 127.0.0.2", "host": "localhost"}

    # Create a mock transport with a specific peername
    mock_transport = mock.Mock()
    mock_transport.get_extra_info.side_effect = lambda name, default=None: {
        "peername": ("192.168.1.100", 12345),
    }.get(name, default)

    # Pass the mock transport to the request
    mock_request = make_mocked_request(
        "GET", "/", headers=headers, transport=mock_transport
    )

    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    assert proxy_request.headers["X-Forwarded-Host"] == "localhost"
    assert (
        proxy_request.headers["X-Forwarded-For"]
        == "127.0.0.1, 127.0.0.2, 192.168.1.100"
    )


def test_x_forwarded_headers_set_clean():
    """Test that the X-Forwarded-For header is set when the clean flag is set"""
    headers = {"X-Forwarded-For": "127.0.0.1, 127.0.0.2", "host": "localhost"}
    # Create a mock transport with a specific peername
    mock_transport = mock.Mock()
    mock_transport.get_extra_info.side_effect = lambda name, default=None: {
        "peername": ("192.168.1.100", 12345),
    }.get(name, default)

    # Pass the mock transport to the request
    mock_request = make_mocked_request(
        "GET",
        "/",
        headers=headers,
        transport=mock_transport,
    )
    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    assert proxy_request.headers["X-Forwarded-Host"] == "localhost"
    assert (
        proxy_request.headers["X-Forwarded-For"]
        == "127.0.0.1, 127.0.0.2, 192.168.1.100"
    )

    proxy_request.set_x_forwarded_for(clean=True)
    assert proxy_request.headers["X-Forwarded-Host"] == "localhost"
    assert proxy_request.headers["X-Forwarded-For"] == "192.168.1.100"


def test_host_header_set_from_proxy():
    """Test that the Host header is set from the proxy"""
    mock_request = make_mocked_request("GET", "/", headers={"Host": "proxyhost.com"})
    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    assert proxy_request.headers["Host"] == "localhost"


@pytest.mark.asyncio
async def test_content_loaded():
    """Test that the content is loaded"""
    payload = StreamReader(protocol=mock.Mock(), limit=1024**2)
    payload.feed_data(b"test")
    payload.feed_eof()
    mock_request = make_mocked_request("POST", "/", payload=payload)
    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    assert proxy_request.content is None
    await proxy_request.load_content()
    assert proxy_request.content == b"test"


@pytest.mark.asyncio
async def test_content_should_not_be_loaded():
    """Test that the content is not loaded if the method is not POST"""
    payload = StreamReader(protocol=mock.Mock(), limit=1024**2)
    payload.feed_data(b"test")
    payload.feed_eof()
    mock_request = make_mocked_request("GET", "/", payload=payload)
    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    assert proxy_request.content is None
    await proxy_request.load_content()
    assert proxy_request.content is None


def test_rewrite_path():
    """Test that the path is rewritten"""
    mock_request = make_mocked_request("GET", "/old/path")
    proxy_request = ProxyRequest(TARGET_URL, mock_request)
    proxy_request.rewrite_path("/path", "/newpath")
    assert proxy_request.url.path == "/old/newpath"

    proxy_request.rewrite_path("/old/newpath", "/new/path")
    assert proxy_request.url.path == "/new/path"

    proxy_request.rewrite_path("new", "old")
    assert proxy_request.url.path == "/old/path"
