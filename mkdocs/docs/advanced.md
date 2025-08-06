---
hide:
  - navigation
---

# Advanced

This section of the docs should cover more advanced usages that weren't covered
with the Quickstart guide or the Tutorial. Nothing here should be really "advanced",
instead it should just give you an idea of the possibilities of this package.

## Additional request options

This package essentially does the following:

- An `aiohttp` web server receives the requests
- Request is mapped and forwarded to an `aiohttp` client session and a request is made
- Response is mapped to an `aiohttp` web response and returned to the client

Not to restrict the user's flexibility with the request options, the `HTTPProxyHandler`
leaves space for the user to forward some desired request options to be set for making
the session request.

This can be done by simply forwarding the kwargs of the [ClientSession.request](https://docs.aiohttp.org/en/stable/client_reference.html##aiohttp.ClientSession.request) to the `HTTPProxyHandler` on definition through the parameter known as
`request_options`.

```python
handler = HTTPProxyHandler(
  context=ctx,
  request_options={
    "max_redirects": 5,
    "read_until_eof": False,
  }
)
```

## Custom error handling

The default error handling for `ClientResponseError` is to raise an `aiohttp.web_exceptions.HTTPInternalServerError` with the reason
`"External API Error"`, and the payload containing the status code and the response, like so:

```python
raise HTTPInternalServerError(
    reason="External API Error",
    content_type="application/json",
    text=json.dumps(
        {
            "status": err.status,
            "message": err.message,
        }
    ),
)
```

For most cases this behaviour should suffice, but sometimes you want more control. In those cases,
a custom error handler can be defined:

```python
def my_error_handler(err: ClientResponseError):
  raise HTTPInternalServerError(
    reason="My reason is better",
    content_type="application/json",
    text=json.dumps(
      {
          "status": err.status,
          "message": err.message,
      }
    )
  )

handler = HTTPProxyHandler(
  context=ctx,
  error_handler=my_error_handler,
)
```

## Custom session factory

Each proxy handler has a context with an `aiohttp.ClientSession`. The session is used for making
requests to the target server.

The session is instantiated on the first request, and reused for further requests.
The default session factory is just the default `aiohttp.ClientSession` constructor. In case
more flexibility is needed a custom session factory can be provided to the `ProxyContext`
constructor which would then be used instead of the default one.

```python
def my_session_factory():
  return ClientSession(
    connector=TCPConnector(
      limit=50,
    )
  )

ctx = ProxyContext(
  url=url,
  session_factory=my_session_factory,
)
```

## Middleware execution order

The main idea of this package is to give you flexibility in writing proxy request
middleware. To make this more powerful, you are able to define at what point some
action might get executed.

E.g. maybe you want something to get executed as soon as you receive the request,
and something should get executed only after that was executed. Same goes for
responses.

We will call this the middleware phase, and when defining a middleware you can
specify which phase it should execute in.

```python
from aiorp import HTTPProxyHandler, MiddlewarePhase, ProxyMiddlewareDef

# ...

http_handler = HTTPProxyHandler(ctx=ctx)
http_handler.add_middleware(
  ProxyMiddlewareDef(phase=MiddlewarePhase.CLIENT_EDGE, middleware=my_middleware)
)
```

The above code demonstrates how to define a middleware that will get executed
on the `CLIENT_EDGE`. An alternative approach is using the decorator pattern.

```python
from aiorp import HTTPProxyHandler

# ...

http_handler = HTTPProxyHandler(ctx=ctx)

@http_handler.client_edge
def my_middleware(ctx: ProxyContext):
  print("I execute at the client edge before the proxy request")
  yield
  print("I execute at the client edge after the proxy request")
```

### Middleware phases

To help with organization, three middleware phases are defined through the
`MiddlewarePhase` enum, and the same are exposed for the decorator pattern:

- `CLIENT_EDGE`: Executes after receiving the initial request,
  and before returning the response to the client
- `TARGET_EDGE`: Executes before making the target request,
  and right after receiving the target response
- `PROXY`: Executes between `TARGET_EDGE` and `CLIENT_EDGE`

You will rarely need more phases than this, but in the distant case that you
might - you can have more phases. The phases are just numbers between 0 - 1000.
Client edge is at 0, proxy is at 500, and target edge is at 1000.

So in theory if you need 4 different phases, you can do something like this:

```python
http_handler.add_middleware(
  ProxyMiddlewareDef(phase=0, middleware=mid_a)
)
http_handler.add_middleware(
  ProxyMiddlewareDef(phase=300, middleware=mid_b)
)
http_handler.add_middleware(
  ProxyMiddlewareDef(phase=500, middleware=mid_c)
)
http_handler.add_middleware(
  ProxyMiddlewareDef(phase=1000, middleware=mid_d)
)
```

**Disclaimer**: Even though this might be possible, I don't encourage it
as you very likely don't need so many phases.

### Asynchronous execution

Other than execution order, phases have another importance. Every phase can
have more than one middleware. And within one phase all middlewares are
executed asynchronously.

### How to design middleware?

With all of the above in mind what are some code design pointers?

- **Keep the number of phases to a minimum**  
  Split actions into phases based on prerequisites. E.g. rate-limiting and
  authentication are examples of client edge actions. If these fail there is
  no point in executing any other action

- **Separate middleware in the same phase into logical parts**  
  BUT don't be excessive with decomposition, if something can't be reused,
  consider using a different asynchronous pattern like `asyncio.gather` or
  `asyncio.wait`

## Path rewriting

Since it is a fairly common thing with proxies, path rewriting was added as
a simple to use functionality.

You can set the rewrite configuration per handler using the `Rewrite` class:

```python
rewrite = Rewrite(rfrom="/mytarget", rto="/")
```

## Proxy request state

More often than not you might need some state during the proxy request
lifecycle. Maybe you need some values accessible in every point of the request
lifecycle and maybe you need to pass some values from one phase to another.

For this use case, a `state` dictionary can be accessed within the
`ProxyContext` object. The context is accessible within every part of the
request lifecycle, and the state is copied for every request, so each request
has its own unique state.

You can set it and use it the following way:

```python
ctx = ProxyContext(url=url, state={"resource_name": "target-A"})

http_handler = HTTPProxyHandler(ctx=ctx)

@http_handler.client_edge
def log_resource(ctx: ProxyContext):
  print(ctx.state["resource_name"])
  ctx.state["custom_key"] = 123

@http_handler.target_edge
def log_custom_value(ctx: ProxyContext):
  print(ctx.state["resource_name"])
  print(ctx.state["custom_key"])
```
