import asyncio
import copy
import json
import logging
from collections import defaultdict
from enum import IntEnum
from typing import Any, AsyncGenerator, Awaitable, Callable

from aiohttp import ClientResponseError, client, web
from aiohttp.web_exceptions import HTTPInternalServerError

from aiorp.base_handler import BaseHandler
from aiorp.context import ProxyContext
from aiorp.response import ResponseType

log = logging.getLogger(__name__)

ErrorHandler = Callable[[ClientResponseError], None] | None
ProxyMiddleware = Callable[[ProxyContext], Awaitable]


class MiddlewarePhase(IntEnum):
    """Middleware phase enumeration."""

    EARLY = 0  # Authentication, security checks
    STANDARD = 500  # Logging, tracking, most transformations
    LATE = 1000  # Anything you might want to execute last before request is sent out


class HTTPProxyHandler(BaseHandler):
    """A handler for proxying requests to a remote server.

    This handler is used to proxy requests to a remote server.
    It has a __call__ method that is used to handle incoming requests.
    The handler can be used as a route handler in an aiohttp.web application.
    It executes specified before and after handlers, before and after the
    incoming request is proxied.

    Args:
        error_handler: Callable that is called when an error occurs during the proxied request.

    Raises:
        ValueError: If connection options contain invalid keys.
    """

    def __init__(self, *args: Any, error_handler: ErrorHandler = None, **kwargs: Any):
        """Initialize the HTTP proxy handler.

        Args:
            *args: Variable length argument list.
            error_handler: Optional callable for handling errors during proxied requests.
            **kwargs: Arbitrary keyword arguments.

        Raises:
            ValueError: If connection options contain invalid keys.
        """
        super().__init__(*args, **kwargs)
        if self.connection_options is not None and any(
            key in self.connection_options
            for key in [
                "method",
                "url",
                "headers",
                "params",
                "data",
            ]
        ):
            raise ValueError(
                "The request options can't contain: method, url, headers, params or data keys.\n"
                "They should be handled by using the ProxyRequest object in the before handlers."
            )

        self._error_handler = error_handler
        self._middlewares = defaultdict(list)

    async def __call__(self, request: web.Request) -> web.Response | web.StreamResponse:
        """Handle incoming requests.

        This method is called when the handler is used as a route handler in an aiohttp.web app.
        It executes the middleware chain that was set by the users.

        Args:
            request: The incoming request to proxy.

        Returns:
            The response from the external server.

        Raises:
            ValueError: If proxy context is not set.
            HTTPInternalServerError: If there's an error during request processing.
        """
        if self.context is None:
            raise ValueError("Proxy context must be set before the handler is invoked.")

        # Make sure session is started in parent so we can preserve it between
        # the copies of contexts
        self.context.start_session()

        # We need to copy context since we don't want race conditions
        # with request or response setting
        ctx = copy.copy(self.context)

        # Set the request to context
        ctx._set_request(request)

        if self._rewrite:
            ctx.request.rewrite_path(
                self._rewrite.rfrom,
                self._rewrite.rto,
            )

        # Execute the middleware chain
        await self._execute_middleware_chain(ctx)

        # Check if the web response was set and set it if it wasn't
        if not ctx.response.web_response_set:
            await ctx.response.set_response(response_type=ResponseType.BASE)

        # Return the response
        return ctx.response.web

    async def _execute_middleware_chain(self, ctx: ProxyContext):
        """Execute the entire provided middleware chain.

        The chain is executed in order the middlewares were registered,
        with the pre-yield code executing in that order, and the post-yield
        executing in reverse order ("russian doll model").

        Raises:
            ValueError: If context is not set before execution.
        """
        sorted_middlewares = sorted(self._middlewares.keys())
        middleware_generators = defaultdict(list)

        # Start all middleware generators and store them
        for order_key in sorted_middlewares:
            middleware_funcs = self._middlewares[order_key]
            generators = [aiter(func(ctx)) for func in middleware_funcs]
            await asyncio.gather(*[anext(gen, None) for gen in generators])
            middleware_generators[order_key] = generators

        # Execute the actual request
        await self._proxy_middleware(ctx)

        # Resume all middleware generators in reverse order
        for order_key in reversed(sorted_middlewares):
            await asyncio.gather(
                *[anext(gen, None) for gen in middleware_generators[order_key]]
            )

    async def _proxy_middleware(self, ctx: ProxyContext):
        """The default final middleware in the middleware chain.

        It executes after all other user provided middlewares, and
        it proxies the request to the target destination.

        Args:
            context: The proxy context holding the request and response information.

        Raises:
            ValueError: If proxy request is not set.
        """
        if ctx.request is None:
            raise ValueError("ProxyRequest not set")
        # Execute the request and check the response
        await ctx.request.load_content()
        resp = await ctx.session.request(
            url=ctx.request.url,
            method=ctx.request.method,
            params=ctx.request.params,
            headers=ctx.request.headers,
            data=ctx.request.content,
            **self.connection_options,
        )
        self._raise_for_status(resp)
        # Build the proxy response object from the target response
        ctx._set_response(resp)

    def _raise_for_status(self, response: client.ClientResponse):
        """Check status of request and handle the error properly.

        In case of an error, the error_handler is called if set, otherwise an
        HTTPInternalServerError is raised with the error message.

        Args:
            response: The response from the external server.

        Raises:
            HTTPInternalServerError: If the response status indicates an error.
        """
        try:
            response.raise_for_status()
        except ClientResponseError as err:
            if self._error_handler:
                self._error_handler(err)
            raise HTTPInternalServerError(
                reason="External API Error",
                content_type="application/json",
                text=json.dumps(
                    {
                        "status": err.status,
                        "message": err.message,
                    }
                ),
            )

    def add_middleware(
        self, order: int, func: Callable[[ProxyContext], AsyncGenerator[None, Any]]
    ):
        """Register a middleware with explicit ordering.

        It will be registered depending on the order and relative to
        other defined middlewares. A lower number means sooner registration,
        while a higher number results in a later registration.

        Args:
            order: Integer representing order of middleware registration.
            func: The middleware function
        """
        self._middlewares[order].append(func)

    def default(
        self, func: Callable[[ProxyContext], AsyncGenerator[None, Any]]
    ) -> Callable[[ProxyContext], AsyncGenerator[None, Any]]:
        """Register a middleware with default execution order that can yield.

        Executes the pre-yield code before late, but after early middleware,
        and the post-yield code after late but before early middleware.

        Args:
            func: The middleware function which yields.

        Returns:
            The decorated middleware function.
        """
        self.add_middleware(MiddlewarePhase.STANDARD, func)
        return func

    def early(
        self, func: Callable[[ProxyContext], AsyncGenerator[None, Any]]
    ) -> Callable[[ProxyContext], AsyncGenerator[None, Any]]:
        """Register an early middleware that can yield.

        This middleware is registered as first, meaning the code before yield
        will act before any other one, but code after yield will execute the last.

        Args:
            func: The middleware function which yields.

        Returns:
            The decorated middleware function.
        """
        self.add_middleware(MiddlewarePhase.EARLY, func)
        return func

    def late(
        self, func: Callable[[ProxyContext], AsyncGenerator[None]]
    ) -> Callable[[ProxyContext], AsyncGenerator[None]]:
        """Register a late middleware that can yield.

        This middleware is registered the last.
        The code before yield will act after all other middlewares. The code after
        the yield runs before any other middleware.

        Args:
            func: The middleware function which yields.

        Returns:
            The decorated middleware function.
        """
        self.add_middleware(MiddlewarePhase.LATE, func)
        return func
