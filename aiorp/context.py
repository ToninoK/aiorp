from typing import Callable

from aiohttp import ClientSession, ClientWebSocketResponse, client, web
from aiohttp.web_ws import WebSocketResponse
from yarl import URL

from aiorp.request import ProxyRequest
from aiorp.response import ProxyResponse

SessionFactory = Callable[[], ClientSession]


#  pylint: disable=too-many-instance-attributes
class ProxyContext:
    """Proxy options used to configure the proxy handler.

    This class manages the context for proxy operations, including the target URL,
    session management, and request/response handling.

    Args:
        url: The target URL to proxy requests to.
        session_factory: Optional factory function to create client sessions.
            If not provided, defaults to aiohttp.ClientSession.
        state: Optional state object to store additional context data.
    """

    def __init__(
        self,
        url: URL,
        session_factory: SessionFactory | None = None,
        state: dict | None = None,
    ):
        """Initialize the proxy context.

        Args:
            url: The target URL to proxy requests to.
            session_factory: Optional factory function to create client sessions.
            state: Optional state object to store additional context data.
        """
        self.url: URL = url
        self.state: dict | None = state
        self.session_factory: SessionFactory = session_factory or ClientSession
        self._request: ProxyRequest | None = None
        self._response: ProxyResponse | None = None
        self._ws_source: web.WebSocketResponse | None = None
        self._ws_target: client.ClientWebSocketResponse | None = None
        self._session: ClientSession | None = None

    def __copy__(self) -> "ProxyContext":
        """Copy the proxy context

        Shares the session object, but creates a new instance for the state.

        Returns:
            A ProxyContext instance with a new instance of state,
                but the same session object.
        """
        ctx = ProxyContext(
            url=self.url,  # Thread-safe design, always returns a new instance
            state={**self.state} if self.state else None,
            session_factory=self.session_factory,
        )
        # Set the session if it is already there
        ctx._session = self._session
        return ctx

    @property
    def ws_source(self) -> WebSocketResponse | None:
        """WebSocketResponse in charge of handling the server side socket with the client.

        Returns:
            The WebSocketResponse
        """
        return self._ws_source

    @property
    def ws_target(self) -> ClientWebSocketResponse | None:
        """ClientWebSocketResponse in charge of handling the client side socket
        with the target server.

        Returns:
            The ClientWebSocketResponse
        """
        return self._ws_target

    @property
    def response(self) -> ProxyResponse:
        """Get the current proxy response.

        Returns:
            The current ProxyResponse object.

        Raises:
            ValueError: If the response has not been set yet.
        """
        if self._response is None:
            raise ValueError("Response is not yet set")
        return self._response

    @property
    def request(self) -> ProxyRequest:
        """Get the current proxy request.

        Returns:
            The current ProxyRequest object.

        Raises:
            ValueError: If the request has not been set yet.
        """
        if self._request is None:
            raise ValueError("Request is not yet set")
        return self._request

    def _set_request(self, request: web.Request):
        """Set the current proxy request.

        Args:
            request: The incoming web request to proxy.
        """
        self._request = ProxyRequest(
            url=self.url,
            in_req=request,
        )

    def _set_response(self, response: client.ClientResponse):
        """Set the current proxy response.

        Args:
            response: The response from the target server.
        """
        self._response = ProxyResponse(in_resp=response)

    @property
    def session(self) -> ClientSession | None:
        """Get the session object, creating it if necessary.

        Returns:
            An active ClientSession instance.

        Note:
            If the session is closed or doesn't exist, a new one will be created
            using the session factory.
        """
        self.start_session()
        return self._session

    def start_session(self):
        """Build the session using the factory"""
        if self._session is None or self._session.closed:
            self._session = self.session_factory()

    async def close_session(self):
        """Close the session object.

        This method properly closes the current session and cleans up resources.
        """
        if self._session is not None:
            await self._session.close()
        self._session = None

    def set_socket_pair(
        self, ws_source: WebSocketResponse, ws_target: ClientWebSocketResponse
    ):
        """Set the socket pair used for tunneling messages

        Args:
            ws_source: The WebSocketResponse to set
            ws_target: The ClientWebSocketResponse to set
        """
        self._ws_source = ws_source
        self._ws_target = ws_target

    async def terminate_sockets(self):
        """Terminate the sockets if any are set"""
        if self._ws_source and self._ws_target:
            await self._ws_source.close()
            await self._ws_target.close()
