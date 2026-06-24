"""
app/services/remove_image_from_collection.py

Single responsibility: remove one image filename from a collection.
"""
from __future__ import annotations

from app.services._storage import load_collections, save_collections


def remove_image_from_collection(
    *,
    username:      str,
    collection_id: str,
    filename:      str,
) -> None:
    """
    Remove `filename` from the specified collection.
    Raises LookupError when collection or image is not found.
    """
    cols      = load_collections()
    user_cols = cols.get(username, [])

    for col in user_cols:
        if col["id"] == collection_id:
            if filename not in col["images"]:
                raise LookupError("Image not found in this collection.")
            col["images"].remove(filename)
            cols[username] = user_cols
            save_collections(cols)
            return

    raise LookupError("Collection not found.")
