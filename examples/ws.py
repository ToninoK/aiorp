from aiohttp import web
from yarl import URL

from aiorp.context import ProxyContext
from aiorp.ws_handler import WebSocketProxyHandler

app = web.Application()

# Create an instance of the WebSocket proxy handler
context = ProxyContext(url=URL("http://localhost:8765/ws"))
ws_handler = WebSocketProxyHandler(context)

# Add a route for WebSocket connections
app.router.add_route("GET", "/ws", ws_handler)


async def shutdown(_app):
    # Close the session when the application is shutting down
    await ws_handler.terminate_sockets()
    await context.close_session()


app.on_shutdown.append(shutdown)
# Run the application
if __name__ == "__main__":
    web.run_app(app, port=8080)
