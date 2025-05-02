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

Great now that it works we can start adding our proxy handlers.
Let's start with the transactions handler.

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

```python
    # ...
    app.router.add_route(
        "*", "/shops/{shop_id:[A-Za-z0-9]+}/transactions{tail:.*}", transactions_handler
    )
    # ...
```

We are now ready to test the communication with the target service. Start both
the proxy server and the target transactions server.

```bash
http GET localhost:8080/shops/BBY001/transactions 'Authorization:Bearer <token-from-login>'
```

If you get a response with test transactions inside, it means we did
everything correctly.

!!! info "The inventory service"

    The setup for the second service is the same,
    you can try doing it yourself, or just copy it from the example in the Github
    repository. You don't even need it for the example, it's there for your
    practice and to demonstrate how to set up a proxy with multiple target
    servers.
