"""
app/services/generate_image.py

Single responsibility: generate one image from a prompt.
All helpers are protected (_prefixed) per §2.2.4.
No HTTP, no serializer, no view logic here.
"""
from __future__ import annotations

import datetime
import io
import random
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from app.models import GeneratedImage, ImageStyle, ImageSize
from app.services._language_detect  import detect_language
from app.services._prompt_expand    import expand_prompt
from app.services._prompt_enhance   import enhance_prompt
from app.services._storage          import (
    OUTPUT_DIR,
    increment_user_daily_count,
    increment_guest_daily_count,
    add_user_history,
    add_guest_history,
    increment_global_stats,
    check_usage_limit,
)

# ---------------------------------------------------------------------------
# Public constants reused by views
# ---------------------------------------------------------------------------

STYLES: dict[str, dict] = {
    "realistic":    {"label": "Realistic",     "emoji": "📷",
                     "suffix": "photorealistic, 4k, highly detailed, sharp focus"},
    "anime":        {"label": "Anime",          "emoji": "🎌",
                     "suffix": "anime style, manga, vibrant colors, studio ghibli"},
    "oil_painting": {"label": "Oil Painting",   "emoji": "🎨",
                     "suffix": "oil painting, classical art, canvas texture, brush strokes"},
    "watercolor":   {"label": "Watercolor",     "emoji": "💧",
                     "suffix": "watercolor painting, soft edges, pastel colors, artistic"},
    "cartoon":      {"label": "Cartoon",        "emoji": "✏️",
                     "suffix": "cartoon style, colorful, fun, bold outlines, pixar style"},
    "cyberpunk":    {"label": "Cyberpunk",      "emoji": "🌆",
                     "suffix": "cyberpunk, neon lights, futuristic city, dark atmosphere, sci-fi"},
    "fantasy":      {"label": "Fantasy",        "emoji": "🐉",
                     "suffix": "fantasy art, magical, epic, detailed, dramatic lighting"},
    "sketch":       {"label": "Pencil Sketch",  "emoji": "✏️",
                     "suffix": "pencil sketch, black and white, hand drawn, detailed linework"},
    "3d_render":    {"label": "3D Render",      "emoji": "💎",
                     "suffix": "3d render, octane render, cinema4d, highly detailed, glossy"},
    "vintage":      {"label": "Vintage",        "emoji": "📸",
                     "suffix": "vintage photography, retro, film grain, faded colors, 1970s"},
}

SIZES: dict[str, dict] = {
    "square":    {"label": "Square (1:1)",      "w": 1024, "h": 1024},
    "portrait":  {"label": "Portrait (3:4)",    "w": 768,  "h": 1024},
    "landscape": {"label": "Landscape (16:9)",  "w": 1280, "h": 720},
    "wide":      {"label": "Wide (2:1)",        "w": 1280, "h": 640},
}

RANDOM_PROMPTS: list[str] = [
    "A dragon flying over a misty mountain at dawn",
    "Ancient library with floating books and candles",
    "Underwater city with glowing coral and mermaids",
    "A lone astronaut on a purple alien planet",
    "Enchanted forest with glowing mushrooms at night",
    "Wolf howling at a massive full moon in winter",
    "A phoenix rising from golden flames",
    "Futuristic Tokyo city at night in heavy rain",
    "A wizard casting spells in a dark stone tower",
    "A fairy tale castle on top of a waterfall",
    "Золотой закат над горами, одинокий волк воет на луну",
    "Древний замок в густом лесу, туман и тайна",
    "Registon maydoni kechqurun, oltin osmon va yulduzlar",
    "Samarqand ko'k gumbazlari, bahor va gullar",
    "غروب الشمس على البحر المتوسط مع ألوان ذهبية",
    "İstanbul gece gökyüzü altın ışıklar ile boğaz",
    "夜晚的城市霓虹灯倒映在雨水中",
]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_image(
    *,
    prompt:      str,
    style_key:   str,
    size_key:    str,
    negative:    str,
    username:    Optional[str],
    ip:          str,
    use_enhance: bool = False,
) -> GeneratedImage:
    """
    Generate a single image.
    Raises ValueError for bad input, RuntimeError on generation failure.
    """
    _validate_prompt(prompt)

    style = STYLES.get(style_key, STYLES["realistic"])
    size  = SIZES.get(size_key,   SIZES["square"])

    allowed, _, _, _ = check_usage_limit(username, ip)
    if not allowed:
        raise PermissionError("Daily generation limit reached. Upgrade to Pro for more.")

    language        = detect_language(prompt)
    expanded_prompt = expand_prompt(prompt, language)

    if use_enhance:
        expanded_prompt = enhance_prompt(expanded_prompt, style_key)

    full_prompt = f"{expanded_prompt}, {style['suffix']}"
    if negative:
        full_prompt += f" --no {negative}"

    seed      = random.randint(1, 999_999_999)
    image_url = _build_image_url(full_prompt, size["w"], size["h"], seed)
    image_data = _fetch_image_bytes(image_url)

    filename  = _save_image(image_data, prompt, seed)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    result = GeneratedImage(
        filename        = filename,
        image_url       = image_url,
        original_prompt = prompt,
        expanded_prompt = expanded_prompt,
        full_prompt     = full_prompt,
        style           = style["label"],
        style_key       = style_key,
        size            = f"{size['w']}x{size['h']}",
        size_key        = size_key,
        seed            = seed,
        timestamp       = timestamp,
        language        = language,
        enhanced        = use_enhance,
        width           = size["w"],
        height          = size["h"],
    )

    _record_usage(result, username, ip)
    return result


# ---------------------------------------------------------------------------
# Protected helpers  (§2.2.4)
# ---------------------------------------------------------------------------

def _validate_prompt(prompt: str) -> None:
    if not prompt or not prompt.strip():
        raise ValueError("Prompt is required.")
    if len(prompt) > 500:
        raise ValueError("Prompt too long — maximum 500 characters.")


def _build_image_url(prompt: str, w: int, h: int, seed: int) -> str:
    encoded = urllib.parse.quote(prompt)
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={w}&height={h}&seed={seed}&nologo=true&enhance=true"
    )


def _fetch_image_bytes(image_url: str) -> bytes:
    req = urllib.request.Request(
        image_url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as exc:
        raise RuntimeError(f"Image fetch failed: {exc}") from exc

    if len(data) < 1_000:
        raise RuntimeError("Image generation returned empty response — try again.")
    return data


def _save_image(image_data: bytes, prompt: str, seed: int) -> str:
    slug     = re.sub(r"[^\w]", "_", prompt[:30]).strip("_").lower() or "image"
    filename = f"{slug}_{seed}.png"
    (OUTPUT_DIR / filename).write_bytes(image_data)
    return filename


def _record_usage(
    result:   GeneratedImage,
    username: Optional[str],
    ip:       str,
) -> None:
    entry = {
        "image_url":       result.image_url,
        "filename":        result.filename,
        "original_prompt": result.original_prompt,
        "style":           result.style,
        "style_key":       result.style_key,
        "size":            result.size,
        "size_key":        result.size_key,
        "seed":            result.seed,
        "timestamp":       result.timestamp,
        "language":        result.language,
        "enhanced":        result.enhanced,
    }
    if username:
        increment_user_daily_count(username)
        add_user_history(username, entry)
    else:
        increment_guest_daily_count(ip)
        add_guest_history(ip, entry)

    increment_global_stats(result.style_key, result.language)
