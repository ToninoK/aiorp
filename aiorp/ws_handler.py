import asyncio
from typing import Awaitable, Callable, Union

from aiohttp import client, web

from aiorp.base_handler import BaseHandler

SocketResponse = Union[web.WebSocketResponse, client.ClientWebSocketResponse]
MessageHandler = Callable[[SocketResponse, SocketResponse], Awaitable]
ClientMessageHandler = Callable[
    [client.ClientWebSocketResponse, web.WebSocketResponse], Awaitable
]
WebMessageHandler = Callable[
    [web.WebSocketResponse, client.ClientWebSocketResponse], Awaitable
]


class WebSocketProxyHandler(BaseHandler):
    """WebSocket handler"""

    def __init__(
        self,
        *args,
        message_handler: MessageHandler = None,
        client_message_handler: ClientMessageHandler = None,
        web_message_handler: WebMessageHandler = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        if self.connection_options is not None and "url" in self.connection_options:
            raise ValueError(
                "The connection options cannot contain the 'url', set it through context instead"
            )

        # Default timeout
        self._receive_timeout = 30

        if message_handler is not None and any(
            [client_message_handler, web_message_handler]
        ):
            raise ValueError(
                "You can either set message handler,"
                " or client_message_handler and web_message_handler, but not both"
            )

        self._client_message_handler = (
            client_message_handler or message_handler or self._sock_to_sock
        )
        self._web_message_handler = (
            web_message_handler or message_handler or self._sock_to_sock
        )
        self._active_sockets = set()

    async def __call__(self, request: web.Request):
        ws_server = web.WebSocketResponse()
        await ws_server.prepare(request)

        async with self._context.session.ws_connect(
            self._context.url,
            receive_timeout=self._receive_timeout,
            **self.connection_options
        ) as ws_client:
            client_to_server = asyncio.create_task(
                self._client_message_handler(ws_client, ws_server)
            )
            server_to_client = asyncio.create_task(
                self._web_message_handler(ws_server, ws_client)
            )

            self._active_sockets.add((ws_client, ws_server))
            _, pending = await asyncio.wait(
                [client_to_server, server_to_client],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel remaining tasks
            # When one socket disconnects we want to clean up the other one
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            if not ws_client.closed:
                await ws_client.close()
            if not ws_server.closed:
                await ws_server.close()

            self._active_sockets.remove((ws_client, ws_server))

        return ws_server

    @staticmethod
    async def _sock_to_sock(source: SocketResponse, destination: SocketResponse):
        while True:
            msg = await source.receive()
            if msg.type == web.WSMsgType.TEXT:
                await destination.send_str(msg.data)
            elif msg.type == web.WSMsgType.BINARY:
                await destination.send_bytes(msg.data)
            elif msg.type in (
                web.WSMsgType.CLOSE,
                web.WSMsgType.CLOSING,
                web.WSMsgType.CLOSED,
                web.WSMsgType.ERROR,
            ):
                break

    async def terminate_sockets(self):
        tasks = []
        for ws_client, ws_server in self._active_sockets:
            if not ws_client.closed:
                tasks.append(ws_client.close())
            if not ws_server.closed:
                tasks.append(ws_server.close())

        await asyncio.gather(*tasks)
