from aiohttp import web

from proxy.context import ProxyRequest
from proxy.config import ProxyOptions

class ProxyHandler:
    def __init__(self, proxy_options: ProxyOptions, rewrite_from=None, rewrite_to=None, preserve_upgrade=True, **kwargs):
        self._proxy_options: ProxyOptions = proxy_options
        self._rewrite_from = rewrite_from
        self._rewrite_to = rewrite_to
        self._preserve_upgrade = preserve_upgrade
        self._execute_options = kwargs.get("execute_options", {})

        self._before_handlers = []
        self._after_handlers = []


    async def __call__(self, request: web.Request):
        proxy_request = ProxyRequest(
            url=self._proxy_options.url,
            in_req=request,
            rewrite_from=self._rewrite_from,
            rewrite_to=self._rewrite_to,
            preserve_upgrade=self._preserve_upgrade,
        )
        for handler in self._before_handlers:
            handler(proxy_request)

        with self._proxy_options.session as session:
            resp = await proxy_request.execute(session, **self._execute_options)

    def before(self):
        def inner(func):
            self._before_handlers.append(func)
            return func
        return inner

    def after(self):
        def inner(func):
            self._after_handlers.append(func)
            return func
        return inner


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
