import pytest
import yarl
from aiohttp.test_utils import make_mocked_request

from aiorp.request import ProxyRequest
from aiorp.rewrite import Rewrite

pytestmark = [
    pytest.mark.unit,
    pytest.mark.rewrite,
]


def test_rewrite_path():
    """Test that the path is rewritten"""
    mock_request = make_mocked_request("GET", "/old/path")
    proxy_request = ProxyRequest(yarl.URL("http://localhost:8000"), mock_request)
    rewrite = Rewrite(rfrom="/path", rto="/newpath")
    proxy_request.url = rewrite.execute(proxy_request.url)
    assert proxy_request.url.path == "/old/newpath"

    print(proxy_request.url.path)
    rewrite = Rewrite(rfrom="/old/newpath", rto="/new/path")
    proxy_request.url = rewrite.execute(proxy_request.url)
    assert proxy_request.url.path == "/new/path"

    rewrite = Rewrite(rfrom="new", rto="old")
    proxy_request.url = rewrite.execute(proxy_request.url)
    assert proxy_request.url.path == "/old/path"
