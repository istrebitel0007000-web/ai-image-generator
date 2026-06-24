"""
app/views/enhance_prompt.py

CBV: EnhancePromptView
URL: POST /api/v1/prompts/enhance/
"""
from __future__ import annotations

from flask import request, jsonify, make_response
from flask.views import MethodView

from app.services.enhance_prompt import enhance_prompt
from app.services.generate_image import STYLES


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class EnhancePromptRequestSerializer:

    def __init__(self, data: dict):
        self.prompt    = (data.get("prompt") or "").strip()
        self.style_key = data.get("style", "realistic")

    def is_valid(self) -> tuple[bool, str]:
        if not self.prompt:
            return False, "prompt is required."
        if len(self.prompt) > 500:
            return False, "Prompt too long — maximum 500 characters."
        if self.style_key not in STYLES:
            return False, f"Unknown style '{self.style_key}'."
        return True, ""


class EnhancePromptResponseSerializer:

    def __init__(self, result: dict):
        self._result = result

    def data(self) -> dict:
        return {
            "original": self._result["original"],
            "expanded": self._result["expanded"],
            "enhanced": self._result["enhanced"],
            "language": self._result["language"],
            "style":    self._result["style"],
        }


# ---------------------------------------------------------------------------
# CBV
# ---------------------------------------------------------------------------

class EnhancePromptView(MethodView):

    def post(self):
        req = EnhancePromptRequestSerializer(request.json or {})
        valid, error = req.is_valid()
        if not valid:
            return make_response(jsonify({"error": error}), 400)

        try:
            result = enhance_prompt(prompt=req.prompt, style_key=req.style_key)
        except ValueError as exc:
            return make_response(jsonify({"error": str(exc)}), 400)

        serializer = EnhancePromptResponseSerializer(result)
        return make_response(jsonify(serializer.data()), 200)
