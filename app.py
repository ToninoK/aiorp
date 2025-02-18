from aiohttp import web

app = web.Application()

class Test:
    async def __call__(self, request):
        return web.Response(text="Hello, world")


test = Test()

app.add_routes(routes=[web.get('/', test)])

web.run_app(app)
