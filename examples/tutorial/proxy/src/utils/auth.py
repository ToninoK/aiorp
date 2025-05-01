from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator

import jwt
from aiohttp import web

from aiorp.context import ProxyContext

# Secret key for JWT signing - in production, this should be in environment variables
JWT_SECRET = "your-super-secret-jwt-key"
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 3600  # 1 hour

# Sample user database - in production, this should be in a proper database
USERS = {
    "admin": {
        "password": "admin123",  # In production, use proper password hashing
        "role": "admin",
    },
    "WAL001": {
        "password": "wal001",
        "role": "user",
    },
    "BBY001": {
        "password": "bby001",
        "role": "user",
    },
    "ZAR001": {
        "password": "zar001",
        "role": "user",
    },
    "WFM001": {
        "password": "wfm001",
        "role": "user",
    },
    "APP001": {
        "password": "app001",
        "role": "user",
    },
    "HNM001": {
        "password": "hnm001",
        "role": "user",
    },
}


def create_token(user_id: str) -> str:
    """Create a new JWT token for the user"""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(tz=timezone.utc) + timedelta(seconds=JWT_EXP_DELTA_SECONDS),
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify the JWT token and return the payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise web.HTTPUnauthorized(reason="Token has expired")
    except jwt.InvalidTokenError:
        raise web.HTTPUnauthorized(reason="Invalid token")


async def auth_middleware(ctx: ProxyContext) -> AsyncGenerator[None, Any]:
    """Middleware to handle authentication for proxy requests"""
    auth_header = ctx.request.in_req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise web.HTTPUnauthorized(reason="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)
        # Store user info in the context state for potential use in other middlewares
        if ctx.state is None:
            ctx.state = {}
        ctx.state["user"] = payload
        yield
    except web.HTTPUnauthorized as e:
        raise e
    except Exception as e:
        raise web.HTTPUnauthorized(reason=str(e))


async def login_handler(request):
    """Handle user login and token generation"""
    try:
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
    except web.HTTPException:
        raise
    except Exception as e:
        raise web.HTTPBadRequest(reason=str(e))
