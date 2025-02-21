from enum import Enum
from functools import cached_property

from aiohttp import client, web


class ResponseType(Enum):
    STREAM = "STREAM"
    BASE = "BASE"

class ProxyResponse:
    def __init__(self, in_req: web.Request, in_resp: client.ClientResponse, proxy_attributes: dict = None):
        self.in_req = in_req
        self.in_resp = in_resp
        self.proxy_attributes = proxy_attributes
        self._response: web.StreamResponse | None = None

    @property
    def response(self) -> web.StreamResponse | web.Response:
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
            text=text,  # We load just text, web.Response takes care of encoding if needed
        )
        self._response = resp
