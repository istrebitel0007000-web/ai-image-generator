import secrets
import urllib.parse

from flask import Blueprint, request, jsonify, session, redirect

from config import GOOGLE_CLIENT_ID
from services.user_service import create_user, verify_user, get_user_data, get_or_create_google_user
from services.auth_service import google_get_auth_url, google_exchange_code, google_get_user_info
from services.usage_service import check_usage_limit

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/google")
def google_login():
    if not GOOGLE_CLIENT_ID:
        return jsonify({"error": "Google login not configured. Add GOOGLE_CLIENT_ID to environment."}), 503
    state                  = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    return redirect(google_get_auth_url(state))


@auth_bp.route("/auth/google/callback")
def google_callback():
    error = request.args.get("error")
    if error:
        return redirect("/?login_error=" + urllib.parse.quote(error))

    code  = request.args.get("code", "")
    state = request.args.get("state", "")

    if state != session.get("oauth_state"):
        return redirect("/?login_error=invalid_state")
    session.pop("oauth_state", None)

    if not code:
        return redirect("/?login_error=no_code")

    try:
        token_data   = google_exchange_code(code)
        access_token = token_data.get("access_token")
        if not access_token:
            return redirect("/?login_error=no_token")

        user_info = google_get_user_info(access_token)
        google_id = user_info.get("sub")
        email     = user_info.get("email", "")
        name      = user_info.get("name", email.split("@")[0])
        avatar    = user_info.get("picture", "")

        if not google_id or not email:
            return redirect("/?login_error=missing_profile")

        username           = get_or_create_google_user(google_id, email, name, avatar)
        session["username"] = username
        return redirect("/?login_success=1")
    except Exception as e:
        return redirect("/?login_error=" + urllib.parse.quote(str(e)[:100]))


@auth_bp.route("/auth/register", methods=["POST"])
def register():
    data     = request.json or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    ok, err  = create_user(username, password)
    if not ok:
        return jsonify({"error": err}), 400
    session["username"] = username
    user = get_user_data(username)
    return jsonify({
        "success":      True,
        "username":     username,
        "display_name": user.get("display_name", username),
        "avatar":       user.get("avatar", ""),
    })


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data     = request.json or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not verify_user(username, password):
        return jsonify({"error": "Wrong username or password"}), 401
    session["username"] = username
    user = get_user_data(username)
    return jsonify({
        "success":      True,
        "username":     username,
        "display_name": user.get("display_name", username),
        "avatar":       user.get("avatar", ""),
    })


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    session.pop("is_admin", None)
    return jsonify({"success": True})


@auth_bp.route("/auth/me")
def me():
    username = session.get("username")
    if not username:
        return jsonify({"logged_in": False})
    data = get_user_data(username)
    if not data:
        return jsonify({"logged_in": False})
    allowed, used, limit, remaining = check_usage_limit(username)
    return jsonify({
        "logged_in":          True,
        "username":           username,
        "display_name":       data.get("display_name", username),
        "avatar":             data.get("avatar", ""),
        "login_method":       data.get("login_method", "password"),
        "plan":               data.get("plan", "free"),
        "joined":             data.get("created", ""),
        "image_count":        len(data.get("history", [])),
        "favorite_count":     len(data.get("favorites", [])),
        "download_count":     len(data.get("downloads", [])),
        "used_today":         used,
        "limit_today":        limit,
        "remaining_today":    remaining,
        "google_configured":  bool(GOOGLE_CLIENT_ID),
    })
