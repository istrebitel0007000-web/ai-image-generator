from flask import Blueprint, request, jsonify, session

from services.api_key_service import create_api_key, get_user_api_keys, revoke_api_key
from services.user_service import get_user_data, update_user

user_bp = Blueprint("user", __name__)


@user_bp.route("/api/v1/user/api-keys")
def list_api_keys():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login required"}), 401
    return jsonify(get_user_api_keys(username))


@user_bp.route("/api/v1/user/api-keys/create", methods=["POST"])
def create_key():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login required"}), 401
    data  = request.json or {}
    label = data.get("label", "My App")
    key   = create_api_key(username, label)
    return jsonify({"success": True, "key": key})


@user_bp.route("/api/v1/user/api-keys/revoke", methods=["POST"])
def revoke_key():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login required"}), 401
    data = request.json or {}
    key  = data.get("key", "")
    ok   = revoke_api_key(key, username)
    if not ok:
        return jsonify({"error": "Key not found or not yours"}), 404
    return jsonify({"success": True})


@user_bp.route("/api/v1/user/profile", methods=["POST"])
def update_profile():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login required"}), 401
    data         = request.json or {}
    user         = get_user_data(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    display_name = (data.get("display_name") or "").strip()
    if display_name:
        user["display_name"] = display_name[:50]
    update_user(username, user)
    return jsonify({"success": True, "display_name": user["display_name"]})
