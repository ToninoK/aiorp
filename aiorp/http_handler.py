import asyncio
import json
import logging
from collections import defaultdict
from enum import IntEnum
from typing import Awaitable, Callable

from aiohttp import ClientResponseError, client, web
from aiohttp.web_exceptions import HTTPInternalServerError

from aiorp.base_handler import BaseHandler
from aiorp.context import ProxyContext
from aiorp.request import ProxyRequest
from aiorp.response import ProxyResponse, ResponseType

log = logging.getLogger(__name__)

ErrorHandler = Callable[[ClientResponseError], None] | None
ProxyMiddleware = Callable[[ProxyContext], Awaitable]


class MiddlewarePhase(IntEnum):
    """Middleware phase enumeration"""

    EARLY = 0  # Authentication, security checks
    STANDARD = 500  # Logging, tracking, most transformations
    LATE = 1000  # Anything you might want to execute last before request is sent out


class HttpProxyHandler(BaseHandler):
    """A handler for proxying requests to a remote server

    This handler is used to proxy requests to a remote server.
    It has a __call__ method that is used to handle incoming requests.
    The handler can be used as a route handler in an aiohttp.web application.
    It executes specified before and after handlers, before and after the
    incoming request is proxied.

    :param error_handler: Callable that is called when an error occurs during the proxied request
    :param context: The options to use when proxying requests
        Defines the URL to proxy requests to and the session to use. It can be None at init, but
        it must be set before attempting to proxy a request.
    :param rewrite_from: The path to rewrite from, if specified rewrite_to must also be set
    :param rewrite_to: The path to rewrite to, if specified rewrite_from must also be set
    :param connection_options: Additional options for establishing the session connection.

    :raises: ValueError
    """

    def __init__(self, *args, error_handler: ErrorHandler = None, **kwargs):
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

    async def __call__(self, request: web.Request) -> web.StreamResponse | web.Response:
        """Handle incoming requests

        This method is called when the handler is used as a route handler in an aiohttp.web app.
        It executes the before handlers, proxies the request, and executes the after handlers.
        If an error occurs during the external request, the error_handler is invoked if set,
        otherwise an HTTPInternalServerError is raised.

        :param request: The incoming request to proxy
        :returns: The response from the external server
        :raises: ValueError, HTTPInternalServerError
        """
        if self._context is None:
            raise ValueError("Proxy context must be set before the handler is invoked.")

        # Build the proxy request object
        proxy_request = ProxyRequest(
            url=self._context.url,
            in_req=request,
        )

        # Check if the path should be rewritten and do so
        if self._rewrite_from and self._rewrite_to:
            proxy_request.rewrite_path(
                self._rewrite_from,
                self._rewrite_to,
            )

        self._context.request = proxy_request

        # Execute the middleware chain
        await self._execute_middleware_chain()

        if self._context.response is None:
            raise ValueError("Response not set")

        try:
            await self._context.response.set_response(response_type=ResponseType.BASE)
        except ValueError:
            pass
        # Return the response
        return self._context.response.web

    async def _execute_middleware_chain(self):
        """Execute the entire provided middleware chain.

        The chain is executed in order the middlewares were registered,
        with the pre-yield code executing in that order, and the post-yield
        executing in reverse order ("russian doll model").
        """
        sorted_middlewares = sorted(self._middlewares.keys())
        middleware_generators = defaultdict(list)

        # Start all middleware generators and store them
        for order_key in sorted_middlewares:
            middleware_funcs = self._middlewares[order_key]
            generators = [func(self._context).__aiter__() for func in middleware_funcs]
            await asyncio.gather(
                *[gen.__anext__() for gen in generators], return_exceptions=True
            )
            middleware_generators[order_key] = generators

        # Execute the actual request
        await self._proxy_middleware(self._context)

        # Resume all middleware generators in reverse order
        for order_key in reversed(sorted_middlewares):
            await asyncio.gather(
                *[gen.__anext__() for gen in middleware_generators[order_key]]
            )

    async def _proxy_middleware(self, context: ProxyContext):
        """The default final middleware in the middleware chain.

        It executes after all other user provided middlewares, and
        it proxies the request to the target destination.

        :param context: The proxy context holding the request and response information
        """
        if context.request is None:
            raise ValueError("ProxyRequest not set")
        # Execute the request and check the response
        resp = await context.request.execute(
            context.session,
            **self.connection_options,
        )
        self._raise_for_status(resp)

        # Build the proxy response object from the target response
        context.response = ProxyResponse(in_resp=resp)

    def _raise_for_status(self, response: client.ClientResponse):
        """Check status of request and handle the error properly

        In case of an error, the error_handler is called if set, otherwise an
        HTTPInternalServerError is raised with the error message.

        :param response: The response from the external server
        :returns: None
        :raises: HTTPInternalServerError
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

    def middleware(self, order=MiddlewarePhase.STANDARD):
        """Register a middleware with explicit ordering

        It will be registered depending on the order and relative to
        other defined middlewares. A lower number means sooner registration,
        while a higher number results in a later registration.

        :param order: Integer representing order of middleware registration.
        """

        def decorator(func):
            self._middlewares[order].append(func)
            return func

        return decorator

    def early(self, func: Callable[[ProxyContext], Awaitable]):
        """Register an early middleware that can yield

        This middleware is registered as first, meaning the code before yield
        will act before any other one, but code after yield will execute the last.

        :param func: The middlware function which yields
        """
        return self.middleware(MiddlewarePhase.EARLY)(func)

    def standard(self, func: Callable[[ProxyContext], Awaitable]):
        """Register a standard middleware that can yield

        This middleware is registered between the early and late middleware.
        The code before yield will act after the early middleware, but before
        late middleware. The code after yield acts after middleware registered late
        but before middleware registered early.

        :param func: The middlware function which yields
        """
        return self.middleware(MiddlewarePhase.STANDARD)(func)

    def late(self, func: Callable[[ProxyContext], Awaitable]):
        """Register a late middleware that can yield

        This middleware is registered the last.
        The code before yield will act after all other middlewares. The code after
        the yield runs before any other middleware.

        :param func: The middleware function which yields
        """
        return self.middleware(MiddlewarePhase.LATE)(func)
