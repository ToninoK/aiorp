---
hide:
  - navigation
---

# Tutorial

This is a more extensive run-through of the package functionality. In this
guide we'll set up an reverse-proxy with the following requirements:

- Proxy requests to two target servers
- Different authentication to different servers
- The application should also be behind its own authentication
- Support compressing response for the user

!!! info "Already bored?"

    Don't feel like listening to me yap? You can jump to the prepared example
    found [here](https://github.com/ToninoK/aiorp/tree/master/examples/tutorial)

## Scenario

Let's take the scenario of an ERP platform. It has multiple partners which
manage their business through it. An ERP system is complex enough for it to
need multiple different services, rather than a large monolithic service.
So the platform likely needs a reverse-proxy in front of its services to handle
the partner authentication and serve all of its content from a single point of
entry.

For our scenario, we'll look at two services an ERP would need to provide:

- Content storage
- Transactions

These will be the target services we will proxy with our reverse-proxy.

## Target servers

The prerequisite to our proxy is obviously something to proxy the requests to.
Not to lose time on writing these, since it's not the point of the exercise,
you can find the codes for the two example servers
[here](https://github.com/ToninoK/aiorp/tree/master/examples/proxy/targets).

Take some time to inspect them, see what endpoints they expose, and how they
work. TL;DR: they have some CRUD endpoints expecting

## Environment

Let's initialize the environment first and install the package.
In this guide we'll use [`uv`](https://github.com/astral-sh/uv) for managing
our dependencies. The following commands will create an environment and install
the package inside it.

```bash
uv init aiorp-example --bare
cd aiorp-example
uv add aiorp pyjwt
source .venv/bin/activate
```

!!! info "Tooling"

    You'll see me using `http` commands in the shell. I'm using
    [`httpie`](https://httpie.io/) for testing but you can use
    `curl` or whatever tool you feel comfortable with

## Folder structure

Let's prepare our folder structure

```tree
proxy/
├── src/
│   ├── middlewares/              # The shared proxy middlewares
│   ├── routers/                  # The routers for our target servers
│   ├── utils/                    # Utility functionality we might need
│   └── app.py                    # Main application entry point
├── pyproject.toml                # Project dependencies
└── uv.lock                       # Locked dependencies
```

Having prepared our structure we're ready to start writing our app.

## The AIOHTTP app

Let's start by creating our AIOHTTP application.
Create a new file `src/app.py` with the following content:

```python
from aiohttp import web


def create_app() -> web.Application:
    """Create and configure the application"""
    app = web.Application()

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="localhost", port=8080)
```

We did no special magic we just configured our application.
You can try running it with:

```bash
python3 -m src.app
```

## Authentication

Let's add some authentication to it. In the `src/utils` folder create a file
called `auth.py`.

```python
from datetime import datetime, timedelta, timezone

import jwt
from aiohttp import web


JWT_SECRET = "your-super-secret-jwt-key"  # (1)
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 3600  # 1hr


USERS = {  # (2)!
    "WAL001": {
        "password": "wal001",
        "role": "user",
    },
}


def create_token(user_id: str) -> str:  # (3)!
    """Create a new JWT token for the user"""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(tz=timezone.utc) + timedelta(seconds=JWT_EXP_DELTA_SECONDS),
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:  # (4)!
    """Verify the JWT token and return the payload"""
    try:
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM], verify_exp=True
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise web.HTTPUnauthorized(reason="Token has expired")
    except jwt.InvalidTokenError:
        raise web.HTTPUnauthorized(reason="Invalid token")
```

1. :shushing_face: `openssl rand -hex 32`
2. In the real world please don't use a dictionary :sweat_smile:
3. Simple function which takes the user_id and creates a token with the user_id.
4. Function that tries to decode the token and verify that it isn't expired

Our file has some simple functionality to generate and verify a generated token.
Let's put some of it to use in our `app.py` file.

```python
from aiohttp import web
from src.utils.auth import USERS, create_token


async def login(request):
    """Handle user login"""
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise web.HTTPBadRequest(reason="Username and password are required")

    user = USERS.get(username)
    if not user or user["password"] != password:
        raise web.HTTPUnauthorized(reason="Invalid username or password")

    token = create_token(username)
    return web.json_response(
        {"token": token, "user": {"username": username, "role": user["role"]}}
    )

def create_app() -> web.Application:
  app = web.Application()

  app.router.add_post("/login", login)

  return app
#...
```

Great! Our app now has authentication. You can run the server and test it:

```bash
http POST localhost:8080/login username=WAL001 password=wal001
```

You can store the token you get as we'll need it later.

## Transactions Handler

Great now that authentication is out of the way, we can start adding our
proxy handlers. Let's start with the transactions handler.

```python
from typing import Any, AsyncGenerator

from aiorp import HTTPProxyHandler, ProxyContext
from yarl import URL

TRANSACTIONS_API_KEY = "transactions-secret-key-123"  # (1)!
TRANSACTIONS_URL = URL("http://localhost:8001")

transactions_ctx = ProxyContext(url=TRANSACTIONS_URL)  # (2)!
transactions_handler = HTTPProxyHandler(context=transactions_ctx)  # (3)!


@transactions_handler.default  # (4)!
async def transactions_auth(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    """Add transactions API key to requests"""
    ctx.request.headers["X-API-Key"] = TRANSACTIONS_API_KEY
    yield  # (5)!
```

1. This is our example API key for our transactions service
2. `ProxyContext` will take care of setting up a session to the target service
3. The proxy handler is the brains, it will forward all of the requests to
   the target service. It also supports attaching middleware functions
   to execute before and after the proxy request.
4. This decorator is used to register a proxy middleware function on our
   handler. The middleware function will do pre-request actions and
   post-request(response) actions.
5. The code up to the yield will execute before the request,
   everything afterwards will happen after the request is executed.
   Within the function, one can use the `ProxyContext` that offers access to
   the `ProxyRequest` and `ProxyResponse` objects.

With this setup now, we configured a handler to forward authenticated requests
to the transactions service. We obviously still need to connect it to our app
so let's do that now.

Import the `transactions_handler`, and then attach it to
the router below the last defined login route. Note that we need to leave the
path open to proxy all requests our service can accept.

Also we need to import the `transactions_ctx` and the `configure_contexts`,
and call the function with the app and context. This will assure proper session
handling.

```python
    # ...
    configure_contexts(app, [transactions_ctx])  # (1)!

    app.router.add_route(
        "*", "/shops/{shop_id:[A-Za-z0-9]+}/transactions{tail:.*}", transactions_handler
    )
    # ...
```

1. We need to configure the context to start sessions when we start the app
   and close them when the app is turned off

We are now ready to test the communication with the target service. Start both
the proxy server and the target transactions server.

```bash
http GET localhost:8080/shops/BBY001/transactions 'Authorization:Bearer <token-from-login>'
```

If you get a response with test transactions inside, it means we did
everything correctly.

!!! info "The inventory handler"

    The setup for the second service is the same,
    you can try doing it yourself, or just copy it from the example in the Github
    repository. You don't need it for the example, it's there for your
    practice and to demonstrate how to set up a proxy with multiple target
    servers.

## Loading the user

More often than not, it might be useful to know which user is interacting with
our service :smile:. We have this information in the token already but we just
need to load it. Let's create a handler that will do just that.

In the `src/middlewares` directory create an `auth.py` file.

```python
from typing import Any, AsyncGenerator

from aiohttp import web
from aiorp import ProxyContext

from src.utils.auth import verify_token


async def auth_middleware(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    """Middleware to handle authentication for proxy requests"""
    auth_header = ctx.request.headers.get("Authorization")  # (1)!
    if not auth_header or not auth_header.startswith("Bearer "):
        raise web.HTTPUnauthorized(reason="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)  # (2)!
        if ctx.state is None:
            ctx.state = {}
        ctx.state["user"] = payload  # (3)!
        yield  # (4)!
    except web.HTTPUnauthorized as e:
        raise e
    except Exception as e:
        raise web.HTTPUnauthorized(reason=str(e))
```

1. Load the auth header from the incoming request (`in_req`)
2. Attempt to verify the token using our utility function
3. Add the user to the current proxy context state
4. Give control back to the http handler

There we have it, an authentication proxy middleware that will store our user
in the proxy context.

```python
# ...
from src.middlewares.auth import auth_middleware
# ...
transactions_handler = HTTPProxyHandler(context=transactions_ctx)

transactions_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.CLIENT_EDGE, auth_middleware)
)  # (1)!
#...
```

1. Add the middleware `CLIENT_EDGE` so it executes as soon as possible in the request
   lifetime

And what's nice, is that it is reusable, so if you've
prepared the `inventory` service also, you can just plug it in there also

## Rewriting the path

Sometimes we might want to have different endpoint paths at our proxy service,
compared to the endpoints on the target services. For example some of our
target services might serve the same common endpoints (e.g. `/api/login`).
For these cases we need to differ the services. With some service identifier
in the proxy endpoint.

In other cases, like the one we can see with our services here, we have
a common prefix that we can actually fill ourselves: `/shops/{shop_id}/`.
We can find the `shop_id` in the API key, and use it to build the path.
Securing even more access to resources of different users. Let's take
a look at how we can easily do this.

Add another file to the `middlewares` module called `rewrite.py`. Let's
define the functionality of rewriting:

```python
from posixpath import join
from typing import Any, AsyncGenerator

from aiorp import ProxyContext


async def rewrite_shop_path(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    user = ctx.state["user"]
    new_path = join(f"/shops/{user["user_id"]}", ctx.request.url.path.lstrip("/"))  # (1)!
    ctx.request.url = ctx.request.url.with_path(new_path)
    yield
```

1. Prefix the path with the correct shop identifier. Don't forget to strip the
   prefix slash from the path (second argument), or `join` will consider it as
   absolute path and disregard all else

Having this prepared now, we can include it in our handlers the same way we did
with the authorization middleware, for both services.

```python
# ...
from src.middlewares.rewrite import rewrite_shop_path
# ...
transactions_handler = HTTPProxyHandler(context=transactions_ctx)

transactions_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.PROXY, rewrite_shop_path)
)  # (1)!
```

1. You want to add it as `PROXY` phase middleware, since we want it executed
   after the user is loaded (in `CLIENT_EDGE` phase)

Just keep in mind to set the middleware phase to `PROXY`.

Let's test it also!

```bash
http localhost:8080/transactions 'Authorization: Bearer <your-token>'
```

## Compressing the response

A common requirement is the possibility to add compression to responses to save
some :moneybag: on network traffic. Let' see how to do that with the proxy
middlewares.

```python
import gzip
from typing import Any, AsyncGenerator

from aiohttp import web

from aiorp.context import ProxyContext


async def compression_middleware(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    """Middleware to compress responses before sending to client"""
    yield

    accept_encoding = ctx.request.in_req.headers.get("Accept-Encoding", "")

    if "gzip" not in accept_encoding.lower():
        return

    if not ctx.response.web_response_set:
        await ctx.response.set_response()

    if ctx.response.web is web.StreamResponse:
        return

    content = ctx.response.web.body

    compressed = gzip.compress(content)

    new_response = web.Response(
        body=compressed,
        status=ctx.response.web.status,
        headers=ctx.response.web.headers,
    )

    new_response.headers["Content-Encoding"] = "gzip"
    new_response.headers["Content-Length"] = str(len(compressed))
    ctx.response._web = new_response
```

Having written this we can add it in the same way we did previously to our
handlers

```python
# ...
transactions_handler.add_middleware(
    ProxyMiddlewareDef(MiddlewarePhase.CLIENT_EDGE, compression_middleware)  # (1)!
)
# ...
```

1. This needs to happen right before we return the response to the client.

Let's test the compression now. The `http` tool sends an `Accept-Encoding`
header by default with `gzip` and `deflate`. If you are using `curl`,
just add the header `Accept-Encoding: gzip`.

```bash
http localhost:8080/transactions 'Authorization: Bearer <your-token>'
```

## Th-th-th-that's all folks!

That should give you a nice overview of the functionality of this package.
If you are missing some more functionality, I recommend checking out the
Advanced section as you might find some information there perhaps. Otherwise,
prepare an Issue on Github with a request. (format for issue all still TBD)
