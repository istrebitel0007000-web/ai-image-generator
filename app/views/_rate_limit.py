"""
app/views/_rate_limit.py  (protected helper)

Attaches X-RateLimit-* headers to every generate response.
"""
from __future__ import annotations

import datetime
from typing import Optional

from app.services._storage import check_usage_limit


def attach_rate_limit_headers(response, username: Optional[str], ip: str):
    """Mutate `response` to include X-RateLimit-* headers and return it."""
    _, used, limit, remaining = check_usage_limit(username, ip)

    now       = datetime.datetime.utcnow()
    reset_utc = datetime.datetime(now.year, now.month, now.day) + datetime.timedelta(days=1)
    reset_ts  = int(reset_utc.timestamp())

    response.headers["X-RateLimit-Limit"]       = str(limit)
    response.headers["X-RateLimit-Used"]         = str(used)
    response.headers["X-RateLimit-Remaining"]    = str(remaining)
    response.headers["X-RateLimit-Reset"]        = str(reset_ts)
    response.headers["X-RateLimit-Reset-After"]  = str(max(0, reset_ts - int(now.timestamp())))
    return response
