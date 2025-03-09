from typing import Any

from aiohttp import client, web
from multidict import CIMultiDict, MultiMapping
from yarl import URL


class ProxyRequest:
    """Proxy request object

    This object encapsulates the incoming request and represents the request that will be sent
    to the target server. It exposes properties and methods to manipulate the request before
    it is executed.

    :param url: The target server URL
    :param in_req: The incoming request object
    :param proxy_attributes: Additional attributes to store in the request object
        This is where the proxy context will be stored and accessible.
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
        proxy_attributes: dict = None,
    ):
        self.in_req: web.Request = in_req
        self.url: URL = url
        self.headers: CIMultiDict[str] = CIMultiDict(in_req.headers)
        self.method: str = in_req.method
        self.params: MultiMapping[str] = in_req.query
        self.content: bytes | Any = None
        self.proxy_attributes: dict = proxy_attributes

        # Update path to match the incoming request
        self.url = self.url.with_path(self.in_req.path)

        # Update Host header with target server host
        self.headers.update({"Host": self.url.host})

        # Remove hop by hop headers
        for header in self.HOP_BY_HOP_HEADERS:
            self.headers.pop(header, None)

        # Set the X-Forwarded-For header
        self.set_x_forwarded_for()

    async def execute(
        self,
        session: client.ClientSession,
        **kwargs,
    ):
        """Execute the request using the provided session object

        Additionally, apply any optional keyword arguments to the request.

        :param session: The session object to use for the request
        :param kwargs: Optional keyword arguments to apply when executing the request
        """
        await self.load_content()
        return await session.request(
            method=self.in_req.method,
            url=self.url,
            headers=self.headers,
            params=self.params,
            data=self.content,
            **kwargs,
        )

    def set_x_forwarded_for(self, clean: bool = False):
        """Set the X-Forwarded related headers

        By default, appends the current remote address to the existing X-Forwarded-For
        header if one exists, and sets the X-Forwarded-Host header to the incoming host.
        If clean is set to True, the existing X-Forwarded-For header will be ignored and
        only the current remote address will be set.

        :param clean: If True, ignore the existing X-Forwarded-For header
        """
        self.headers["X-Forwarded-Host"] = self.in_req.host
        if self.in_req.headers.get("X-Forwarded-For") and not clean:
            self.headers[
                "X-Forwarded-For"
            ] = f"{self.in_req.headers['X-Forwarded-For']}, {self.in_req.remote}"
        else:
            self.headers["X-Forwarded-For"] = self.in_req.remote

    def upgrade_request(self):
        """Preserve the Upgrade header if it exists in the incoming request"""
        if not self.in_req.headers.get("Upgrade"):
            return

        self.headers["Upgrade"] = self.in_req.headers["Upgrade"]
        self.headers["Connection"] = "Upgrade"
        self.headers.pop("Sec-WebSocket-Key", None)
        self.headers.pop("Sec-WebSocket-Version", None)
        self.headers.pop("Sec-WebSocket-Extensions", None)

    async def load_content(self):
        """Load the content of the incoming request if it can be read"""
        if self.method in ["POST", "PUT", "PATCH"] and self.in_req.can_read_body:
            self.content = await self.in_req.read()

    def rewrite_path(self, current, new):
        """Rewrite the path of the request URL from current to new value

        :param current: The current path value to replace
        :param new: The new path value to replace with
        """
        self.url = self.url.with_path(self.url.path.replace(current, new))
