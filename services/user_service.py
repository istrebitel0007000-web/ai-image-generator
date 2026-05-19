import re
import datetime

from config import USERS_FILE
from services.json_store import load_json, save_json
from services.auth_service import hash_password


def load_users():
    return load_json(USERS_FILE, {})


def save_users(users):
    save_json(USERS_FILE, users)


def get_user_data(username):
    return load_users().get(username)


def update_user(username, data):
    users = load_users()
    if username in users:
        users[username] = data
        save_users(users)


def _make_user_record(password_hash, display_name="", avatar="", login_method="password"):
    return {
        "password":     password_hash,
        "display_name": display_name,
        "avatar":       avatar,
        "login_method": login_method,
        "created":      datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "plan":         "free",
        "history":      [],
        "favorites":    [],
        "downloads":    [],
        "daily_count":  {},
    }


def create_user(username, password):
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 30:
        return False, "Username too long (max 30)"
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Only letters, numbers, underscore allowed"
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    users = load_users()
    if username in users:
        return False, "Username already taken"
    users[username] = _make_user_record(hash_password(password), display_name=username)
    save_users(users)
    return True, ""


def verify_user(username, password):
    users = load_users()
    if username not in users:
        return False
    return users[username].get("password") == hash_password(password)


def get_or_create_google_user(google_id, email, name, avatar):
    users = load_users()
    for uname, udata in users.items():
        if udata.get("google_id") == google_id:
            users[uname]["display_name"] = name
            users[uname]["avatar"] = avatar
            save_users(users)
            return uname
    base = re.sub(r"[^a-zA-Z0-9_]", "_", email.split("@")[0])[:20]
    username = base
    counter = 1
    while username in users:
        username = f"{base}_{counter}"
        counter += 1
    users[username] = _make_user_record(
        password_hash="",
        display_name=name,
        avatar=avatar,
        login_method="google",
    )
    users[username]["google_id"] = google_id
    users[username]["email"]     = email
    save_users(users)
    return username
