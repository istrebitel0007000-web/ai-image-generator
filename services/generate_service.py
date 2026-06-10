import re
import random
import datetime
import urllib.error                  # ← ADDED for specific error catching
from flask import request as flask_request
from config import OUTPUT_DIR
from models.data import STYLES, SIZES
from services.language_service import detect_language, expand_prompt
from services.image_service import build_image_url, fetch_image_bytes, MAX_RETRIES
from services.usage_service import check_usage_limit, increment_user_daily_count, increment_guest_count, increment_global_stats
from services.history_service import add_user_history, add_guest_history, is_user_favorite

def generate_image(prompt, style_key, size_key, negative, username):
    """
    Core image generation.
    Returns (result_dict, error_str, http_code).
    """
    if not prompt:
        return None, "Please write a description first!", 400
    if len(prompt) > 500:
        return None, "Description too long (max 500 chars)", 400

    style = STYLES.get(style_key, STYLES["realistic"])
    size  = SIZES.get(size_key, SIZES["square"])

    allowed, used, limit, remaining = check_usage_limit(username)
    if not allowed:
        return None, f"Daily limit reached ({limit} images/day). Upgrade to Pro for more.", 429

    detected_lang   = detect_language(prompt)
    expanded_prompt = expand_prompt(prompt, detected_lang)
    full_prompt     = f"{expanded_prompt}, {style['suffix']}"
    if negative:
        full_prompt += f" --no {negative}"

    seed      = random.randint(1, 999_999_999)
    image_url = build_image_url(full_prompt, size["w"], size["h"], seed)

    # ── Network call — fetch_image_bytes handles retries internally ──
    try:
        image_data = fetch_image_bytes(image_url)
    except urllib.error.URLError as e:
        # Connection refused, DNS failure, HTTP error, timeout
        reason = str(e.reason) if hasattr(e, "reason") else str(e)
        return None, f"Image service unavailable after {MAX_RETRIES} attempts. Please try again shortly. ({reason[:80]})", 503
    except OSError as e:
        # Low-level socket / OS timeout
        return None, f"Connection timed out after {MAX_RETRIES} attempts. Please try again shortly.", 503
    except Exception as e:
        return None, f"Generation failed: {str(e)[:200]}", 500

    # ── Validate response ──────────────────────────────────────────────
    if len(image_data) < 1000:
        return None, "Image generation failed — empty response. Please try again.", 500

    # ── Save file ──────────────────────────────────────────────────────
    slug     = re.sub(r"[^\w]", "_", prompt[:30]).strip("_").lower() or "image"
    filename = f"{slug}_{seed}.png"
    (OUTPUT_DIR / filename).write_bytes(image_data)

    ts    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = {
        "image_url":       image_url,
        "filename":        filename,
        "original_prompt": prompt,
        "style":           style["label"],
        "style_key":       style_key,
        "size":            f"{size['w']}x{size['h']}",
        "size_key":        size_key,
        "seed":            seed,
        "timestamp":       ts,
        "language":        detected_lang,
    }

    # ── History & stats (100% unchanged) ──────────────────────────────
    if username:
        increment_user_daily_count(username)
        add_user_history(username, entry)
    else:
        ip = flask_request.remote_addr or "unknown"
        increment_guest_count(ip)
        add_guest_history(ip, entry)

    increment_global_stats(style_key, detected_lang)

    return {
        "success":           True,
        "image_url":         image_url,
        "filename":          filename,
        "prompt":            full_prompt,
        "original_prompt":   prompt,
        "expanded_prompt":   expanded_prompt,
        "size":              f"{size['w']}x{size['h']}",
        "width":             size["w"],
        "height":            size["h"],
        "style":             style["label"],
        "style_key":         style_key,
        "size_key":          size_key,
        "seed":              seed,
        "detected_language": detected_lang,
        "was_translated":    detected_lang != "English",
        "timestamp":         ts,
        "used_today":        used + 1,
        "limit_today":       limit,
        "remaining_today":   max(0, remaining - 1),
        "is_favorite":       is_user_favorite(username, filename) if username else False,
    }, None, 200
