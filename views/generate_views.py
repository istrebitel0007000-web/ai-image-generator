import io
import random

from flask import Blueprint, request, jsonify, send_file, session

from models.data import STYLES, SIZES, RANDOM_PROMPTS, SUGGESTIONS
from services.generate_service import generate_image
from services.image_service import fetch_image_bytes, upscale_image, add_watermark
from services.history_service import (
    create_share, get_share, increment_share_views,
    toggle_user_favorite, log_user_download, get_guest_history, get_user_history,
    is_user_favorite,
)
from services.api_key_service import require_api_key
from config import OUTPUT_DIR, UPSCALE_DIR, WATERMARK_DIR

generate_bp = Blueprint("generate", __name__)


@generate_bp.route("/api/v1/generate", methods=["POST"])
def api_generate():
    data     = request.json or {}
    username = session.get("username")
    result, err, code = generate_image(
        prompt    = (data.get("prompt") or "").strip(),
        style_key = data.get("style", "realistic"),
        size_key  = data.get("size", "square"),
        negative  = (data.get("negative") or "").strip(),
        username  = username,
    )
    if err:
        return jsonify({"error": err}), code
    return jsonify(result)


@generate_bp.route("/api/v1/generate-api", methods=["POST"])
@require_api_key
def api_generate_with_key():
    data     = request.json or {}
    username = getattr(request, "api_username", None)
    result, err, code = generate_image(
        prompt    = (data.get("prompt") or "").strip(),
        style_key = data.get("style", "realistic"),
        size_key  = data.get("size", "square"),
        negative  = (data.get("negative") or "").strip(),
        username  = username,
    )
    if err:
        return jsonify({"error": err}), code
    return jsonify(result)


@generate_bp.route("/api/v1/styles")
def api_styles():
    return jsonify({
        k: {"label": v["label"], "emoji": v["emoji"]}
        for k, v in STYLES.items()
    })


@generate_bp.route("/api/v1/sizes")
def api_sizes():
    return jsonify(SIZES)


@generate_bp.route("/api/v1/random-prompt")
def api_random_prompt():
    return jsonify({"prompt": random.choice(RANDOM_PROMPTS)})


@generate_bp.route("/api/v1/suggestions")
def api_suggestions():
    q       = (request.args.get("q") or "").lower()
    results = []
    for prefix, suggestions in SUGGESTIONS.items():
        if q.startswith(prefix) or prefix.startswith(q):
            results.extend(suggestions)
    return jsonify({"suggestions": results[:8]})


@generate_bp.route("/api/v1/upscale", methods=["POST"])
def api_upscale():
    data      = request.json or {}
    image_url = data.get("image_url", "")
    scale     = int(data.get("scale", 2))
    filename  = data.get("filename", "image.png")
    if not image_url:
        return jsonify({"error": "image_url required"}), 400
    try:
        image_data          = fetch_image_bytes(image_url)
        upscaled, new_w, new_h = upscale_image(image_data, scale)
        out_filename        = f"upscaled_{filename}"
        (UPSCALE_DIR / out_filename).write_bytes(upscaled)
        return jsonify({
            "success":  True,
            "filename": out_filename,
            "width":    new_w,
            "height":   new_h,
        })
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@generate_bp.route("/api/v1/watermark", methods=["POST"])
def api_watermark():
    data      = request.json or {}
    image_url = data.get("image_url", "")
    text      = data.get("text", "AI Generated")
    position  = data.get("position", "bottom-right")
    opacity   = float(data.get("opacity", 0.6))
    size      = data.get("size", "medium")
    filename  = data.get("filename", "image.png")
    if not image_url:
        return jsonify({"error": "image_url required"}), 400
    try:
        image_data   = fetch_image_bytes(image_url)
        watermarked  = add_watermark(image_data, text, position, opacity, size)
        out_filename = f"wm_{filename}"
        (WATERMARK_DIR / out_filename).write_bytes(watermarked)
        return jsonify({"success": True, "filename": out_filename})
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@generate_bp.route("/api/v1/download")
def api_download():
    filename = request.args.get("filename", "")
    username = session.get("username")
    if not filename:
        return jsonify({"error": "filename required"}), 400
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        return jsonify({"error": "File not found"}), 404
    if username:
        log_user_download(username, {"filename": filename})
    return send_file(str(filepath), as_attachment=True, download_name=filename)


@generate_bp.route("/api/v1/share", methods=["POST"])
def api_share():
    data      = request.json or {}
    username  = session.get("username")
    share_id  = create_share(
        filename  = data.get("filename", ""),
        image_url = data.get("image_url", ""),
        prompt    = data.get("prompt", ""),
        style     = data.get("style", ""),
        username  = username,
    )
    return jsonify({"success": True, "share_id": share_id})


@generate_bp.route("/share/<share_id>")
def view_share(share_id):
    from flask import render_template
    share = get_share(share_id)
    if not share:
        return "Share not found", 404
    increment_share_views(share_id)
    return render_template("share.html", share=share, share_id=share_id)


@generate_bp.route("/api/v1/favorite", methods=["POST"])
def api_favorite():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Login required"}), 401
    data    = request.json or {}
    added, count = toggle_user_favorite(username, data)
    return jsonify({"success": True, "added": added, "count": count})


@generate_bp.route("/api/v1/history")
def api_history():
    username = session.get("username")
    if username:
        return jsonify(get_user_history(username))
    ip = request.remote_addr or "unknown"
    return jsonify(get_guest_history(ip))


@generate_bp.route("/api/v1/favorites")
def api_favorites():
    username = session.get("username")
    if not username:
        return jsonify([])
    from services.history_service import get_user_favorites
    return jsonify(get_user_favorites(username))


@generate_bp.route("/api/v1/downloads")
def api_downloads():
    username = session.get("username")
    if not username:
        return jsonify([])
    from services.history_service import get_user_downloads
    return jsonify(get_user_downloads(username))
