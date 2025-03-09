import asyncio
from bisect import insort
from collections import defaultdict
from enum import IntEnum
from typing import Any, Awaitable, Callable, List

from aiohttp import ClientResponseError, client, web
from aiohttp.web_exceptions import HTTPInternalServerError

from aiorp.context import ProxyContext
from aiorp.request import ProxyRequest
from aiorp.response import ProxyResponse, ResponseType

ErrorHandler = Callable[[ClientResponseError], None]
BeforeHandler = Callable[[ProxyRequest], Awaitable]
AfterHandler = Callable[[ProxyResponse], Awaitable]


class Priority(IntEnum):
    """Handler priority enumeration"""

    HIGHEST = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    LOWEST = 4


class PriorityCollection:
    """Dict-like object for storing items with priorities

    The collection stores items while keeping track of their priority. Items with the
    same priority are stored in a list. Iterating over the collection will yield the
    lists of items in the order of their priority.
    """

    def __init__(self):
        self._handlers = defaultdict(list)
        self._priorities = []

    def __getitem__(self, priority: Priority) -> List:
        return self._handlers[priority]

    def add(self, priority: Priority, value: Any):
        self._handlers[priority].append(value)
        insort(self._priorities, priority)

    def __iter__(self):
        """Iterate over the priorities in the collection"""
        for priority in self._priorities:
            yield priority

    def values(self):
        """Iterate over the values in the collection in the order of their priority"""
        for priority in self._priorities:
            yield self._handlers[priority]

    def keys(self):
        """Iterate over the priorities the collection"""
        for priority in self._priorities:
            yield priority

    def items(self):
        """Iterate over the items in the collection"""
        for priority in self._priorities:
            yield priority, self._handlers[priority]

    def merge(
        self,
        handler_collection: "PriorityCollection",
    ):
        """Merge another collection into this collection"""
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
    It executes specified before and after handlers, before and after the
    incoming request is proxied.

    :param proxy_options: The options to use when proxying requests
        Defines the URL to proxy requests to and the session to use. It can be None at init, but
        it must be set before attempting to proxy a request.
    :param rewrite_from: The path to rewrite from, if specified rewrite_to must also be set
    :param rewrite_to: The path to rewrite to, if specified rewrite_from must also be set
    :param error_handler: Callable that is called when an error occurs during the proxied request
    :param request_options: Additional options for making the request.
        The specified options are passed to the aiohttp `ClientSession.request` method.
        The options can't contain the following keys: method, url, headers, params, data.
        Those parameters are to be managed through the ProxyRequest object in the before handlers.

    :raises: ValueError
    """

    def __init__(
        self,
        context: ProxyContext = None,
        rewrite_from=None,
        rewrite_to=None,
        error_handler: ErrorHandler = None,
        request_options: dict = None,
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

        self._context: ProxyContext = context
        self._rewrite_from = rewrite_from
        self._rewrite_to = rewrite_to
        self._error_handler = error_handler

        self.request_options = request_options or {}
        self.before_handlers = PriorityCollection()
        self.after_handlers = PriorityCollection()

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
            proxy_attributes=self._context.attributes,
        )

        # Check if the path should be rewritten and do so
        if self._rewrite_from and self._rewrite_to:
            proxy_request.rewrite_path(
                self._rewrite_from,
                self._rewrite_to,
            )

        # Execute the before request handlers
        for handlers in self.before_handlers.values():
            await asyncio.gather(*(handler(proxy_request) for handler in handlers))

        # Execute the request and check the response
        resp = await proxy_request.execute(
            self._context.session,
            **self.request_options,
        )
        self._raise_for_status(resp)

        # Build the proxy response object from the target response
        proxy_response = ProxyResponse(
            in_req=request,
            in_resp=resp,
            proxy_attributes=self._context.attributes,
        )
        # Execute the after response handlers
        for handlers in self.after_handlers.values():
            await asyncio.gather(*(handler(proxy_response) for handler in handlers))

        # If the response has not been set, set it using the base response type
        if not proxy_response.response:
            await proxy_response.set_response(response_type=ResponseType.BASE)

        # Return the response
        return proxy_response.response

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
        priority: Priority | int = Priority.HIGHEST,
    ) -> Callable[[BeforeHandler], BeforeHandler]:
        """Decorator to add a before handler to the proxy handler

        :param priority: The priority of the handler which defines order of execution.
            You can use the Priority enum to set the priority, or a simple integer. Keep in mind
            that lower numbers mark a higher priority. Default is Priority.HIGHEST.
        :returns: A decorator that adds the function to the before handlers collection
        """

        def inner(func: BeforeHandler):
            self.before_handlers.add(priority=priority, value=func)
            return func

        return inner

    def after(
        self,
        priority: Priority | int = Priority.HIGHEST,
    ) -> Callable[[AfterHandler], AfterHandler]:
        """Decorator to add an after handler to the proxy handler

        :param priority: The priority of the handler which defines order of execution.
            You can use the Priority enum to set the priority, or a simple integer. Keep in mind
            that lower numbers mark a higher priority. Default is Priority.HIGHEST.
        :returns: A decorator that adds the function to the after handlers collection
        """

        def inner(func: AfterHandler):
            self.after_handlers.add(priority=priority, value=func)
            return func

        return inner

    def add_before(self, priority: Priority, func: BeforeHandler):
        """Add a before handler to the proxy handler

        :param priority: The priority of the handler which defines order of execution.
            You can use the Priority enum to set the priority, or a simple integer. Keep in mind
            that lower numbers mark a higher priority. Default is Priority.HIGHEST.
        :param func: The function to add to the before handlers collection
        :returns: None
        """
        self.before_handlers.add(priority, func)

    def add_after(self, priority: Priority, func: AfterHandler):
        """Add an after handler to the proxy handler

        :param priority: The priority of the handler which defines order of execution.
            You can use the Priority enum to set the priority, or a simple integer. Keep in mind
            that lower numbers mark a higher priority. Default is Priority.HIGHEST.
        :param func: The function to add to the after handlers collection
        :returns: None
        """
        self.after_handlers.add(priority, func)
