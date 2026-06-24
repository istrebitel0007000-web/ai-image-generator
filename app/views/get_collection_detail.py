"""
app/views/get_collection_detail.py

CBV: GetCollectionDetailView
URL: GET /api/v1/collections/<collection_id>/detail/
"""
from __future__ import annotations

from flask import jsonify, make_response, session
from flask.views import MethodView

from app.services._storage import load_collections
from app.views._auth       import require_login


class GetCollectionDetailResponseSerializer:

    def __init__(self, collection: dict):
        self._collection = collection

    def data(self) -> dict:
        c = self._collection
        return {
            "id":          c["id"],
            "name":        c["name"],
            "description": c.get("description", ""),
            "created":     c.get("created", ""),
            "images":      c.get("images", []),
            "image_count": len(c.get("images", [])),
        }


class GetCollectionDetailView(MethodView):

    @require_login
    def get(self, collection_id: str):
        username    = session["username"]
        user_cols   = load_collections().get(username, [])
        collection  = next((c for c in user_cols if c["id"] == collection_id), None)

        if not collection:
            return make_response(jsonify({"error": "Collection not found."}), 404)

        serializer = GetCollectionDetailResponseSerializer(collection)
        return make_response(jsonify(serializer.data()), 200)
