from aiohttp.web import Application, WebSocketResponse, WSMsgType


async def ws_echo_server(aiohttp_server):
    app = Application()

    async def ws_handler(request):
        ws = WebSocketResponse()
        await ws.prepare(request)

        while True:
            msg = await ws.receive()
            if msg.type == WSMsgType.TEXT:
                await ws.send_str(msg.data)
            elif msg.type == WSMsgType.BINARY:
                await ws.send_bytes(msg.data)
            elif msg.type == WSMsgType.PING:
                await ws.pong()
            elif msg.type in (
                WSMsgType.CLOSING,
                WSMsgType.CLOSED,
                WSMsgType.ERROR,
                WSMsgType.CLOSE,
            ):
                break

        ws.close()
        return ws

    app.add_routes("/{path:.*}", ws_handler)
    return aiohttp_server(app)
