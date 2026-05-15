"""
app/services/_storage.py  (protected helper)

All JSON persistence and daily-quota helpers.
No business logic — pure data access layer.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

OUTPUT_DIR    = Path(os.getenv("OUTPUT_DIR",    "generated_images"))
UPSCALE_DIR   = Path(os.getenv("UPSCALE_DIR",   "upscaled_images"))
WATERMARK_DIR = Path(os.getenv("WATERMARK_DIR", "watermarked_images"))

for _d in (OUTPUT_DIR, UPSCALE_DIR, WATERMARK_DIR):
    _d.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

_USERS_FILE       = Path("users.json")
_SHARES_FILE      = Path("shares.json")
_STATS_FILE       = Path("stats.json")
_API_KEYS_FILE    = Path("api_keys.json")
_GUEST_FILE       = Path("guest_history.json")
_COLLECTIONS_FILE = Path("collections.json")

# ---------------------------------------------------------------------------
# Limits (overridable via env)
# ---------------------------------------------------------------------------

DAILY_FREE_LIMIT = int(os.getenv("DAILY_FREE_LIMIT", "10"))
DAILY_PRO_LIMIT  = int(os.getenv("DAILY_PRO_LIMIT",  "100"))


# ---------------------------------------------------------------------------
# Low-level JSON helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path, default=None) -> dict:
    if default is None:
        default = {}
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _today() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def load_users() -> dict:
    return _load_json(_USERS_FILE, {})


def save_users(users: dict) -> None:
    _save_json(_USERS_FILE, users)


def get_user_data(username: Optional[str]) -> Optional[dict]:
    if not username:
        return None
    return load_users().get(username)


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

def load_collections() -> dict:
    return _load_json(_COLLECTIONS_FILE, {})


def save_collections(data: dict) -> None:
    _save_json(_COLLECTIONS_FILE, data)


# ---------------------------------------------------------------------------
# Shares
# ---------------------------------------------------------------------------

def load_shares() -> dict:
    return _load_json(_SHARES_FILE, {})


def save_shares(shares: dict) -> None:
    _save_json(_SHARES_FILE, shares)


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------

def load_api_keys() -> dict:
    return _load_json(_API_KEYS_FILE, {})


def save_api_keys(keys: dict) -> None:
    _save_json(_API_KEYS_FILE, keys)


def get_user_api_keys(username: str) -> dict:
    return {k: v for k, v in load_api_keys().items() if v.get("username") == username}


# ---------------------------------------------------------------------------
# Daily usage
# ---------------------------------------------------------------------------

def _get_user_daily_count(username: str) -> int:
    data = get_user_data(username)
    if not data:
        return 0
    return data.get("daily_count", {}).get(_today(), 0)


def _get_user_limit(username: Optional[str]) -> int:
    if not username:
        return DAILY_FREE_LIMIT
    data = get_user_data(username)
    if not data:
        return DAILY_FREE_LIMIT
    return DAILY_PRO_LIMIT if data.get("plan") == "pro" else DAILY_FREE_LIMIT


def _get_guest_daily_count(ip: str) -> int:
    stats = _load_json(_STATS_FILE, {})
    key   = f"guest_{ip}_{_today()}"
    return stats.get("guest_counts", {}).get(key, 0)


def check_usage_limit(
    username: Optional[str],
    ip:       str = "",
) -> Tuple[bool, int, int, int]:
    """Returns (allowed, used, limit, remaining)."""
    if username:
        used  = _get_user_daily_count(username)
        limit = _get_user_limit(username)
    else:
        used  = _get_guest_daily_count(ip)
        limit = DAILY_FREE_LIMIT

    remaining = max(0, limit - used)
    return used < limit, used, limit, remaining


def increment_user_daily_count(username: str, amount: int = 1) -> None:
    users = load_users()
    if username not in users:
        return
    users[username].setdefault("daily_count", {})
    users[username]["daily_count"].setdefault(_today(), 0)
    users[username]["daily_count"][_today()] += amount
    save_users(users)


def increment_guest_daily_count(ip: str, amount: int = 1) -> None:
    stats = _load_json(_STATS_FILE, {})
    key   = f"guest_{ip}_{_today()}"
    stats.setdefault("guest_counts", {})
    stats["guest_counts"][key] = stats["guest_counts"].get(key, 0) + amount
    _save_json(_STATS_FILE, stats)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def add_user_history(username: str, entry: dict) -> None:
    users = load_users()
    if username not in users:
        return
    users[username].setdefault("history", []).insert(0, entry)
    users[username]["history"] = users[username]["history"][:100]
    save_users(users)


def get_user_history(username: Optional[str]) -> list:
    data = get_user_data(username)
    return data.get("history", []) if data else []


def add_guest_history(ip: str, entry: dict) -> None:
    import re as _re
    data = _load_json(_GUEST_FILE, {})
    key  = "guest_" + _re.sub(r"[^0-9a-fA-F.:]", "_", ip)
    data.setdefault(key, []).insert(0, entry)
    data[key] = data[key][:20]
    _save_json(_GUEST_FILE, data)


def get_guest_history(ip: str) -> list:
    import re as _re
    data = _load_json(_GUEST_FILE, {})
    key  = "guest_" + _re.sub(r"[^0-9a-fA-F.:]", "_", ip)
    return data.get(key, [])


# ---------------------------------------------------------------------------
# Global stats
# ---------------------------------------------------------------------------

def increment_global_stats(style_key: str, language: str, amount: int = 1) -> None:
    stats = _load_json(_STATS_FILE, {})
    today = _today()
    stats.setdefault("daily", {})
    stats["daily"].setdefault(today, {"total": 0, "styles": {}, "languages": {}})
    stats["daily"][today]["total"] += amount
    st = stats["daily"][today]["styles"]
    st[style_key] = st.get(style_key, 0) + amount
    la = stats["daily"][today]["languages"]
    la[language] = la.get(language, 0) + amount
    stats["total_all_time"] = stats.get("total_all_time", 0) + amount
    _save_json(_STATS_FILE, stats)
