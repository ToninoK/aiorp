from aiohttp import WSMsgType, web


async def websocket_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            if msg.data == "close":
                await ws.close()
            else:
                await ws.send_str(msg.data + "/answer")
        elif msg.type == WSMsgType.ERROR:
            print("ws connection closed with exception %s" % ws.exception())

    print("websocket connection closed")

    return ws


app = web.Application()
app.add_routes(
    [
        web.get("/", websocket_handler),
    ]
)


web.run_app(app, port=8181)
