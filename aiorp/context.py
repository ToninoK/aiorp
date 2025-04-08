from typing import Callable

from aiohttp import ClientSession, client, web
from yarl import URL

from aiorp.request import ProxyRequest
from aiorp.response import ProxyResponse

SessionFactory = Callable[[], ClientSession]


class ProxyContext:
    """Proxy options used to configure the proxy handler"""

    def __init__(
        self, url: URL, session_factory: SessionFactory | None = None, state=None
    ):
        self.url = url
        self.state = state
        self.session_factory: SessionFactory = session_factory or ClientSession
        self._request: ProxyRequest | None = None
        self._response: ProxyResponse | None = None
        self._session: ClientSession | None = None

    @property
    def response(self):
        if self.response is None:
            raise ValueError("Response is not yet set")
        return self.response

    @property
    def request(self):
        if self.request is None:
            raise ValueError("Request is not yet set")
        return self.request

    def _set_request(self, request: web.Request):
        self._request = ProxyRequest(
            url=self.url,
            in_req=request,
        )

    def _set_response(self, response: client.ClientResponse):
        self._response = ProxyResponse(in_resp=response)

    @property
    def session(self) -> ClientSession:
        """Get the session object, creating it if necessary"""
        if not self._session or self._session.closed:
            self._session = self.session_factory()
        return self._session

    async def close_session(self):
        """Close the session object"""
        if self._session:
            await self._session.close()
        self._session = None
