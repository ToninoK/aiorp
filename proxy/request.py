from aiohttp import client, web
from propcache import cached_property
from yarl import URL

from multidict import CIMultiDict


class ProxyRequest:
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
        rewrite_from: str = None,
        rewrite_to: str = None,
        preserve_upgrade: bool = True,
        proxy_attributes: dict = None,
    ):
        self.in_req: web.Request = in_req
        self.url = url
        self.headers = CIMultiDict(in_req.headers)
        self.method = in_req.method
        self.params = in_req.query
        self._content = None

        self._proxy_attributes: dict = proxy_attributes

        # URL
        # Handle path rewriting if specified
        self.url = self.url.with_path(self.in_req.path)
        if (rewrite_from and rewrite_to is None) or (rewrite_to and rewrite_from is None):
            raise ValueError("Both rewrite_from and rewrite_to must be set, or neither")
        elif rewrite_from and rewrite_to:
            self.rewrite_path(rewrite_from, rewrite_to)

        # HEADERS
        # Remove host header
        self.headers.pop("host")

        # Remove hop by hop headers
        for header in self.HOP_BY_HOP_HEADERS:
            self.headers.pop(header, None)


        # Set the X-Forwarded-For header
        # By default appends the current remote address to the existing X-Forwarded-For header if one exists
        self.set_x_forwarded_for()

        if preserve_upgrade:
            self._handle_request_upgrade()

    def _handle_request_upgrade(self):
        """Preserve the Upgrade header if it exists in the incoming request"""
        if not self.in_req.headers.get("Upgrade"):
            return
        self.headers["Upgrade"] = self.in_req.headers["Upgrade"]
        self.headers["Connection"] = "Upgrade"
        self.headers.pop("Sec-WebSocket-Key", None)
        self.headers.pop("Sec-WebSocket-Version", None)
        self.headers.pop("Sec-WebSocket-Extensions", None)

    async def execute(self, session: client.ClientSession, **kwargs):
        await self.content()
        return await session.request(
            method=self.in_req.method,
            url=self.url,
            headers=self.headers,
            params=self.params,
            data=self._content,
            **kwargs
        )

    def set_x_forwarded_for(self, clean: bool = False):
        """Set the X-Forwarded-For header

        By default, appends the current remote address to the existing X-Forwarded-For header if one exists,
        and sets the X-Forwarded-Host header to the incoming host. If clean is set to True, the existing
        X-Forwarded-For header will be ignored and only the current remote address will be set.

        :param clean: If True, ignore the existing X-Forwarded-For header
        """
        self.headers["X-Forwarded-Host"] = self.in_req.host
        if self.in_req.headers.get("X-Forwarded-For") and not clean:
            self.headers["X-Forwarded-For"] = f"{self.in_req.headers['X-Forwarded-For']}, {self.in_req.remote}"
        else:
            self.headers["X-Forwarded-For"] = self.in_req.remote

    async def content(self):
        if self.method in ["POST", "PUT", "PATCH"] and self.in_req.can_read_body:
            self._content = await self.in_req.read()
        return self._content

    def update_content(self, content):
        """Update the content of the request"""
        self._content = content

    def update_headers(self, headers):
        """Update the headers of the request"""
        self.headers.update(headers)

    def rewrite_path(self, current, new):
        """Rewrite the path of the request URL from current to new value

        :param current: The current path value to replace
        :param new: The new path value to replace with
        """
        self.url = self.url.with_path(self.url.path.replace(current, new))

    @cached_property
    def proxy_attributes(self):
        """Proxy configuration passed from the proxy handling this request"""
        return self._proxy_attributes



class ResponseContext:
    pass