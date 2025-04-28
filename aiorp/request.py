from typing import Any

from aiohttp import web
from multidict import CIMultiDict
from yarl import URL


class ProxyRequest:
    """Proxy request object.

    This object encapsulates the incoming request and represents the request that will be sent
    to the target server. It exposes properties and methods to manipulate the request before
    it is executed.

    Args:
        url: The target server URL.
        in_req: The incoming request object.
    """

    HOP_BY_HOP_HEADERS = [
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    ]

    def __init__(
        self,
        url: URL,
        in_req: web.Request,
    ):
        self.in_req: web.Request = in_req
        self.url: URL = url
        self.headers: CIMultiDict[str] = CIMultiDict(in_req.headers)
        self.method: str = in_req.method
        self.params: dict = dict(in_req.query)
        self.content: bytes | Any = None

        # Update path to match the incoming request
        self.url = self.url.with_path(self.in_req.path)

        # Update Host header with target server host
        self.headers.update(host=self.url.host or "")

        # Remove hop by hop headers
        for header in self.HOP_BY_HOP_HEADERS:
            self.headers.pop(header, None)

        # Don't send default user-agent header if no other is provided
        if "user-agent" not in self.headers:
            self.headers["User-Agent"] = ""

        # Set the X-Forwarded-For header
        self.set_x_forwarded_for()

    def set_x_forwarded_for(self, clean: bool = False):
        """Set the X-Forwarded related headers.

        By default, appends the current remote address to the existing X-Forwarded-For
        header if one exists, and sets the X-Forwarded-Host header to the incoming host.
        If clean is set to True, the existing X-Forwarded-For header will be ignored and
        only the current remote address will be set.

        Args:
            clean: If True, ignore the existing X-Forwarded-For header.
        """
        self.headers["X-Forwarded-Host"] = self.in_req.host
        if self.in_req.headers.get("X-Forwarded-For") and not clean:
            self.headers[
                "X-Forwarded-For"
            ] = f"{self.in_req.headers['X-Forwarded-For']}, {self.in_req.remote}"
        elif self.in_req.remote:
            self.headers["X-Forwarded-For"] = self.in_req.remote

    async def load_content(self):
        """Load the content of the incoming request if it can be read."""
        if self.method in ["POST", "PUT", "PATCH"] and self.in_req.can_read_body:
            self.content = await self.in_req.read()
