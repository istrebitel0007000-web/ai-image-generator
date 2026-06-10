# ════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES  —  drop these into your app.py (or import as a Blueprint)
#  Place this file next to app.py and add to app.py:
#      from admin_routes import admin_bp
#      app.register_blueprint(admin_bp)
# ════════════════════════════════════════════════════════════════════════════

import os, json, hashlib, datetime, functools, re
from flask import (
    Blueprint, request, jsonify, session,
    send_file, render_template, abort
)

admin_bp = Blueprint("admin", __name__)

# ── paths ────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
USERS_FILE    = os.path.join(BASE_DIR, "users.json")
GUESTS_FILE   = os.path.join(BASE_DIR, "guests.json")
SHARES_FILE   = os.path.join(BASE_DIR, "shares.json")
CONFIG_FILE   = os.path.join(BASE_DIR, "config.json")
IMAGES_FILE   = os.path.join(BASE_DIR, "images_log.json")
LOGS_FILE     = os.path.join(BASE_DIR, "admin_logs.json")

# ── default super-admin credentials (override via env vars) ──────────────────
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")   # change this!


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════

def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")


def write_log(action: str, detail: str):
    logs = load_json(LOGS_FILE, [])
    logs.insert(0, f"[{now_str()}] [{action}] {detail}")
    logs = logs[:500]          # keep last 500 entries
    save_json(LOGS_FILE, logs)


