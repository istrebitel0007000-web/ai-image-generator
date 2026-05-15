"""
app/services/create_collection.py

Single responsibility: validate and persist a new image collection.
"""
from __future__ import annotations

import datetime
import secrets

from app.models import Collection
from app.services._storage import load_collections, save_collections

_MAX_COLLECTIONS = 50
_MAX_NAME_LENGTH = 60
_MAX_DESC_LENGTH = 200


def create_collection(
    *,
    username:    str,
    name:        str,
    description: str = "",
) -> Collection:
    """
    Create and persist a new named collection for `username`.
    Raises ValueError on invalid input or duplicates.
    """
    _validate_name(name)
    name        = name.strip()
    description = description.strip()[:_MAX_DESC_LENGTH]

    cols      = load_collections()
    user_cols = cols.get(username, [])

    _check_duplicate(name, user_cols)
    _check_limit(user_cols)

    new_col = Collection(
        id          = secrets.token_urlsafe(8),
        name        = name,
        description = description,
        created     = datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        images      = [],
    )

    user_cols.append(_to_dict(new_col))
    cols[username] = user_cols
    save_collections(cols)

    return new_col


# ---------------------------------------------------------------------------
# Protected helpers
# ---------------------------------------------------------------------------

def _validate_name(name: str) -> None:
    name = name.strip() if name else ""
    if not name:
        raise ValueError("Collection name cannot be empty.")
    if len(name) > _MAX_NAME_LENGTH:
        raise ValueError(f"Collection name too long — maximum {_MAX_NAME_LENGTH} characters.")


def _check_duplicate(name: str, user_cols: list) -> None:
    if any(c["name"].lower() == name.lower() for c in user_cols):
        raise ValueError("A collection with that name already exists.")


def _check_limit(user_cols: list) -> None:
    if len(user_cols) >= _MAX_COLLECTIONS:
        raise ValueError(f"Maximum {_MAX_COLLECTIONS} collections reached.")


def _to_dict(col: Collection) -> dict:
    return {
        "id":          col.id,
        "name":        col.name,
        "description": col.description,
        "created":     col.created,
        "images":      col.images,
    }
