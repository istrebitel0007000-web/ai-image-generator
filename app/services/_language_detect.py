"""
app/services/_language_detect.py  (protected helper — not a public service)

Detects the language of a user prompt.
Supports: English, Russian, Uzbek, Arabic, Turkish, Chinese.
"""
from __future__ import annotations

import re

# Character sets
_RU_CYRILLIC   = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
_UZ_CYR_UNIQUE = set("ўқғҳ")
_AR_CHARS      = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")
_ZH_RANGE      = (0x4E00, 0x9FFF)

_UZ_LATIN_WORDS: frozenset = frozenset({
    "tog", "tog'", "qor", "gul", "ko'l", "bo'ri", "burgut",
    "navruz", "navro'z", "registon", "samarqand", "buxoro", "xiva",
    "toshkent", "chimyon", "plov", "atlas", "suzani", "do'ppi",
    "cho'l", "daryo", "osmon", "quyosh", "bahor", "kuz", "yoz", "qish",
    "chiroyli", "go'zal", "buyuk", "ulkan", "sokin", "yolg'iz",
    "qadimiy", "karvon", "ipak", "masjid", "oltin", "baxt", "orzu",
})

_TR_DISTINCTIVE: frozenset = frozenset({
    "gökyüzü", "gündoğumu", "gün", "batımı", "bulutlar", "orman",
    "dağlar", "şelale", "yıldızlar", "ejderha", "şövalye", "kale",
    "istanbul", "kapadokya", "pamukkale", "güzel", "antik", "gizemli",
    "devasa", "altın", "kırmızı", "yeşil", "beyaz", "siyah",
})


def detect_language(text: str) -> str:
    """Return one of: English, Russian, Uzbek, Arabic, Turkish, Chinese."""
    if not text or not text.strip():
        return "English"

    lower = text.lower()
    words = set(re.split(r"[\s,،.!?]+", lower))
    total = max(len(text.replace(" ", "")), 1)

    # Chinese — CJK ideographs
    zh_count = sum(1 for c in text if _ZH_RANGE[0] <= ord(c) <= _ZH_RANGE[1])
    if zh_count / total > 0.15:
        return "Chinese"

    # Arabic
    ar_count = sum(1 for c in text if c in _AR_CHARS)
    if ar_count / total > 0.20:
        return "Arabic"

    # Uzbek — unique Cyrillic letters
    if any(c in _UZ_CYR_UNIQUE for c in text):
        return "Uzbek"

    # Uzbek — Latin word list
    if words & _UZ_LATIN_WORDS:
        return "Uzbek"
    if any(w in lower for w in _UZ_LATIN_WORDS):
        return "Uzbek"

    # Russian — Cyrillic density
    cy_count = sum(1 for c in text if c in _RU_CYRILLIC)
    if cy_count / total > 0.25:
        return "Russian"

    # Turkish — distinctive vocabulary
    if words & _TR_DISTINCTIVE:
        return "Turkish"
    if any(w in lower for w in _TR_DISTINCTIVE):
        return "Turkish"

    return "English"
