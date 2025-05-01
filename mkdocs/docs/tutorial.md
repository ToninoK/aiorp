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
uv init aiorp-example
cd aiorp-example
uv add aiorp
source .venv/bin/activate
rm hello.py  # (1)!
```

1. `uv` creates a `hello.py` file, so let's just remove that
