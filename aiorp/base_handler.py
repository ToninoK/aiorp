from aiohttp import web

from aiorp.context import ProxyContext
from aiorp.rewrite import Rewrite


class BaseHandler:
    """Base handler for proxying requests, not to be used directly.

    This class provides the basic functionality for handling proxy requests.
    It should be subclassed to implement specific proxy behavior.

    Args:
        context: Optional proxy context containing target URL and session information.
        rewrite: Optional rewrite configuration for modifying request paths.
        request_options: Optional dictionary of additional request options to be injected on
            request. Refer to the `ClientSession.request` function arguments for the exact options
    """

    def __init__(
        self,
        context: ProxyContext | None = None,
        rewrite: Rewrite | None = None,
        request_options: dict | None = None,
    ):
        self._rewrite = rewrite
        self.request_options = request_options or {}
        self.context: ProxyContext | None = context

    async def __call__(self, request: web.Request):
        """Handle incoming requests.

        This method must be implemented by subclasses to provide specific
        proxy behavior.

        Args:
            request: The incoming web request to handle.

        Raises:
            NotImplementedError: Always raised as this method must be implemented
                by subclasses.
        """
        raise NotImplementedError(
            "The __call__ method must be implemented in a subclass"
        )
