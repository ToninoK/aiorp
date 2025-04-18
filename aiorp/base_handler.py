from aiohttp import web

from aiorp.context import ProxyContext


class BaseHandler:
    """Base handler for proxying requests, not to be used directly."""

    def __init__(
        self,
        context: ProxyContext | None = None,
        rewrite_from=None,
        rewrite_to=None,
        connection_options: dict | None = None,
    ):

        if (rewrite_from and rewrite_to is None) or (
            rewrite_to and rewrite_from is None
        ):
            raise ValueError("Both rewrite_from and rewrite_to must be set, or neither")

        self._context: ProxyContext | None = context
        self._rewrite_from = rewrite_from
        self._rewrite_to = rewrite_to

        self.connection_options = connection_options or {}

    async def __call__(self, request: web.Request):
        raise NotImplementedError(
            "The __call__ method must be implemented in a subclass"
        )
