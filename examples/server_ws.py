from aiohttp import web


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    while True:
        msg = await ws.receive()
        if msg.type == web.WSMsgType.TEXT:
            await ws.send_str(f"Server received: {msg.data}")
        elif msg.type == web.WSMsgType.BINARY:
            await ws.send_bytes(msg.data)
        elif msg.type == web.WSMsgType.ERROR:
            break
        elif msg.type == web.WSMsgType.CLOSE:
            break

    return ws


app = web.Application()
app.router.add_route("GET", "/ws", websocket_handler)

if __name__ == "__main__":
    web.run_app(app, port=8765)
