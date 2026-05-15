"""
app/services/delete_collection.py

Single responsibility: remove a collection by id.
"""
from __future__ import annotations

from app.services._storage import load_collections, save_collections


def delete_collection(*, username: str, collection_id: str) -> None:
    """
    Delete the named collection for `username`.
    Raises LookupError when collection_id is not found.
    """
    cols      = load_collections()
    user_cols = cols.get(username, [])
    updated   = [c for c in user_cols if c["id"] != collection_id]

    if len(updated) == len(user_cols):
        raise LookupError("Collection not found.")

    cols[username] = updated
    save_collections(cols)
