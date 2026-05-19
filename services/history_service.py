import re
import secrets
import datetime

from config import GUEST_FILE, SHARES_FILE
from services.json_store import load_json, save_json
from services.user_service import load_users, save_users, get_user_data


# ── User history ───────────────────────────────────────────────────────

def add_user_history(username, entry):
    if not username:
        return
    users = load_users()
    if username not in users:
        return
    users[username].setdefault("history", []).insert(0, entry)
    users[username]["history"] = users[username]["history"][:100]
    save_users(users)


def get_user_history(username):
    data = get_user_data(username)
    return data.get("history", []) if data else []


# ── Guest history ──────────────────────────────────────────────────────

def add_guest_history(ip, entry):
    data = load_json(GUEST_FILE, {})
    key  = f"guest_{re.sub(r'[^0-9a-fA-F.:]', '_', ip)}"
    data.setdefault(key, []).insert(0, entry)
    data[key] = data[key][:20]
    save_json(GUEST_FILE, data)


def get_guest_history(ip):
    data = load_json(GUEST_FILE, {})
    key  = f"guest_{re.sub(r'[^0-9a-fA-F.:]', '_', ip)}"
    return data.get(key, [])


# ── Favorites ──────────────────────────────────────────────────────────

def toggle_user_favorite(username, entry):
    if not username:
        return False, 0
    users = load_users()
    if username not in users:
        return False, 0
    favs     = users[username].get("favorites", [])
    filename = entry.get("filename", "")
    if any(f.get("filename") == filename for f in favs):
        favs = [f for f in favs if f.get("filename") != filename]
        users[username]["favorites"] = favs
        save_users(users)
        return False, len(favs)
    favs.insert(0, entry)
    users[username]["favorites"] = favs
    save_users(users)
    return True, len(favs)


def get_user_favorites(username):
    data = get_user_data(username)
    return data.get("favorites", []) if data else []


def is_user_favorite(username, filename):
    return any(f.get("filename") == filename for f in get_user_favorites(username))


# ── Downloads ──────────────────────────────────────────────────────────

def log_user_download(username, entry):
    if not username:
        return
    users = load_users()
    if username not in users:
        return
    users[username].setdefault("downloads", []).insert(0, entry)
    users[username]["downloads"] = users[username]["downloads"][:200]
    save_users(users)


def get_user_downloads(username):
    data = get_user_data(username)
    return data.get("downloads", []) if data else []


# ── Shares ─────────────────────────────────────────────────────────────

def _load_shares():
    return load_json(SHARES_FILE, {})


def _save_shares(shares):
    save_json(SHARES_FILE, shares)


def create_share(filename, image_url, prompt, style, username):
    share_id = secrets.token_urlsafe(10)
    shares   = _load_shares()
    shares[share_id] = {
        "filename":   filename,
        "image_url":  image_url,
        "prompt":     prompt,
        "style":      style,
        "created_by": username or "guest",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "views":      0,
    }
    _save_shares(shares)
    return share_id


def get_share(share_id):
    return _load_shares().get(share_id)


def increment_share_views(share_id):
    shares = _load_shares()
    if share_id in shares:
        shares[share_id]["views"] = shares[share_id].get("views", 0) + 1
        _save_shares(shares)
