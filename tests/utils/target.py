from aiohttp import web


async def dump_data(request: web.Request):
    return web.json_response(
        {
            "_id": "680f5dfe0bf1efde2f3e7e51",
            "index": 0,
            "guid": "d96c062b-d12c-48a2-b8f6-ee2993ae9981",
            "isActive": True,
            "balance": "$2,841.06",
            "picture": "http://placehold.it/32x32",
            "age": 39,
            "eyeColor": "green",
            "name": "Duncan Raymond",
            "gender": "male",
            "company": "CUBICIDE",
            "email": "duncanraymond@cubicide.com",
        }
    )


async def ping(request: web.Request) -> web.Response:
    return web.Response(text="pong")


async def yell(request: web.Request):
    return web.Response(text=f"{request.path}!!!")


async def store_data(request: web.Request) -> web.Response:
    data = await request.json()
    return web.Response(body=data)


async def return_error(request: web.Request) -> web.Response:
    raise web.HTTPConflict(reason="Conflict error")


async def internal_error(request: web.Request) -> web.Response:
    raise Exception("Big bad thing!")


def app():
    app = web.Application()

    app.add_routes(
        [
            web.get("/", ping),
            web.get("/yell_path", yell),
            web.get("/dump/data", dump_data),
            web.post("/upload", store_data),
            web.get("/error", return_error),
            web.get("/error/internal", internal_error),
        ]
    )
    return app
