import asyncio
import copy
from typing import Awaitable, Callable, Union

from aiohttp import client, web

from aiorp.base_handler import BaseHandler
from aiorp.context import ProxyContext

SocketResponse = Union[web.WebSocketResponse, client.ClientWebSocketResponse]
MessageHandler = Callable[[SocketResponse, SocketResponse], Awaitable]
ClientMessageHandler = Callable[
    [web.WebSocketResponse, client.ClientWebSocketResponse], Awaitable
]
WebMessageHandler = Callable[
    [client.ClientWebSocketResponse, web.WebSocketResponse], Awaitable
]


class WsProxyHandler(BaseHandler):
    """WebSocket handler."""

    def __init__(
        self,
        *args,
        proxy_tunnel: Callable[[ProxyContext], Awaitable] | None = None,
        **kwargs,
    ):
        """Initialize the WebSocket proxy handler.

        Args:
            *args: Variable length argument list.
            message_handler: Optional handler for all message types.
            client_message_handler: Optional handler for client messages.
            web_message_handler: Optional handler for web messages.
            **kwargs: Arbitrary keyword arguments.

        Raises:
            ValueError: If connection options contain 'url' or if both message_handler and
                client/web_message_handlers are specified.
        """
        super().__init__(*args, **kwargs)

        if self.connection_options is not None and "url" in self.connection_options:
            raise ValueError(
                "The connection options cannot contain the 'url', set it through context instead"
            )

        self._default_timeout = client.ClientWSTimeout(ws_receive=30)
        self._proxy_tunnel = proxy_tunnel or self._default_proxy_tunnel

    async def __call__(self, request: web.Request):
        if self.context is None:
            raise ValueError("Proxy context must be set before the handler is invoked.")

        ctx = copy.copy(self.context)

        ws_source = web.WebSocketResponse()
        ws_target = await ctx.session.ws_connect(
            ctx.url, timeout=self._default_timeout, **self.connection_options
        )
        ctx.set_socket_pair(ws_source=ws_source, ws_target=ws_target)

        await ctx.ws_source.prepare(request)

        await self._default_proxy_tunnel(ctx)

        await ctx.terminate_sockets()

        return ws_source

    async def _default_proxy_tunnel(self, ctx: ProxyContext):
        if not ctx.ws_target or not ctx.ws_source:
            raise ValueError("Sockets must be set before tunneling can start")

        # Create and run message forwarding tasks
        source_to_target = asyncio.create_task(
            self._sock_to_sock(ctx.ws_source, ctx.ws_target)
        )
        target_to_source = asyncio.create_task(
            self._sock_to_sock(ctx.ws_target, ctx.ws_source)
        )

        # Wait for first task to complete
        _, pending = await asyncio.wait(
            [source_to_target, target_to_source],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _sock_to_sock(self, ws_source: SocketResponse, ws_target: SocketResponse):
        """Forwards messages from source socket to target socket.

        When this function is finished, both sockets will be closed.

        Args:
            ws_source: Source socket.
            ws_target: Target socket.

        Raises:
            Exception: If an unexpected exception occurs (not a timeout or connection error).
        """
        try:
            # Forward messages from source to target
            await self._proxy_messages(ws_source, ws_target)
        except asyncio.TimeoutError:
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
        """Forwards messages from source socket to target socket.

        Args:
            ws_source: Source socket.
            ws_target: Target socket.
        """
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
