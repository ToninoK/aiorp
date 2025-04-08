import asyncio
from typing import Awaitable, Callable, Union

from aiohttp import client, web

from aiorp.base_handler import BaseHandler

SocketResponse = Union[web.WebSocketResponse, client.ClientWebSocketResponse]
MessageHandler = Callable[[SocketResponse, SocketResponse], Awaitable]
ClientMessageHandler = Callable[
    [web.WebSocketResponse, client.ClientWebSocketResponse], Awaitable
]
WebMessageHandler = Callable[
    [client.ClientWebSocketResponse, web.WebSocketResponse], Awaitable
]


class WsProxyHandler(BaseHandler):
    """WebSocket handler"""

    def __init__(
        self,
        *args,
        message_handler: MessageHandler | None = None,
        client_message_handler: ClientMessageHandler | None = None,
        web_message_handler: WebMessageHandler | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if self.connection_options is not None and "url" in self.connection_options:
            raise ValueError(
                "The connection options cannot contain the 'url', set it through context instead"
            )

        if message_handler is not None and any(
            [client_message_handler, web_message_handler]
        ):
            raise ValueError(
                "You can either set message_handler,"
                " or client_message_handler and web_message_handler, but not both"
            )

        self._default_timeout = client.ClientWSTimeout(ws_receive=30)
        self._client_message_handler = (
            client_message_handler or message_handler or self._sock_to_sock
        )
        self._web_message_handler = (
            web_message_handler or message_handler or self._sock_to_sock
        )
        self._active_sockets = set()

    async def __call__(self, request: web.Request):
        if self._context is None:
            raise ValueError("Proxy context must be set before the handler is invoked.")

        ws_client = web.WebSocketResponse()
        ws_target = await self._context.session.ws_connect(
            self._context.url, timeout=self._default_timeout, **self.connection_options
        )

        # Add sockets to active set
        socket_pair = (ws_client, ws_target)
        self._active_sockets.add(socket_pair)

        # Prepare client
        await ws_client.prepare(request)

        # Create and run message forwarding tasks
        client_to_target = asyncio.create_task(
            self._client_message_handler(ws_client, ws_target)
        )
        target_to_client = asyncio.create_task(
            self._web_message_handler(ws_target, ws_client)
        )

        # Wait for first task to complete
        _, pending = await asyncio.wait(
            [client_to_target, target_to_client],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Ensure both sockets are closed
        # This can happen when the user provided message handlers don't close the sockets
        await self._terminate_sockets(ws_client, ws_target)

        # Remove the socket pair from the active set
        self._active_sockets.remove(socket_pair)

        return ws_client

    async def _sock_to_sock(self, ws_source: SocketResponse, ws_target: SocketResponse):
        """Forwards messages from source socket to target socket

        When this function is finished, both sockets will be closed.

        :param ws_source: Source socket
        :param ws_target: Target socket
        :raises Exception: If an unexpected exception occurs (not a timeout or connection error)
        """
        try:
            # Forward messages from source to target
            await self._proxy_messages(ws_source, ws_target)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            # Connection might be broken, so we should close the target
            if not ws_target.closed:
                await ws_target.close(code=1001, message=b"Server disconnected")
        except Exception as e:
            # For unexpected exceptions, close the target socket
            if not ws_target.closed:
                await ws_target.close(code=1011, message=str(e).encode())
            raise
        finally:
            # Make sure the source socket is closed
            if not ws_source.closed:
                await ws_source.close()

    async def _proxy_messages(
        self, ws_source: SocketResponse, ws_target: SocketResponse
    ):
        """Forwards messages from source socket to target socket"""
        while True:
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
                if not ws_target.closed:
                    await ws_target.close(
                        code=msg.data.code,
                        message=msg.data.message if msg.data else b"",
                    )
                break
            elif msg.type in (
                web.WSMsgType.CLOSING,
                web.WSMsgType.CLOSED,
                web.WSMsgType.ERROR,
            ):
                break

    async def close_active_sockets(self):
        """Closes all active sockets"""
        for ws_client, ws_target in self._active_sockets:
            await self._terminate_sockets(ws_client, ws_target)

    @staticmethod
    async def _terminate_sockets(ws_source: SocketResponse, ws_target: SocketResponse):
        """Closes both sockets"""
        if not ws_source.closed:
            await ws_source.close()
        if not ws_target.closed:
            await ws_target.close()
