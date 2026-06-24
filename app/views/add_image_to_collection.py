"""
app/views/add_image_to_collection.py

CBV: AddImageToCollectionView
URL: POST /api/v1/collections/<collection_id>/add-image/
"""
from __future__ import annotations

from flask import request, jsonify, make_response, session
from flask.views import MethodView

from app.services.add_image_to_collection import add_image_to_collection
from app.views._auth                      import require_login


class AddImageToCollectionRequestSerializer:

    def __init__(self, data: dict):
        self.filename = (data.get("filename") or "").strip()

    def is_valid(self) -> tuple[bool, str]:
        if not self.filename:
            return False, "filename is required."
        return True, ""


class AddImageToCollectionView(MethodView):

    @require_login
    def post(self, collection_id: str):
        username = session["username"]

        req = AddImageToCollectionRequestSerializer(request.json or {})
        valid, error = req.is_valid()
        if not valid:
            return make_response(jsonify({"error": error}), 400)

        try:
            add_image_to_collection(
                username      = username,
                collection_id = collection_id,
                filename      = req.filename,
            )
        except (LookupError, ValueError) as exc:
            status = 404 if isinstance(exc, LookupError) else 400
            return make_response(jsonify({"error": str(exc)}), status)

        return make_response(jsonify({"success": True}), 200)
