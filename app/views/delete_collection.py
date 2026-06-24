"""
app/views/delete_collection.py

CBV: DeleteCollectionView
URL: DELETE /api/v1/collections/<collection_id>/delete/
"""
from __future__ import annotations

from flask import jsonify, make_response, session
from flask.views import MethodView

from app.services.delete_collection import delete_collection
from app.views._auth                import require_login


class DeleteCollectionView(MethodView):

    @require_login
    def delete(self, collection_id: str):
        username = session["username"]
        try:
            delete_collection(username=username, collection_id=collection_id)
        except LookupError as exc:
            return make_response(jsonify({"error": str(exc)}), 404)

        return make_response(jsonify({"success": True}), 200)
