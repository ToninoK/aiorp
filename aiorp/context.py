import aiohttp
from aiohttp.client import ClientSession
from yarl import URL


class ProxyContext:
    """Proxy options used to configure the proxy handler"""

    def __init__(self, url: URL, session_factory=None, attributes=None):
        self.url = url
        self.attributes = attributes
        self.session_factory = session_factory
        self._session: ClientSession | None = None

    @property
    def session(self) -> ClientSession:
        """Get the session object, creating it if necessary"""
        if not self._session or self._session.closed:
            self._session = (
                self.session_factory()
                if self.session_factory
                else aiohttp.ClientSession()
            )
        return self._session

    async def close_session(self):
        """Close the session object"""
        if self._session:
            await self._session.close()
        self._session = None
