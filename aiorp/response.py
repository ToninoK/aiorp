from enum import Enum

from aiohttp import client, web
from aiohttp.web import Response, StreamResponse
from multidict import CIMultiDict


class ResponseType(Enum):
    """Response type enumeration."""

    STREAM = "STREAM"
    BASE = "BASE"


class ProxyResponse:
    """Proxy response object.

    This object encapsulates the incoming request and the response from target server.
    It exposes a method to set the response object which can then be modified before being
    returned to the client.

    Args:
        in_resp: The incoming response object.
    """

    def __init__(
        self,
        in_resp: client.ClientResponse,
    ):
        """Initialize the proxy response object.

        Args:
            in_resp: The incoming response object.
        """
        self.in_resp: client.ClientResponse = in_resp
        self._web: web.StreamResponse | None = None
        self._content: bytes | None = None

    @property
    def web_response_set(self) -> bool:
        """Checks if the web response is set already.

        Returns:
            A boolean, true if set, false otherwise
        """
        return self._web is not None

    @property
    def web(
        self,
    ) -> StreamResponse | Response:
        """Access the web response.

        Returns:
            A response, either StreamResponse or Response.

        Raises:
            ValueError: When response is not set yet.
        """
        if self._web is None:
            raise ValueError("Response has not been set")
        return self._web

    async def set_response(
        self, response_type: ResponseType = ResponseType.BASE
    ) -> StreamResponse | Response:
        """Set the response using the given response type.

        Args:
            response_type: The type of response to set.

        Returns:
            The set web response.

        Raises:
            ValueError: When attempted to set the response a second time.
        """
        if self._web is not None:
            raise ValueError("Response can only be set once")
        if response_type == ResponseType.STREAM:
            self._web = await self._get_stream_response()
        else:
            self._web = await self._get_base_response()
        return self._web

    async def _get_stream_response(self) -> StreamResponse:
        """Convert incoming response to stream response."""

        headers = CIMultiDict(self.in_resp.headers)

        # These headers should not be proxied
        headers.pop("content-length", None)
        headers.pop("content-encoding", None)
        headers.pop("content-type", None)

        stream_resp = StreamResponse(
            status=self.in_resp.status,
            reason=self.in_resp.reason,
            headers=self.in_resp.headers,
        )
        return stream_resp

    async def _get_base_response(self) -> Response:
        """Convert incoming response to base response."""
        content = await self.in_resp.read()

        headers = CIMultiDict(self.in_resp.headers)

        # These headers should not be proxied
        headers.pop("content-length", None)
        headers.pop("content-encoding", None)

        if content:
            headers["content-length"] = str(len(content))

        resp = Response(
            status=self.in_resp.status,
            reason=self.in_resp.reason,
            headers=headers,
            body=content,
        )
        return resp
