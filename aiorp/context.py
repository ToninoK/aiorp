from typing import Callable

from aiohttp import ClientSession, client, web
from yarl import URL

from aiorp.request import ProxyRequest
from aiorp.response import ProxyResponse

SessionFactory = Callable[[], ClientSession]


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
        state: dict = None,
    ):
        """Initialize the proxy context.

        Args:
            url: The target URL to proxy requests to.
            session_factory: Optional factory function to create client sessions.
            state: Optional state object to store additional context data.
        """
        self.url: URL = url
        self.state: dict = state
        self.session_factory: SessionFactory = session_factory or ClientSession
        self._request: ProxyRequest | None = None
        self._response: ProxyResponse | None = None
        self._session: ClientSession | None = None

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
    def session(self) -> ClientSession:
        """Get the session object, creating it if necessary.

        Returns:
            An active ClientSession instance.

        Note:
            If the session is closed or doesn't exist, a new one will be created
            using the session factory.
        """
        if not self._session or self._session.closed:
            self._session = self.session_factory()
        return self._session

    async def close_session(self):
        """Close the session object.

        This method properly closes the current session and cleans up resources.
        """
        if self._session:
            await self._session.close()
        self._session = None
