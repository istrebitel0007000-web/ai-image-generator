"""
app/views/_auth.py  (protected helper)

Shared auth utilities used by views.
Not a view itself — no routes registered here.
"""
from __future__ import annotations

from functools import wraps
from typing import Optional

from flask import session, request, jsonify, make_response

from app.services._storage import load_api_keys, save_api_keys


def resolve_username() -> Optional[str]:
    """
    Return the authenticated username from session OR API key header.
    Returns None for unauthenticated requests.
    """
    username = session.get("username")
    if username:
        return username

    api_key = (
        request.headers.get("X-API-Key")
        or request.args.get("api_key")
    )
    if api_key:
        valid, api_username = _validate_api_key(api_key)
        if valid:
            return api_username

    return None


def require_login(f):
    """Decorator: return 401 when user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("username"):
            return make_response(jsonify({"error": "Login required."}), 401)
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Decorator: return 403 when user is not an admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return make_response(jsonify({"error": "Admin access required."}), 403)
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _validate_api_key(key: str) -> tuple[bool, Optional[str]]:
    if not key:
        return False, None
    keys = load_api_keys()
    if key not in keys or not keys[key].get("active", True):
        return False, None
    keys[key]["uses"] = keys[key].get("uses", 0) + 1
    save_api_keys(keys)
    return True, keys[key].get("username")
