from enum import Enum

from aiohttp import client, web


class ResponseType(Enum):
    """Response type enumeration"""

    STREAM = "STREAM"
    BASE = "BASE"


class ProxyResponse:
    """Proxy response object

    This object encapsulates the incoming request and the response from target server.
    It exposes a method to set the response object which can then be modified before being
    returned to the client.

    :param in_req: The incoming request object
    :param in_resp: The incoming response object
    :param proxy_attributes: Additional attributes to store in the response object
        This is where the proxy context will be stored and accessible.
    """

    def __init__(
        self,
        in_req: web.Request,
        in_resp: client.ClientResponse,
        proxy_attributes: dict = None,
    ):
        self.in_req: web.Request = in_req
        self.in_resp: client.ClientResponse = in_resp
        self.proxy_attributes: dict = proxy_attributes
        self._response: web.StreamResponse | None = None

    @property
    def response(
        self,
    ) -> web.StreamResponse | web.Response:
        if not self._response:
            raise ValueError("Response has not been set")
        return self._response

    async def set_response(self, response_type: ResponseType):
        if self._response:
            raise ValueError("Response can only be set once")
        if response_type == ResponseType.BASE:
            await self._set_base_response()
        elif response_type == ResponseType.STREAM:
            self._set_stream_response()
        return self._response

    def _set_stream_response(self):
        stream_resp = web.StreamResponse(
            status=self.in_resp.status,
            reason=self.in_resp.reason,
            headers=self.in_resp.headers,
        )
        stream_resp.prepare(self.in_req)
        self._response = stream_resp

    async def _set_base_response(self):
        text = await self.in_resp.text()
        content_type = self.in_resp.content_type
        charset = self.in_resp.charset
        if self.in_resp.headers.get("Content-Type"):
            content_type = None
            charset = None

        resp = web.Response(
            status=self.in_resp.status,
            reason=self.in_resp.reason,
            headers=self.in_resp.headers,
            content_type=content_type,
            charset=charset,
            # We load just text, web.Response takes care of encoding if needed
            text=text,
        )
        self._response = resp
