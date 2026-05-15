"""
app/views/batch_generate_images.py

CBV: BatchGenerateImagesView
URL: POST /api/v1/images/batch-generate/
"""
from __future__ import annotations

from flask import request, jsonify, make_response
from flask.views import MethodView

from app.services.batch_generate_images import batch_generate_images
from app.services.generate_image        import STYLES, SIZES
from app.services._storage              import check_usage_limit
from app.views._rate_limit              import attach_rate_limit_headers
from app.views._auth                    import resolve_username
from app.views.generate_image           import GenerateImageResponseSerializer


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class BatchGenerateImagesRequestSerializer:

    def __init__(self, data: dict):
        self.prompt      = (data.get("prompt")   or "").strip()
        self.style_key   = data.get("style",  "realistic")
        self.size_key    = data.get("size",   "square")
        self.negative    = (data.get("negative") or "").strip()
        self.count       = int(data.get("count", 2))
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
        if not 1 <= self.count <= 4:
            return False, "count must be between 1 and 4."
        return True, ""


class BatchGenerateImagesResponseSerializer:

    def __init__(self, result, username: str, ip: str):
        self._result   = result
        self._username = username
        self._ip       = ip

    def data(self) -> dict:
        _, used, limit, remaining = check_usage_limit(self._username, self._ip)
        images = []
        for img in self._result.images:
            s = GenerateImageResponseSerializer(img, self._username, used, limit, remaining)
            images.append(s.data())

        return {
            "success":         True,
            "batch_count":     self._result.generated,
            "requested":       self._result.requested,
            "images":          images,
            "partial_errors":  self._result.partial_errors or None,
            "used_today":      used,
            "limit_today":     limit,
            "remaining_today": remaining,
        }


# ---------------------------------------------------------------------------
# CBV
# ---------------------------------------------------------------------------

class BatchGenerateImagesView(MethodView):

    def post(self):
        username = resolve_username()
        ip       = request.remote_addr or "unknown"

        req = BatchGenerateImagesRequestSerializer(request.json or {})
        valid, error = req.is_valid()
        if not valid:
            resp = make_response(jsonify({"error": error}), 400)
            return attach_rate_limit_headers(resp, username, ip)

        try:
            result = batch_generate_images(
                prompt      = req.prompt,
                style_key   = req.style_key,
                size_key    = req.size_key,
                negative    = req.negative,
                username    = username,
                ip          = ip,
                count       = req.count,
                use_enhance = req.use_enhance,
            )
        except PermissionError as exc:
            resp = make_response(jsonify({"error": str(exc)}), 429)
            return attach_rate_limit_headers(resp, username, ip)
        except RuntimeError as exc:
            resp = make_response(jsonify({"error": str(exc)}), 500)
            return attach_rate_limit_headers(resp, username, ip)

        serializer = BatchGenerateImagesResponseSerializer(result, username, ip)
        resp = make_response(jsonify(serializer.data()), 200)
        return attach_rate_limit_headers(resp, username, ip)
