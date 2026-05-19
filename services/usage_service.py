import datetime

from flask import request as flask_request

from config import STATS_FILE, DAILY_FREE_LIMIT, DAILY_PRO_LIMIT
from services.json_store import load_json, save_json
from services.user_service import load_users, save_users, get_user_data


def get_today():
    return datetime.date.today().strftime("%Y-%m-%d")


# ── Per-user counters ──────────────────────────────────────────────────

def get_user_daily_count(username):
    if not username:
        return 0
    data = get_user_data(username)
    if not data:
        return 0
    return data.get("daily_count", {}).get(get_today(), 0)


def increment_user_daily_count(username):
    if not username:
        return
    users = load_users()
    if username not in users:
        return
    today = get_today()
    users[username].setdefault("daily_count", {})
    users[username]["daily_count"][today] = (
        users[username]["daily_count"].get(today, 0) + 1
    )
    save_users(users)


def get_user_limit(username):
    if not username:
        return DAILY_FREE_LIMIT
    data = get_user_data(username)
    if not data:
        return DAILY_FREE_LIMIT
    return DAILY_PRO_LIMIT if data.get("plan") == "pro" else DAILY_FREE_LIMIT


def check_usage_limit(username):
    """Returns (allowed, used, limit, remaining)"""
    if not username:
        ip    = flask_request.remote_addr or "unknown"
        stats = load_json(STATS_FILE, {})
        today = get_today()
        key   = f"guest_{ip}_{today}"
        used  = stats.get("guest_counts", {}).get(key, 0)
        limit = DAILY_FREE_LIMIT
        return used < limit, used, limit, max(0, limit - used)
    used      = get_user_daily_count(username)
    limit     = get_user_limit(username)
    remaining = max(0, limit - used)
    return used < limit, used, limit, remaining


def increment_guest_count(ip):
    stats = load_json(STATS_FILE, {})
    today = get_today()
    key   = f"guest_{ip}_{today}"
    stats.setdefault("guest_counts", {})
    stats["guest_counts"][key] = stats["guest_counts"].get(key, 0) + 1
    save_json(STATS_FILE, stats)


# ── Global stats ───────────────────────────────────────────────────────

def increment_global_stats(style_key, detected_lang):
    stats = load_json(STATS_FILE, {})
    today = get_today()
    stats.setdefault("daily", {})
    stats["daily"].setdefault(today, {"total": 0, "styles": {}, "languages": {}})
    stats["daily"][today]["total"] += 1
    st = stats["daily"][today]["styles"]
    st[style_key] = st.get(style_key, 0) + 1
    la = stats["daily"][today]["languages"]
    la[detected_lang] = la.get(detected_lang, 0) + 1
    stats["total_all_time"] = stats.get("total_all_time", 0) + 1
    save_json(STATS_FILE, stats)


def get_admin_stats():
    stats = load_json(STATS_FILE, {})
    users = load_users()
    today = get_today()

    chart_labels, chart_values = [], []
    for i in range(6, -1, -1):
        day = (datetime.date.today() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        chart_labels.append(day[5:])
        chart_values.append(stats.get("daily", {}).get(day, {}).get("total", 0))

    today_data  = stats.get("daily", {}).get(today, {})
    today_styles = today_data.get("styles", {})
    today_langs  = today_data.get("languages", {})
    top_style    = max(today_styles, key=today_styles.get) if today_styles else "—"
    total_users  = len(users)
    pro_users    = sum(1 for u in users.values() if u.get("plan") == "pro")

    return {
        "today_total":  today_data.get("total", 0),
        "all_time":     stats.get("total_all_time", 0),
        "total_users":  total_users,
        "pro_users":    pro_users,
        "free_users":   total_users - pro_users,
        "top_style":    top_style,
        "today_styles": today_styles,
        "today_langs":  today_langs,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
    }
