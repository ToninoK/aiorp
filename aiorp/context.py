from typing import Callable

import aiohttp
from aiohttp.client import ClientSession
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
        self.session_factory: SessionFactory = session_factory or aiohttp.ClientSession
        self.request: ProxyRequest | None = None
        self.response: ProxyResponse | None = None
        self._session: ClientSession | None = None

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