def admin_required(fn):
    """Decorator — blocks non-admins with 401."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


def load_users() -> dict:
    return load_json(USERS_FILE, {})


def save_users(data: dict):
    save_json(USERS_FILE, data)


def load_config() -> dict:
    cfg = load_json(CONFIG_FILE, {})
    cfg.setdefault("free_limit", 10)
    cfg.setdefault("pro_limit", 100)
    cfg.setdefault("watermark", True)
    cfg.setdefault("upscale_default", False)
    return cfg


def get_user_limit(plan: str) -> int:
    cfg = load_config()
    return cfg["pro_limit"] if plan == "pro" else cfg["free_limit"]


def enrich_user(username: str, udata: dict) -> dict:
    """Return a safe, flat dict for the frontend."""
    cfg = load_config()
    plan  = udata.get("plan", "free")
    limit = cfg["pro_limit"] if plan == "pro" else cfg["free_limit"]
    today = today_str()

    used_today = 0
    daily = udata.get("daily_counts", {})
    if isinstance(daily, dict):
        used_today = daily.get(today, 0)

    history = udata.get("history", [])
    image_count = len(history)

    # grab last 20 for live feed
    recent = sorted(history, key=lambda x: x.get("timestamp",""), reverse=True)[:20]

    return {
        "username":      username,
        "email":         udata.get("email", ""),
        "display_name":  udata.get("display_name", username),
        "plan":          plan,
        "limit":         limit,
        "used_today":    used_today,
        "image_count":   image_count,
        "joined":        udata.get("joined", ""),
        "last_active":   udata.get("last_active", ""),
        "last_ip":       udata.get("last_ip", ""),
        "login_method":  udata.get("login_method", "password"),
        "api_keys":      udata.get("api_keys", []),
        "is_banned":     udata.get("is_banned", False),
        "recent_history": recent,
    }


# ════════════════════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/login", methods=["POST"])
def admin_login():
    body = request.get_json(force=True) or {}
    uname = body.get("username", "").strip()
    pw    = body.get("password", "")

    if uname == ADMIN_USERNAME and pw == ADMIN_PASSWORD:
        session["is_admin"]    = True
        session["admin_user"]  = uname
        session.permanent      = True
        write_log("LOGIN", f'Admin "{uname}" signed in from {request.remote_addr}')
        return jsonify({"success": True, "username": uname})

    write_log("FAIL_LOGIN", f'Failed login attempt for "{uname}" from {request.remote_addr}')
    return jsonify({"success": False, "error": "Invalid credentials"}), 401


@admin_bp.route("/admin/logout", methods=["POST"])
def admin_logout():
    uname = session.get("admin_user", "unknown")
    session.clear()
    write_log("LOGOUT", f'Admin "{uname}" signed out')
    return jsonify({"success": True})


# ── serve the admin panel HTML ────────────────────────────────────────────────
@admin_bp.route("/admin")
@admin_bp.route("/admin/")
def admin_panel():
    # Page is served regardless — login is handled client-side.
    # Session check happens on every API call.
    return render_template("admin.html")


# ════════════════════════════════════════════════════════════════════════════
#  DASHBOARD STATS
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/stats")
@admin_required
def admin_stats():
    users  = load_users()
    today  = today_str()

    today_total   = 0
    all_time      = 0
    pro_count     = 0
    free_count    = 0
    today_styles  = {}
    today_langs   = {}

    for uname, udata in users.items():
        if uname == "__guests__":
            continue
        plan = udata.get("plan", "free")
        if plan == "pro":
            pro_count  += 1
        else:
            free_count += 1

        history = udata.get("history", [])
        all_time += len(history)

        for entry in history:
            ts = entry.get("timestamp", "")
            if ts.startswith(today):
                today_total += 1
                s = entry.get("style", "unknown")
                l = entry.get("language", "English")
                today_styles[s] = today_styles.get(s, 0) + 1
                today_langs[l]  = today_langs.get(l, 0) + 1

    # chart: last 7 days
    labels, values = [], []
    for i in range(6, -1, -1):
        d  = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        lbl = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%b %d")
        cnt = 0
        for uname, udata in users.items():
            if uname == "__guests__":
                continue
            for entry in udata.get("history", []):
                if entry.get("timestamp", "").startswith(d):
                    cnt += 1
        labels.append(lbl)
        values.append(cnt)

    top_style = max(today_styles, key=today_styles.get) if today_styles else "—"

    return jsonify({
        "today_total":   today_total,
        "all_time":      all_time,
        "total_users":   pro_count + free_count,
        "pro_users":     pro_count,
        "free_users":    free_count,
        "top_style":     top_style,
        "today_styles":  today_styles,
        "today_langs":   today_langs,
        "chart_labels":  labels,
        "chart_values":  values,
    })


# ════════════════════════════════════════════════════════════════════════════
#  USERS
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/users")
@admin_required
def admin_users():
    users = load_users()
    out   = []
    for uname, udata in users.items():
        if uname == "__guests__":
            continue
        out.append(enrich_user(uname, udata))
    return jsonify({"users": out})


@admin_bp.route("/admin/users/<username>/update", methods=["POST"])
@admin_required
def admin_update_user(username):
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found"}), 404
    body = request.get_json(force=True) or {}

    if "display_name" in body and body["display_name"]:
        users[username]["display_name"] = body["display_name"]
    if "plan" in body and body["plan"] in ("free", "pro"):
        users[username]["plan"] = body["plan"]
    if body.get("password"):
        users[username]["password"] = hash_password(body["password"])

    save_users(users)
    write_log("EDIT", f'Updated user "{username}" by {session.get("admin_user")}')
    return jsonify({"success": True})


@admin_bp.route("/admin/users/<username>/plan", methods=["POST"])
@admin_required
def admin_set_plan(username):
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found"}), 404
    body = request.get_json(force=True) or {}
    plan = body.get("plan", "free")
    if plan not in ("free", "pro"):
        return jsonify({"error": "Invalid plan"}), 400
    users[username]["plan"] = plan
    save_users(users)
    write_log("PLAN", f'Set "{username}" plan → {plan} by {session.get("admin_user")}')
    return jsonify({"success": True})


@admin_bp.route("/admin/users/<username>/delete", methods=["POST"])
@admin_required
def admin_delete_user(username):
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found"}), 404
    del users[username]
    save_users(users)
    write_log("DELETE", f'Deleted user "{username}" by {session.get("admin_user")}')
    return jsonify({"success": True})


@admin_bp.route("/admin/users/<username>/reset_limit", methods=["POST"])
@admin_required
def admin_reset_limit(username):
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found"}), 404
    today = today_str()
    users[username].setdefault("daily_counts", {})[today] = 0
    save_users(users)
    write_log("RESET", f'Reset daily limit for "{username}" by {session.get("admin_user")}')
    return jsonify({"success": True})


@admin_bp.route("/admin/users/create", methods=["POST"])
@admin_required
def admin_create_user():
    users = load_users()
    body  = request.get_json(force=True) or {}
    uname = body.get("username", "").strip()
    pw    = body.get("password", "")
    plan  = body.get("plan", "free")

    if not uname or not pw:
        return jsonify({"error": "Username and password required"}), 400
    if uname in users:
        return jsonify({"error": "Username already exists"}), 409
    if len(pw) < 6:
        return jsonify({"error": "Password too short (min 6)"}), 400
    if plan not in ("free", "pro"):
        plan = "free"

    users[uname] = {
        "password":     hash_password(pw),
        "plan":         plan,
        "email":        "",
        "joined":       now_str(),
        "last_active":  now_str(),
        "history":      [],
        "favorites":    [],
        "daily_counts": {},
        "api_keys":     [],
        "login_method": "password",
    }
    save_users(users)
    write_log("CREATE", f'Admin created user "{uname}" (plan={plan}) via {session.get("admin_user")}')
    return jsonify({"success": True})


@admin_bp.route("/admin/users/<username>/ban", methods=["POST"])
@admin_required
def admin_ban_user(username):
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found"}), 404
    body = request.get_json(force=True) or {}
    banned = bool(body.get("banned", True))
    users[username]["is_banned"] = banned
    save_users(users)
    action = "BANNED" if banned else "UNBANNED"
    write_log(action, f'"{username}" by {session.get("admin_user")}')
    return jsonify({"success": True})


# ════════════════════════════════════════════════════════════════════════════
#  SESSIONS / IP TRACKING
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/sessions")
@admin_required
def admin_sessions():
    """
    Returns registered users with session metadata.
    IP is stored in users.json as 'last_ip' whenever a user generates an image.
    """
    users = load_users()
    sessions_out = []
    for uname, udata in users.items():
        if uname == "__guests__":
            continue
        e = enrich_user(uname, udata)
        sessions_out.append(e)
    return jsonify({"sessions": sessions_out})


# ════════════════════════════════════════════════════════════════════════════
#  GUEST TRACKING
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/guests")
@admin_required
def admin_guests():
    """
    guests.json format:
    {
      "1.2.3.4": {
        "today_count": 3,
        "total": 18,
        "last_active": "2025-05-30 14:22:11",
        "last_prompt": "sunset over mountains",
        "dates": {"2025-05-30": 3, ...}
      },
      ...
    }
    """
    raw    = load_json(GUESTS_FILE, {})
    today  = today_str()
    guests = []
    for ip, gdata in raw.items():
        today_count = gdata.get("dates", {}).get(today, gdata.get("today_count", 0))
        guests.append({
            "ip":          ip,
            "today_count": today_count,
            "total":       gdata.get("total", 0),
            "last_active": gdata.get("last_active", ""),
            "last_prompt": gdata.get("last_prompt", ""),
        })
    # sort by most active today
    guests.sort(key=lambda g: g["today_count"], reverse=True)
    return jsonify({"guests": guests})


# ════════════════════════════════════════════════════════════════════════════
#  IMAGE LOG
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/images")
@admin_required
def admin_images():
    """
    Aggregates history from all users into a flat list for the admin table.
    Falls back to images_log.json if it exists.
    """
    # Try images_log.json first (written by generate route)
    if os.path.exists(IMAGES_FILE):
        images = load_json(IMAGES_FILE, [])
        images_sorted = sorted(images, key=lambda x: x.get("timestamp",""), reverse=True)
        return jsonify({"images": images_sorted[:500]})

    # Otherwise rebuild from users.json
    users  = load_users()
    images = []
    for uname, udata in users.items():
        if uname == "__guests__":
            continue
        for entry in udata.get("history", []):
            images.append({**entry, "username": uname})

    # Also add guest images if stored
    guests = load_json(GUESTS_FILE, {})
    for ip, gdata in guests.items():
        for entry in gdata.get("history", []):
            images.append({**entry, "username": f"guest ({ip})"})

    images.sort(key=lambda x: x.get("timestamp",""), reverse=True)
    return jsonify({"images": images[:500]})


# ════════════════════════════════════════════════════════════════════════════
#  SHARES
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/shares")
@admin_required
def admin_shares():
    raw = load_json(SHARES_FILE, {})
    shares = []
    for sid, sdata in raw.items():
        shares.append({
            "id":         sid,
            "prompt":     sdata.get("original_prompt", sdata.get("prompt", "")),
            "style":      sdata.get("style", ""),
            "created_by": sdata.get("created_by", "guest"),
            "created_at": sdata.get("created_at", sdata.get("timestamp", "")),
            "views":      sdata.get("views", 0),
            "image_url":  sdata.get("image_url", ""),
        })
    shares.sort(key=lambda s: s.get("created_at",""), reverse=True)
    return jsonify({"shares": shares})


@admin_bp.route("/admin/shares/<share_id>/delete", methods=["POST"])
@admin_required
def admin_delete_share(share_id):
    raw = load_json(SHARES_FILE, {})
    if share_id not in raw:
        return jsonify({"error": "Not found"}), 404
    del raw[share_id]
    save_json(SHARES_FILE, raw)
    write_log("DELETE_SHARE", f'Deleted share "{share_id}" by {session.get("admin_user")}')
    return jsonify({"success": True})


# ════════════════════════════════════════════════════════════════════════════
#  API KEYS
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/apikeys")
@admin_required
def admin_apikeys():
    users = load_users()
    keys  = []
    for uname, udata in users.items():
        if uname == "__guests__":
            continue
        for k in udata.get("api_keys", []):
            if isinstance(k, dict):
                keys.append({
                    "key":      k.get("key", ""),
                    "label":    k.get("label", ""),
                    "username": uname,
                    "created":  k.get("created", ""),
                    "uses":     k.get("uses", 0),
                    "active":   k.get("active", True),
                })
            elif isinstance(k, str):
                keys.append({
                    "key":      k,
                    "label":    "",
                    "username": uname,
                    "created":  "",
                    "uses":     0,
                    "active":   True,
                })
    return jsonify({"keys": keys})


@admin_bp.route("/admin/apikeys/<path:key>/revoke", methods=["POST"])
@admin_required
def admin_revoke_key(key):
    users   = load_users()
    revoked = False
    for uname, udata in users.items():
        if uname == "__guests__":
            continue
        for k in udata.get("api_keys", []):
            if isinstance(k, dict) and k.get("key") == key:
                k["active"] = False
                revoked = True
    if not revoked:
        return jsonify({"error": "Key not found"}), 404
    save_users(users)
    write_log("REVOKE", f'Revoked API key {key[:16]}... by {session.get("admin_user")}')
    return jsonify({"success": True})


# ════════════════════════════════════════════════════════════════════════════
#  CONFIG / SETTINGS
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/config", methods=["GET", "POST"])
@admin_required
def admin_config():
    if request.method == "GET":
        return jsonify(load_config())

    body = request.get_json(force=True) or {}
    cfg  = load_config()

    if "free_limit" in body:
        v = int(body["free_limit"])
        if 1 <= v <= 10000:
            cfg["free_limit"] = v
    if "pro_limit" in body:
        v = int(body["pro_limit"])
        if 1 <= v <= 100000:
            cfg["pro_limit"] = v
    if "watermark" in body:
        cfg["watermark"] = bool(body["watermark"])
    if "upscale_default" in body:
        cfg["upscale_default"] = bool(body["upscale_default"])

    save_json(CONFIG_FILE, cfg)
    write_log("CONFIG", f'Settings updated by {session.get("admin_user")}: {body}')
    return jsonify({"success": True, **cfg})


@admin_bp.route("/admin/change_password", methods=["POST"])
@admin_required
def admin_change_password():
    """
    Changes the admin password stored as ADMIN_PASSWORD env var placeholder.
    In production this writes to a local creds file; for Render set env vars.
    """
    body = request.get_json(force=True) or {}
    pw   = body.get("password", "")
    if len(pw) < 8:
        return jsonify({"error": "Min 8 characters"}), 400

    cfg = load_config()
    cfg["admin_password_hash"] = hash_password(pw)
    save_json(CONFIG_FILE, cfg)
    write_log("SECURITY", f'Admin password changed by {session.get("admin_user")}')
    return jsonify({"success": True})


# ════════════════════════════════════════════════════════════════════════════
#  DANGER ZONE
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/danger/<action>", methods=["POST"])
@admin_required
def admin_danger(action):
    if action == "reset_guest_counts":
        raw   = load_json(GUESTS_FILE, {})
        today = today_str()
        for ip in raw:
            raw[ip].setdefault("dates", {})[today] = 0
            raw[ip]["today_count"] = 0
        save_json(GUESTS_FILE, raw)
        write_log("DANGER", f'Reset all guest daily counts by {session.get("admin_user")}')
        return jsonify({"success": True})

    if action == "reset_all_counts":
        users = load_users()
        today = today_str()
        for uname, udata in users.items():
            if uname == "__guests__":
                continue
            udata.setdefault("daily_counts", {})[today] = 0
        save_users(users)
        # also guests
        raw = load_json(GUESTS_FILE, {})
        for ip in raw:
            raw[ip].setdefault("dates", {})[today] = 0
            raw[ip]["today_count"] = 0
        save_json(GUESTS_FILE, raw)
        write_log("DANGER", f'Reset ALL daily counts by {session.get("admin_user")}')
        return jsonify({"success": True})

    return jsonify({"error": "Unknown action"}), 400


# ════════════════════════════════════════════════════════════════════════════
#  EXPORT
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/export/users")
@admin_required
def admin_export_users():
    if not os.path.exists(USERS_FILE):
        return jsonify({"error": "users.json not found"}), 404
    write_log("EXPORT", f'users.json exported by {session.get("admin_user")}')
    return send_file(
        USERS_FILE,
        as_attachment=True,
        download_name=f"users_{today_str()}.json",
        mimetype="application/json"
    )


# ════════════════════════════════════════════════════════════════════════════
#  LOGS
# ════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/admin/logs")
@admin_required
def admin_logs():
    logs = load_json(LOGS_FILE, [])
    return jsonify({"logs": logs[:200]})


# ════════════════════════════════════════════════════════════════════════════
#  MIDDLEWARE — track IP on every request
#  Add this to your main app.py (not in the blueprint) so it fires globally:
#
#      @app.before_request
#      def track_user_ip():
#          if current_user.is_authenticated:
#              users = load_json(USERS_FILE, {})
#              uname = current_user.username  # or however you store it
#              if uname in users:
#                  users[uname]["last_ip"]     = request.remote_addr
#                  users[uname]["last_active"] = now_str()
#                  save_json(USERS_FILE, users)
#
# ════════════════════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════════════════════
#  HOW TO WIRE INTO app.py
# ════════════════════════════════════════════════════════════════════════════
#
#  1. Copy this file (admin_routes.py) into the same folder as app.py
#
#  2. In app.py, near the top, add:
#
#       from admin_routes import admin_bp
#       app.register_blueprint(admin_bp)
#
#  3. Make sure Flask sessions are secret:
#       app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
#
#  4. Set env vars on Render (or .env locally):
#       ADMIN_USERNAME=your_admin_name
#       ADMIN_PASSWORD=your_secure_password
#
#  5. Visit  https://your-app.onrender.com/admin
#
#  6. Update your generate() route to:
#     a) Store last_ip in users.json:
#            users[username]["last_ip"]     = request.remote_addr
#            users[username]["last_active"] = now_str()
#     b) Store each generation in history with all fields:
#            {
#              "timestamp":       now_str(),
#              "original_prompt": original_prompt,
#              "expanded_prompt": expanded,
#              "style":           style,
#              "size":            size,
#              "language":        detected_language,
#              "seed":            seed,
#              "image_url":       url,
#              "image_path":      local_path,
#            }
#     c) For guests, write to guests.json:
#            {
#              "1.2.3.4": {
#                "dates":       {"2025-05-30": 3},
#                "today_count": 3,
#                "total":       18,
#                "last_active": "2025-05-30 14:22",
#                "last_prompt": "sunset",
#                "history":     [...]
#              }
#            }
#
# ════════════════════════════════════════════════════════════════════════════
