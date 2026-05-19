from flask import Blueprint, request, jsonify, session, render_template

from config import ADMIN_USERNAME, ADMIN_PASSWORD
from services.usage_service import get_admin_stats, check_usage_limit
from services.user_service import load_users, get_user_data, update_user
from services.api_key_service import require_admin

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.json or {}
    if data.get("username") == ADMIN_USERNAME and data.get("password") == ADMIN_PASSWORD:
        session["is_admin"] = True
        return jsonify({"success": True})
    return jsonify({"error": "Wrong admin credentials"}), 401


@admin_bp.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    return jsonify({"success": True})


@admin_bp.route("/admin")
def admin_page():
    return render_template("admin.html")


@admin_bp.route("/admin/stats")
@require_admin
def admin_stats():
    return jsonify(get_admin_stats())


@admin_bp.route("/admin/users")
@require_admin
def admin_users():
    users  = load_users()
    result = []
    for uname, udata in users.items():
        _, used, limit, _ = check_usage_limit(uname)
        result.append({
            "username":     uname,
            "display_name": udata.get("display_name", uname),
            "plan":         udata.get("plan", "free"),
            "created":      udata.get("created", ""),
            "image_count":  len(udata.get("history", [])),
            "used_today":   used,
            "limit_today":  limit,
            "login_method": udata.get("login_method", "password"),
        })
    return jsonify(result)


@admin_bp.route("/admin/users/<username>/set-plan", methods=["POST"])
@require_admin
def admin_set_plan(username):
    data = request.json or {}
    plan = data.get("plan", "free")
    if plan not in ("free", "pro"):
        return jsonify({"error": "Invalid plan"}), 400
    user = get_user_data(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user["plan"] = plan
    update_user(username, user)
    return jsonify({"success": True, "username": username, "plan": plan})


@admin_bp.route("/admin/users/<username>/delete", methods=["POST"])
@require_admin
def admin_delete_user(username):
    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found"}), 404
    del users[username]
    from services.json_store import save_json
    from config import USERS_FILE
    save_json(USERS_FILE, users)
    return jsonify({"success": True})
