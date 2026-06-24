"""
app/views/generate_image.py

CBV: GenerateImageView  (§2.3.1, §2.3.4)
HTTP only — no business logic.
Serializers defined in this file per §2.1.5.
URL: POST /api/v1/images/generate/
"""
from __future__ import annotations

import datetime

from flask import request, jsonify, make_response, session
from flask.views import MethodView

from app.services.generate_image import generate_image, STYLES, SIZES
from app.services._storage import (
    check_usage_limit,
    get_user_data,
)
from app.views._rate_limit import attach_rate_limit_headers
from app.views._auth       import resolve_username


# ---------------------------------------------------------------------------
# Request / Response serializers  (§2.1.1, §2.1.5)
# ---------------------------------------------------------------------------

class GenerateImageRequestSerializer:
    """Validate and parse POST /api/v1/images/generate/ body."""

    def __init__(self, data: dict):
        self.prompt      = (data.get("prompt")   or "").strip()
        self.style_key   = data.get("style",  "realistic")
        self.size_key    = data.get("size",   "square")
        self.negative    = (data.get("negative") or "").strip()
        self.use_enhance = bool(data.get("enhance", False))

    def is_valid(self) -> tuple[bool, str]:
        if not self.prompt:
            return False, "prompt is required."
        if len(self.prompt) > 500:
            return False, "Prompt too long — maximum 500 characters."
        if self.style_key not in STYLES:
            return False, f"Unknown style '{self.style_key}'."
        if self.size_key not in SIZES:
            return False, f"Unknown size '{self.size_key}'."
        return True, ""


class GenerateImageResponseSerializer:
    """Serialize a GeneratedImage dataclass to a JSON-safe dict."""

    def __init__(self, image, username: str, used: int, limit: int, remaining: int):
        self._image     = image
        self._username  = username
        self._used      = used
        self._limit     = limit
        self._remaining = remaining

    def data(self) -> dict:
        img = self._image
        return {
            "success":           True,
            "image_url":         img.image_url,
            "filename":          img.filename,
            "prompt":            img.full_prompt,
            "original_prompt":   img.original_prompt,
            "expanded_prompt":   img.expanded_prompt,
            "size":              img.size,
            "width":             img.width,
            "height":            img.height,
            "style":             img.style,
            "style_key":         img.style_key,
            "size_key":          img.size_key,
            "seed":              img.seed,
            "detected_language": img.language,
            "was_translated":    img.language != "English",
            "enhanced":          img.enhanced,
            "timestamp":         img.timestamp,
            "used_today":        self._used,
            "limit_today":       self._limit,
            "remaining_today":   self._remaining,
            "is_favorite":       _is_favorite(self._username, img.filename),
        }


# ---------------------------------------------------------------------------
# CBV  (§2.3.4)
# ---------------------------------------------------------------------------

class GenerateImageView(MethodView):

    def post(self):
        username = resolve_username()
        ip       = request.remote_addr or "unknown"

        req = GenerateImageRequestSerializer(request.json or {})
        valid, error = req.is_valid()
        if not valid:
            resp = make_response(jsonify({"error": error}), 400)
            return attach_rate_limit_headers(resp, username, ip)

        try:
            image = generate_image(
                prompt      = req.prompt,
                style_key   = req.style_key,
                size_key    = req.size_key,
                negative    = req.negative,
                username    = username,
                ip          = ip,
                use_enhance = req.use_enhance,
            )
        except PermissionError as exc:
            resp = make_response(jsonify({"error": str(exc)}), 429)
            return attach_rate_limit_headers(resp, username, ip)
        except (ValueError, RuntimeError) as exc:
            resp = make_response(jsonify({"error": str(exc)}), 400)
            return attach_rate_limit_headers(resp, username, ip)

        _, used, limit, remaining = check_usage_limit(username, ip)
        serializer = GenerateImageResponseSerializer(image, username, used, limit, remaining)
        resp = make_response(jsonify(serializer.data()), 200)
        return attach_rate_limit_headers(resp, username, ip)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_favorite(username: str, filename: str) -> bool:
    if not username:
        return False
    data = get_user_data(username)
    if not data:
        return False
    return any(f.get("filename") == filename for f in data.get("favorites", []))
