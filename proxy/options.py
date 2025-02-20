import aiohttp

from yarl import URL


class ProxyOptions:
    def __init__(self, url: URL, session_factory = None, attributes = None):
        self.url = url
        self.attributes = attributes
        self._session_factory = session_factory
        self._session = None

    @property
    def session(self):
        if not self._session:
            self._session = self._session_factory() if self._session_factory else aiohttp.ClientSession()
        return self._session