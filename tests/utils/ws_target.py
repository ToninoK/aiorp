from aiohttp import WSMsgType, web


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            if msg.data == "close":
                await ws.close()
                break
            if msg.data == "error":
                raise Exception("Target error")
            await ws.send_str(f"received: {msg.data}")
        elif msg.type == WSMsgType.BINARY:
            await ws.send_bytes(f"received: {msg.data}".encode())
        elif msg.type == WSMsgType.PING:
            await ws.pong()
        elif msg.type == WSMsgType.ERROR:
            if exc := ws.exception():
                raise exc
    return ws


def app():
    app = web.Application()

    app.add_routes(
        [
            web.get("/", ws_handler),
        ]
    )
    return app
