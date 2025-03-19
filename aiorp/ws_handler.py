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


class WsProxyHandler(BaseHandler):
    """WebSocket handler"""

    def __init__(
        self,
        *args,
        message_handler: MessageHandler = None,
        client_message_handler: ClientMessageHandler = None,
        web_message_handler: WebMessageHandler = None,
        receive_timeout: int = 30,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        if self.connection_options is not None and "url" in self.connection_options:
            raise ValueError(
                "The connection options cannot contain the 'url', set it through context instead"
            )

        # Default timeout
        self._receive_timeout = receive_timeout

        if message_handler is not None and any(
            [client_message_handler, web_message_handler]
        ):
            raise ValueError(
                "You can either set message handler,"
                " or client_message_handler and web_message_handler, but not both"
            )

        self._client_message_handler = (
            client_message_handler or message_handler or self._client_to_target
        )
        self._web_message_handler = (
            web_message_handler or message_handler or self._target_to_client
        )
        self._active_sockets = set()

    async def __call__(self, request: web.Request):
        ws_client = web.WebSocketResponse()
        await ws_client.prepare(request)

        async with self._context.session.ws_connect(
            self._context.url,
            timeout=client.ClientWSTimeout(ws_receive=self._receive_timeout),
            **self.connection_options
        ) as ws_target:
            self._active_sockets.add((ws_client, ws_target))

            client_to_target = asyncio.create_task(
                self._client_message_handler(ws_client, ws_target)
            )
            target_to_client = asyncio.create_task(
                self._web_message_handler(ws_target, ws_client)
            )

            _, pending = await asyncio.wait(
                [client_to_target, target_to_client],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Close both sockets gracefully before cancelling tasks
            await ws_client.close()
            await ws_target.close()

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self._active_sockets.remove((ws_client, ws_target))

        return ws_client

    async def _sock_to_sock(self, ws_source: SocketResponse, ws_target: SocketResponse):
        """Forwards messages from source socket to target socket

        :param ws_source: Source socket
        :param ws_target: Target socket
        :raises Exception: If an unexpected exception occurs (not a timeout or connection error)
        """
        try:
            while True:
                try:
                    msg = await ws_source.receive()
                    if msg.type == web.WSMsgType.TEXT:
                        await ws_target.send_str(msg.data)
                    elif msg.type == web.WSMsgType.BINARY:
                        await ws_target.send_bytes(msg.data)
                    elif msg.type == web.WSMsgType.PING:
                        await ws_target.ping()
                    elif msg.type == web.WSMsgType.PONG:
                        await ws_target.pong()
                    elif msg.type == web.WSMsgType.CLOSE:
                        await ws_target.close()
                        break
                    elif msg.type in (
                        web.WSMsgType.CLOSING,
                        web.WSMsgType.CLOSED,
                        web.WSMsgType.ERROR,
                    ):
                        break
                except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                    # Connection likely broken, so we should close the target
                    if not ws_target.closed:
                        await ws_target.close(code=1001, message=b"Server disconnected")
                    break
        except Exception as e:
            # For any other exception, ensure we close the target socket
            if not ws_target.closed:
                await ws_target.close(code=1011, message=str(e).encode())
            raise

    async def _client_to_target(
        self, ws_client: SocketResponse, ws_target: SocketResponse
    ):
        """Forwards messages from client socket to target socket"""
        await self._sock_to_sock(ws_client, ws_target)

    async def _target_to_client(
        self, ws_target: SocketResponse, ws_client: SocketResponse
    ):
        """Forwards messages from target socket to client socket"""
        await self._sock_to_sock(ws_target, ws_client)

    async def terminate_sockets(self):
        """Closes all active sockets"""
        tasks = []
        for ws_client, ws_server in self._active_sockets:
            if not ws_client.closed:
                tasks.append(ws_client.close())
            if not ws_server.closed:
                tasks.append(ws_server.close())

        await asyncio.gather(*tasks)
