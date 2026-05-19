import secrets
import datetime
from functools import wraps

from flask import request, jsonify, session

from config import API_KEYS_FILE
from services.json_store import load_json, save_json


def _load_api_keys():
    return load_json(API_KEYS_FILE, {})


def _save_api_keys(keys):
    save_json(API_KEYS_FILE, keys)


def generate_api_key():
    return "aig_" + secrets.token_urlsafe(32)


def create_api_key(username, label="My App"):
    keys = _load_api_keys()
    key  = generate_api_key()
    keys[key] = {
        "username": username,
        "label":    label,
        "created":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "uses":     0,
        "active":   True,
    }
    _save_api_keys(keys)
    return key


def validate_api_key(key):
    if not key:
        return False, None
    keys = _load_api_keys()
    if key not in keys or not keys[key].get("active", True):
        return False, None
    keys[key]["uses"] = keys[key].get("uses", 0) + 1
    _save_api_keys(keys)
    return True, keys[key].get("username")


def get_user_api_keys(username):
    return {k: v for k, v in _load_api_keys().items() if v.get("username") == username}


def revoke_api_key(key, username):
    keys = _load_api_keys()
    if key in keys and keys[key].get("username") == username:
        keys[key]["active"] = False
        _save_api_keys(keys)
        return True
    return False


# ── Decorators ─────────────────────────────────────────────────────────

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key             = request.headers.get("X-API-Key") or request.args.get("api_key")
        valid, username = validate_api_key(key)
        if not valid:
            return jsonify({"error": "Invalid or missing API key", "code": 401}), 401
        request.api_username = username
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated
