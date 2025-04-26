import asyncio
import copy
from typing import Awaitable, Callable, Union

from aiohttp import WSCloseCode, client, web
from aiohttp.client_exceptions import ClientConnectorSSLError

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
        receive_timeout: int = 30,
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

        if self.request_options is not None and "url" in self.request_options:
            raise ValueError(
                "The connection options cannot contain the 'url', set it through context instead"
            )

        self._default_timeout = client.ClientWSTimeout(ws_receive=receive_timeout)
        self._proxy_tunnel = proxy_tunnel or self._default_proxy_tunnel

    async def __call__(self, request: web.Request):
        """The handler that should be set on an endpoint

        The handler:
          - opies the context, updates the path if needed, prepares the source socket,
        sets up
        """
        # Make sure the context is set up
        if self.context is None:
            raise ValueError("Proxy context must be set before the handler is invoked.")

        # Copy the context so it is separate per request
        ctx = copy.copy(self.context)
        ctx.set_request(request)

        # Rewrite path if specified
        if self._rewrite:
            ctx.request.rewrite_path(
                self._rewrite.rfrom,
                self._rewrite.rto,
            )
        # Prepare the source websocket
        ws_source = web.WebSocketResponse()
        await ws_source.prepare(ctx.request.in_req)

        try:
            # Attempt to connect with wss
            ctx.request.url = ctx.request.url.with_scheme("wss")
            ws_target = await ctx.session.ws_connect(
                ctx.request.url, timeout=self._default_timeout, **self.request_options
            )
        except ClientConnectorSSLError:
            # Fallback to ws
            ctx.request.url = ctx.request.url.with_scheme("ws")
            ws_target = await ctx.session.ws_connect(
                ctx.request.url, timeout=self._default_timeout, **self.request_options
            )
        # Set the socket pair in the context
        ctx.set_socket_pair(ws_source=ws_source, ws_target=ws_target)

        # Use the default proxy tunnel
        await self._proxy_tunnel(ctx)

        # Terminate the sockets
        await ctx.terminate_sockets()

        return ws_source

    async def _default_proxy_tunnel(self, ctx: ProxyContext):
        """The default logic for forwarding messages between two sockets

        Args:
            ctx: The ProxyContext accessible for handling the tunneling
        Raises:
            ValueError: When the tunneling starts before sockets are set (very unlikely)
        """

        if ctx.ws_target is None or ctx.ws_source is None:
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
        except asyncio.TimeoutError as e:
            print(e)
            # Connection might be broken, so we should close the target
            if not ws_target.closed:
                await ws_target.close(
                    code=WSCloseCode.GOING_AWAY,
                    message=b"Other socket timed out, going away.",
                )
        except Exception as e:
            print(e)
            # For unexpected exceptions, close the target socket
            if not ws_target.closed:
                await ws_target.close(
                    code=WSCloseCode.INTERNAL_ERROR, message=str(e).encode()
                )
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
            elif msg.type in (
                web.WSMsgType.CLOSE,
                web.WSMsgType.CLOSING,
                web.WSMsgType.CLOSED,
                web.WSMsgType.ERROR,
            ):
                if not ws_target.closed:
                    await ws_target.close(
                        code=WSCloseCode.GOING_AWAY,
                        message=b"Other socket will not communicate any further, going away.",
                    )
                break
