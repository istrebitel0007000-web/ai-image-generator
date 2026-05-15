"""
app/services/add_image_to_collection.py

Single responsibility: add one image filename to a collection.
"""
from __future__ import annotations

from app.services._storage import load_collections, save_collections

_MAX_IMAGES_PER_COLLECTION = 500


def add_image_to_collection(
    *,
    username:      str,
    collection_id: str,
    filename:      str,
) -> None:
    """
    Append `filename` to the specified collection.
    Raises LookupError when collection_id is not found.
    Raises ValueError on duplicates or capacity exceeded.
    """
    if not filename or not filename.strip():
        raise ValueError("filename is required.")

    cols      = load_collections()
    user_cols = cols.get(username, [])

    col = _find_collection(user_cols, collection_id)
    _check_duplicate(col, filename)
    _check_capacity(col)

    col["images"].insert(0, filename)
    cols[username] = user_cols
    save_collections(cols)


# ---------------------------------------------------------------------------
# Protected helpers
# ---------------------------------------------------------------------------

def _find_collection(user_cols: list, collection_id: str) -> dict:
    for col in user_cols:
        if col["id"] == collection_id:
            return col
    raise LookupError("Collection not found.")


def _check_duplicate(col: dict, filename: str) -> None:
    if filename in col["images"]:
        raise ValueError("Image already in this collection.")


def _check_capacity(col: dict) -> None:
    if len(col["images"]) >= _MAX_IMAGES_PER_COLLECTION:
        raise ValueError(f"Collection is full — maximum {_MAX_IMAGES_PER_COLLECTION} images.")
