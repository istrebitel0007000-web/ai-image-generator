"""
app/models/image.py

Data-only model definitions.
No business logic lives here — all logic is in services/.
Foreign keys use quoted strings per §2.4.1.
Enums are inner classes per §2.4.3.
"""
from __future__ import annotations

import datetime
import hashlib
import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, TypedDict


# ---------------------------------------------------------------------------
# Enums  (§2.4.3 — singular naming, inner to their owner where logical)
# ---------------------------------------------------------------------------

class ImageStyle(str, Enum):
    REALISTIC    = "realistic"
    ANIME        = "anime"
    OIL_PAINTING = "oil_painting"
    WATERCOLOR   = "watercolor"
    CARTOON      = "cartoon"
    CYBERPUNK    = "cyberpunk"
    FANTASY      = "fantasy"
    SKETCH       = "sketch"
    RENDER_3D    = "3d_render"
    VINTAGE      = "vintage"


class ImageSize(str, Enum):
    SQUARE    = "square"
    PORTRAIT  = "portrait"
    LANDSCAPE = "landscape"
    WIDE      = "wide"


class UserPlan(str, Enum):
    FREE = "free"
    PRO  = "pro"


class DetectedLanguage(str, Enum):
    ENGLISH  = "English"
    RUSSIAN  = "Russian"
    UZBEK    = "Uzbek"
    ARABIC   = "Arabic"
    TURKISH  = "Turkish"
    CHINESE  = "Chinese"


# ---------------------------------------------------------------------------
# TypedDicts  (§2.4.4 — JSONField-equivalent grouped fields)
# ---------------------------------------------------------------------------

class StyleMeta(TypedDict):
    label:  str
    emoji:  str
    suffix: str


class SizeMeta(TypedDict):
    label: str
    w:     int
    h:     int


class DailyCount(TypedDict):
    date:  str   # YYYY-MM-DD
    count: int


# ---------------------------------------------------------------------------
# Plain dataclasses (used as in-memory "model" objects — no ORM)
# ---------------------------------------------------------------------------

@dataclass
class GeneratedImage:
    filename:         str
    image_url:        str
    original_prompt:  str
    expanded_prompt:  str
    full_prompt:      str
    style:            str
    style_key:        str
    size:             str
    size_key:         str
    seed:             int
    timestamp:        str
    language:         str
    enhanced:         bool
    width:            int
    height:           int


@dataclass
class User:
    username:     str
    password:     str          # sha-256 hex digest or ""
    display_name: str
    avatar:       str
    login_method: str          # "password" | "google"
    plan:         str          # UserPlan value
    created:      str
    google_id:    str          = ""
    email:        str          = ""
    history:      List[dict]   = field(default_factory=list)
    favorites:    List[dict]   = field(default_factory=list)
    downloads:    List[dict]   = field(default_factory=list)
    daily_count:  dict         = field(default_factory=dict)


@dataclass
class Collection:
    id:          str
    name:        str
    description: str
    created:     str
    images:      List[str] = field(default_factory=list)   # list of filenames


@dataclass
class ShareLink:
    share_id:   str
    filename:   str
    image_url:  str
    prompt:     str
    style:      str
    created_by: str
    created_at: str
    views:      int = 0


@dataclass
class ApiKey:
    key:      str
    username: str
    label:    str
    created:  str
    uses:     int  = 0
    active:   bool = True
