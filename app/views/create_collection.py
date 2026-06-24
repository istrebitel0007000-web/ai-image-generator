"""
app/views/create_collection.py

CBV: CreateCollectionView
URL: POST /api/v1/collections/create/
"""
from __future__ import annotations

from flask import request, jsonify, make_response, session
from flask.views import MethodView

from app.services.create_collection import create_collection
from app.views._auth                import require_login


class CreateCollectionRequestSerializer:

    def __init__(self, data: dict):
        self.name        = (data.get("name")        or "").strip()
        self.description = (data.get("description") or "").strip()

    def is_valid(self) -> tuple[bool, str]:
        if not self.name:
            return False, "name is required."
        if len(self.name) > 60:
            return False, "name too long — maximum 60 characters."
        return True, ""


class CreateCollectionResponseSerializer:

    def __init__(self, collection):
        self._collection = collection

    def data(self) -> dict:
        c = self._collection
        return {
            "id":          c.id,
            "name":        c.name,
            "description": c.description,
            "created":     c.created,
            "image_count": 0,
        }


class CreateCollectionView(MethodView):

    @require_login
    def post(self):
        username = session["username"]

        req = CreateCollectionRequestSerializer(request.json or {})
        valid, error = req.is_valid()
        if not valid:
            return make_response(jsonify({"error": error}), 400)

        try:
            collection = create_collection(
                username    = username,
                name        = req.name,
                description = req.description,
            )
        except ValueError as exc:
            return make_response(jsonify({"error": str(exc)}), 400)

        serializer = CreateCollectionResponseSerializer(collection)
        return make_response(jsonify({"success": True, "collection": serializer.data()}), 201)
