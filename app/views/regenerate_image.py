"""
app/views/regenerate_image.py

CBV: RegenerateImageView
URL: POST /api/v1/images/regenerate/
"""
from __future__ import annotations

from flask import request, jsonify, make_response
from flask.views import MethodView

from app.services.regenerate_image import regenerate_image
from app.services.generate_image   import STYLES, SIZES
from app.services._storage         import check_usage_limit
from app.views._rate_limit         import attach_rate_limit_headers
from app.views._auth               import resolve_username
from app.views.generate_image      import GenerateImageResponseSerializer


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class RegenerateImageRequestSerializer:

    def __init__(self, data: dict):
        self.prompt      = (data.get("prompt")   or "").strip() or None
        self.filename    = (data.get("filename")  or "").strip() or None
        self.style_key   = data.get("style",  "realistic")
        self.size_key    = data.get("size",   "square")
        self.negative    = (data.get("negative") or "").strip()
        self.use_enhance = bool(data.get("enhance", False))

    def is_valid(self) -> tuple[bool, str]:
        if not self.prompt and not self.filename:
            return False, "Either 'prompt' or 'filename' is required."
        if self.style_key not in STYLES:
            return False, f"Unknown style '{self.style_key}'."
        if self.size_key not in SIZES:
            return False, f"Unknown size '{self.size_key}'."
        return True, ""


# ---------------------------------------------------------------------------
# CBV
# ---------------------------------------------------------------------------

class RegenerateImageView(MethodView):

    def post(self):
        username = resolve_username()
        ip       = request.remote_addr or "unknown"

        req = RegenerateImageRequestSerializer(request.json or {})
        valid, error = req.is_valid()
        if not valid:
            resp = make_response(jsonify({"error": error}), 400)
            return attach_rate_limit_headers(resp, username, ip)

        try:
            image = regenerate_image(
                prompt      = req.prompt,
                filename    = req.filename,
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

        payload = serializer.data()
        payload["regenerated"]      = True
        payload["source_filename"]  = req.filename

        resp = make_response(jsonify(payload), 200)
        return attach_rate_limit_headers(resp, username, ip)
