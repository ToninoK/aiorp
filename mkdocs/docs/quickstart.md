---
hide:
  - navigation
---

# Quickstart

Want to try it out ASAP to see if it suits your use-case?
Let's set up a minimal example for you.

## Installation

Let's get the package installed for starters.
In your virtual environment run the following:

```bash
pip3 install aiorp
```

Once this completes you should have both `aiorp` and `aiohttp` installed.

## Minimal example

```python
from aiohttp import web
from aiorp import HTTPProxyHandler, ProxyContext
from aiorp.context import configure_contexts

TARGET_URL = yarl.URL("https://your-target-server.com")  # (1)!

app = web.Application()

ctx = ProxyContext(TARGET_URL)
configure_contexts(app, [ctx])

handler = HTTPProxyHandler(context=ctx)

app.router.add_get("/{path:.*}", handler)  # (2)!

web.run_app(app, host="0.0.0.0", port=8000)
```

1. Replace with your target server URL

## What did I just read?

If you are confused a bit about what you just read above, no worries,
we'll walk through the example and discuss what's happening.

### Imports

```python
from aiohttp import web
from aiorp import HTTPProxyHandler, ProxyContext, configure_contexts
# ...
```

You should probably understand what's happening here. We are just importing
all the packages we need. We need:

- the `web` module from `aiohttp` for setting up the application
- `HTTPProxyHandler` for defining the proxy handler
- `ProxyContext` to be able to set the context for requests targeting a
  specific server
- `configure_contexts` to set up some context management for the contexts we
  define

### Defining the App

```python
# ...
app = web.Application()
# ...
web.run_app(app, host="0.0.0.0", port=8000)
```

Nothing out of the ordinary here, we just need to set up the `aiohttp` server
application we want to use for our proxy server.

### Defining the proxy context

```python
# ...
ctx = ProxyContext(TARGET_URL)
configure_contexts(app, [ctx])
# ...
```

To define where our handler should proxy the requests you need to feed it a
`ProxyContext` instance. `ProxyContext` is a class in charge of handling
the proxied request contexts targeting a specific URL. What falls under
the _jurisdiction_ of a proxy context? Well pretty much anything related
to your proxy request:

- Session -> the session that manages connections to the target server
- `ProxyRequest` -> a wrapper around incoming and outgoing requests
- `ProxyResponse` -> a wrapper around incoming and outgoing responses
- State -> simple dictionary allowing you to share data between handlers
  during the request lifetime

If you need any further information on the above-mentioned, you should
find it all within the documentation.

The `configure_contexts` function on the other hand is very simple. It is
just in charge of making sure that the sessions are properly opened and
closed during the application lifecycle.

### Defining our handler

```python
# ...
handler = HTTPProxyHandler(context=ctx)

app.router.add_get("/{path:.*}", handler)
# ...
```

Finally, we can define our handler and attach it to the application.
What exactly does the handler do? It accepts a `web.Request` object,
and proxies it to the target server defined in the context, returning the
target server response.

In the second line we simply route all of the GET requests to the handler.

## Where to next?

This is just the bare-bones functionality, if you want a more complex example,
you should check out the [Tutorial](./tutorial.md). After that, I recommend
checking out the [Advanced documentation](../advanced/) and the
[API reference](./api_reference/BaseHandler.md).
