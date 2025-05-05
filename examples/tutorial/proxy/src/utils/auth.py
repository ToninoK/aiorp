from datetime import datetime, timedelta, timezone

import jwt
from aiohttp import web

JWT_SECRET = "your-super-secret-jwt-key"  #
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 3600  # 1hr


USERS = {
    "WAL001": {
        "password": "wal001",
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
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM], verify_exp=True
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise web.HTTPUnauthorized(reason="Token has expired")
    except jwt.InvalidTokenError:
        raise web.HTTPUnauthorized(reason="Invalid token")
