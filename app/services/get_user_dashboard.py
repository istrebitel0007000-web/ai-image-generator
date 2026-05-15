"""
app/services/get_user_dashboard.py

Single responsibility: assemble and return the full user dashboard dict.
"""
from __future__ import annotations

import datetime
from typing import Optional

from app.services._storage import (
    get_user_data,
    check_usage_limit,
    load_collections,
    get_user_api_keys,
)


def get_user_dashboard(*, username: str, ip: str) -> dict:
    """
    Return a comprehensive stats payload for `username`.
    Raises LookupError when user does not exist.
    """
    data = get_user_data(username)
    if not data:
        raise LookupError("User not found.")

    _, used, limit, remaining = check_usage_limit(username, ip)

    history     = data.get("history",   [])
    favorites   = data.get("favorites", [])
    downloads   = data.get("downloads", [])
    collections = load_collections().get(username, [])

    return {
        "username":     username,
        "display_name": data.get("display_name", username),
        "avatar":       data.get("avatar", ""),
        "plan":         data.get("plan", "free"),
        "joined":       data.get("created", ""),
        "login_method": data.get("login_method", "password"),
        "usage": {
            "used_today":        used,
            "limit_today":       limit,
            "remaining_today":   remaining,
            "total_images":      len(history),
            "total_favorites":   len(favorites),
            "total_downloads":   len(downloads),
            "total_collections": len(collections),
        },
        "style_breakdown":    _count_field(history, "style_key"),
        "top_style":          _top_value(history, "style_key"),
        "language_breakdown": _count_field(history, "language"),
        "daily_activity":     _daily_activity(history),
        "recent_history":     history[:10],
        "collections": [
            {"id": c["id"], "name": c["name"], "image_count": len(c.get("images", []))}
            for c in collections
        ],
        "api_key_count": len(get_user_api_keys(username)),
    }


# ---------------------------------------------------------------------------
# Protected helpers
# ---------------------------------------------------------------------------

def _count_field(history: list, field: str) -> dict:
    counts: dict = {}
    for entry in history:
        val = entry.get(field, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts


def _top_value(history: list, field: str) -> Optional[str]:
    counts = _count_field(history, field)
    return max(counts, key=counts.get) if counts else None


def _daily_activity(history: list) -> list:
    today = datetime.date.today()
    index: dict = {}
    for entry in history:
        day = (entry.get("timestamp") or "")[:10]
        if day:
            index[day] = index.get(day, 0) + 1

    result = []
    for i in range(6, -1, -1):
        day = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        result.append({"date": day, "count": index.get(day, 0)})
    return result
