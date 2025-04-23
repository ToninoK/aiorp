from aiohttp import web

from aiorp.context import ProxyContext


class Rewrite:
    """Specifies a rewrite configuration for rewriting url paths"""

    def __init__(self, rfrom: str, rto: str):
        if (rfrom and rto is None) or (rto and rfrom is None):
            raise ValueError("Both rewrite_from and rewrite_to must be set, or neither")
        self.rfrom = rfrom
        self.rto = rto


class BaseHandler:
    """Base handler for proxying requests, not to be used directly."""

    def __init__(
        self,
        context: ProxyContext | None = None,
        rewrite: Rewrite | None = None,
        connection_options: dict | None = None,
    ):

        self._context: ProxyContext | None = context
        self._rewrite = rewrite
        self.connection_options = connection_options or {}

    async def __call__(self, request: web.Request):
        raise NotImplementedError(
            "The __call__ method must be implemented in a subclass"
        )
