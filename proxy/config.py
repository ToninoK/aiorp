import aiohttp
import logging

from yarl import URL


class ProxyOptions:
    def __init__(self, url: URL, session: aiohttp.ClientSession, config: dict):
        self.url = url
        self.config = config
        if not session:
            logging.warning("No session provided, a default session will be used")
        self.session = session or aiohttp.ClientSession()
