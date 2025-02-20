from aiohttp import web

from proxy.options import ProxyOptions
from proxy.request import ProxyRequest
from proxy.response import ProxyResponse, ResponseType

class ProxyHandler:
    """A handler for proxying requests to a remote server

    This handler is used to proxy requests to a remote server. It has a __call__ method that is used to handle incoming
    requests. The handler can be used as a route handler in an aiohttp.web application. It executes specified before and
    after handlers before and after the incoming request is proxied.

    :param proxy_options: The options to use when proxying requests
    :param rewrite_from: The path to rewrite from
    :param rewrite_to: The path to rewrite to
    :param preserve_upgrade: Whether to preserve the Upgrade header in the incoming request
    :param request_options: Additional options to pass to the handler. These options are passed as kwargs to the
        ProxyRequest.execute method, which is essentially a wrapper over aiohttp.ClientSession.request method.
        In simple terms these options are passed to the aiohttp request that will be made to the target server.
        Specifying
    """
    def __init__(self, proxy_options: ProxyOptions = None, rewrite_from=None, rewrite_to=None, preserve_upgrade=True, request_options: dict = None):
        self._proxy_options: ProxyOptions = proxy_options
        self._rewrite_from = rewrite_from
        self._rewrite_to = rewrite_to
        self._preserve_upgrade = preserve_upgrade

        if request_options is not None and any(
                key in request_options for key in ["method", "url", "headers", "params", "data"]
        ):
            raise ValueError(
                "The request options must not contain the method, url, headers, params or data keys.\n"
                "You can handle these directly by using the ProxyRequest object in the before handlers."
            )
        self.request_options = request_options or {}
        self.before_handlers = []
        self.after_handlers = []

    async def __call__(self, request: web.Request):
        if self._proxy_options is None:
            raise ValueError("Proxy options must be set before the handler is invoked.")
        proxy_request = ProxyRequest(
            url=self._proxy_options.url,
            in_req=request,
            rewrite_from=self._rewrite_from,
            rewrite_to=self._rewrite_to,
            preserve_upgrade=self._preserve_upgrade,
            proxy_attributes=self._proxy_options.attributes
        )
        for handler in self.before_handlers:
            handler(proxy_request)

        resp = await proxy_request.execute(self._proxy_options.session, **self.request_options)
        resp.raise_for_status()

        proxy_response = ProxyResponse(request, resp)
        for handler in self.after_handlers:
            handler(proxy_response)

        if not proxy_response.response:
            await proxy_response.set_response(response_type=ResponseType.BASE)

        return proxy_response.response

    @classmethod
    def merge(cls, *handlers, **kwargs):
        """Merge multiple handlers into a single handler

        Combines the before and after handlers of multiple handlers into a single handler.
        The kwargs are passed to the constructor of the merged handler.
        """
        merged_handlers = cls(**kwargs)

        for handler in handlers:
            merged_handlers.before_handlers.extend(handler.before_handlers)
            merged_handlers.after_handlers.extend(handler.after_handlers)

        return merged_handlers

    def update_request_options(self, **kwargs):
        """Update the request options for the handler

        Updates the request options for the handler. These options are passed to the ProxyRequest.execute method.
        """
        self.request_options.update(kwargs)

    def before(self):
        def inner(func):
            self.before_handlers.append(func)
            return func
        return inner

    def after(self):
        def inner(func):
            self.after_handlers.append(func)
            return func
        return inner

    async def close_session(self):
        await self._proxy_options.session.close()


"""
proxy_options = ProxyOptions(url=URL("http://example.com"), session=None, config={})

handler = ProxyHandler(proxy_options, rewrite_from="/proxy", rewrite_to="")

@handler.before
def prepare(request: ProxyRequest):
    print('Modify request')

@handler.after
def process(response: ProxyResponse):
    print('Modify response')
    
app = web.Application()
handler_routes = [
    web.get('/proxy/search', handler),
    web.get('/proxy/details', handler),
    web.get('/proxy/more', handler),
    web.get('/proxy/smth/{test}', handler),
]
app.router.add_routes(handler_routes)
"""
