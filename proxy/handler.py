import asyncio
from bisect import insort
from collections import defaultdict
from enum import IntEnum
from typing import Callable

from aiohttp import ClientResponseError, client, web
from aiohttp.web_exceptions import HTTPInternalServerError

from proxy.options import ProxyOptions
from proxy.request import ProxyRequest
from proxy.response import ProxyResponse, ResponseType

ErrorHandler = Callable[[ClientResponseError], None]


class HandlerPriority(IntEnum):
    """Handler priority enumeration"""

    HIGHEST = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    LOWEST = 4


class HandlerCollection:
    """Dict-like object for storing handlers with priorities"""

    def __init__(self):
        self._handlers = defaultdict(list)
        self._priorities = []

    def __getitem__(self, priority: HandlerPriority):
        return self._handlers[priority]

    def __setitem__(self, priority: HandlerPriority, value):
        self._handlers[priority] = value
        insort(self._priorities, priority)

    def __iter__(self):
        for priority in self._priorities:
            yield from self._handlers[priority]

    def items(self):
        for priority in self._priorities:
            yield priority, self._handlers[priority]

    def merge(
        self,
        handler_collection: "HandlerCollection",
    ):
        for (
            priority,
            handlers,
        ) in handler_collection.items():
            self._handlers[priority].extend(handlers)
            insort(self._priorities, priority)


class ProxyHandler:
    """A handler for proxying requests to a remote server

    This handler is used to proxy requests to a remote server.
    It has a __call__ method that is used to handle incoming requests.
    The handler can be used as a route handler in an aiohttp.web application.
    It executes specified before and after handlers before and after the
    incoming request is proxied.

    :param proxy_options: The options to use when proxying requests
    :param rewrite_from: The path to rewrite from
    :param rewrite_to: The path to rewrite to
    :param request_options: Additional options to pass to the handler.
        These options are passed as kwargs to the ProxyRequest.execute method,
        which is essentially a wrapper over aiohttp.ClientSession.request method.
        In simple terms these options are passed to the aiohttp request that will
        be made to the target server.
    :param error_handler: A callable that is called when an error occurs during the request
    """

    def __init__(
        self,
        proxy_options: ProxyOptions = None,
        rewrite_from=None,
        rewrite_to=None,
        request_options: dict = None,
        error_handler: ErrorHandler = None,
    ):

        if (rewrite_from and rewrite_to is None) or (
            rewrite_to and rewrite_from is None
        ):
            raise ValueError("Both rewrite_from and rewrite_to must be set, or neither")

        if request_options is not None and any(
            key in request_options
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

        self._proxy_options: ProxyOptions = proxy_options
        self._rewrite_from = rewrite_from
        self._rewrite_to = rewrite_to
        self._error_handler = error_handler

        self.request_options = request_options or {}
        self.before_handlers = HandlerCollection()
        self.after_handlers = HandlerCollection()

    async def __call__(self, request: web.Request):
        if self._proxy_options is None:
            raise ValueError("Proxy options must be set before the handler is invoked.")
        proxy_request = ProxyRequest(
            url=self._proxy_options.url,
            in_req=request,
            proxy_attributes=self._proxy_options.attributes,
        )

        if self._rewrite_from and self._rewrite_to:
            proxy_request.rewrite_path(
                self._rewrite_from,
                self._rewrite_to,
            )

        for handlers in self.before_handlers:
            await asyncio.gather(*(handler(proxy_request) for handler in handlers))

        resp = await proxy_request.execute(
            self._proxy_options.session,
            **self.request_options,
        )
        self._raise_for_status(resp)

        proxy_response = ProxyResponse(
            in_req=request,
            in_resp=resp,
            proxy_attributes=self._proxy_options.attributes,
        )
        for handlers in self.after_handlers:
            await asyncio.gather(*(handler(proxy_response) for handler in handlers))

        if not proxy_response.response:
            await proxy_response.set_response(response_type=ResponseType.BASE)

        return proxy_response.response

    def _raise_for_status(self, response: client.ClientResponse):
        try:
            response.raise_for_status()
        except ClientResponseError as err:
            if self._error_handler:
                self._error_handler(err)
            raise HTTPInternalServerError(
                reason="External API Error",
                body={
                    "status": err.status,
                    "message": err.message,
                },
            )

    @classmethod
    def merge(cls, *handlers, **kwargs):
        """Merge multiple handlers into a single handler

        Combines the before and after handlers of multiple handlers into a single handler.
        The kwargs are passed to the constructor of the merged handler.
        """
        merged_handlers = cls(**kwargs)

        for proxy_handler in handlers:
            merged_handlers.before_handlers.merge(proxy_handler.before_handlers)
            merged_handlers.after_handlers.merge(proxy_handler.after_handlers)

        return merged_handlers

    def update_request_options(self, **kwargs):
        """Update the request options for the handler

        Updates the request options for the handler.
        These options are passed to the ProxyRequest.execute method.
        """
        self.request_options.update(kwargs)

    def before(
        self,
        priority: HandlerPriority | int = HandlerPriority.HIGHEST,
    ):
        def inner(func):
            self.before_handlers[priority] = func
            return func

        return inner

    def after(
        self,
        priority: HandlerPriority | int = HandlerPriority.HIGHEST,
    ):
        def inner(func):
            self.after_handlers[priority] = func
            return func

        return inner
