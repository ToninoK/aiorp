from aiohttp import web

from aiorp.context import ProxyContext


class Rewrite:
    """Specifies a rewrite configuration for rewriting URL paths.

    This class defines a path rewriting rule that can be used to modify
    the path of incoming requests before they are proxied.

    Args:
        rfrom: The path pattern to match and replace.
        rto: The replacement path pattern.

    Raises:
        ValueError: If only one of rfrom or rto is provided.
    """

    def __init__(self, rfrom: str, rto: str):
        """Initialize the rewrite configuration.

        Args:
            rfrom: The path pattern to match and replace.
            rto: The replacement path pattern.

        Raises:
            ValueError: If only one of rfrom or rto is provided.
        """
        if (rfrom and rto is None) or (rto and rfrom is None):
            raise ValueError("Both rewrite_from and rewrite_to must be set, or neither")
        self.rfrom = rfrom
        self.rto = rto


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
