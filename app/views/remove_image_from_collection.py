"""
app/views/remove_image_from_collection.py

CBV: RemoveImageFromCollectionView
URL: DELETE /api/v1/collections/<collection_id>/remove-image/
"""
from __future__ import annotations

from flask import request, jsonify, make_response, session
from flask.views import MethodView

from app.services.remove_image_from_collection import remove_image_from_collection
from app.views._auth                           import require_login


class RemoveImageFromCollectionRequestSerializer:

    def __init__(self, data: dict):
        self.filename = (data.get("filename") or "").strip()

    def is_valid(self) -> tuple[bool, str]:
        if not self.filename:
            return False, "filename is required."
        return True, ""


class RemoveImageFromCollectionView(MethodView):

    @require_login
    def delete(self, collection_id: str):
        username = session["username"]

        req = RemoveImageFromCollectionRequestSerializer(request.json or {})
        valid, error = req.is_valid()
        if not valid:
            return make_response(jsonify({"error": error}), 400)

        try:
            remove_image_from_collection(
                username      = username,
                collection_id = collection_id,
                filename      = req.filename,
            )
        except LookupError as exc:
            return make_response(jsonify({"error": str(exc)}), 404)

        return make_response(jsonify({"success": True}), 200)
