"""
app/views/list_collections.py

CBV: ListCollectionsView
URL: GET /api/v1/collections/list/
"""
from __future__ import annotations

from flask import jsonify, make_response, session
from flask.views import MethodView

from app.services._storage import load_collections
from app.views._auth       import require_login


class ListCollectionsResponseSerializer:

    def __init__(self, collections: list):
        self._collections = collections

    def data(self) -> list:
        return [
            {
                "id":          c["id"],
                "name":        c["name"],
                "description": c.get("description", ""),
                "created":     c.get("created", ""),
                "image_count": len(c.get("images", [])),
            }
            for c in self._collections
        ]


class ListCollectionsView(MethodView):

    @require_login
    def get(self):
        username    = session["username"]
        collections = load_collections().get(username, [])
        serializer  = ListCollectionsResponseSerializer(collections)
        return make_response(jsonify(serializer.data()), 200)
