"""
app/services/batch_generate_images.py

Single responsibility: generate multiple images in parallel for one prompt.
Delegates each slot to generate_image service.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import List, Optional

from app.models import GeneratedImage
from app.services.generate_image import generate_image
from app.services._storage import check_usage_limit, get_user_data

# Free users: max 2 per batch. Pro users: max 4.
_BATCH_LIMIT_FREE = 2
_BATCH_LIMIT_PRO  = 4


@dataclass
class BatchResult:
    images:         List[GeneratedImage]
    partial_errors: List[str]
    requested:      int
    generated:      int


def batch_generate_images(
    *,
    prompt:      str,
    style_key:   str,
    size_key:    str,
    negative:    str,
    username:    Optional[str],
    ip:          str,
    count:       int,
    use_enhance: bool = False,
) -> BatchResult:
    """
    Generate `count` image variations in parallel.
    Raises PermissionError when quota is exhausted before starting.
    """
    count = _clamp_batch_count(count, username)

    allowed, _, _, remaining = check_usage_limit(username, ip)
    if not allowed:
        raise PermissionError("Daily generation limit reached. Upgrade to Pro for more.")

    # Never exceed remaining quota
    count = min(count, remaining)
    if count == 0:
        raise PermissionError("No remaining quota for today.")

    return _run_parallel(
        prompt      = prompt,
        style_key   = style_key,
        size_key    = size_key,
        negative    = negative,
        username    = username,
        ip          = ip,
        count       = count,
        use_enhance = use_enhance,
    )


# ---------------------------------------------------------------------------
# Protected helpers
# ---------------------------------------------------------------------------

def _clamp_batch_count(count: int, username: Optional[str]) -> int:
    user_data = get_user_data(username) if username else None
    is_pro    = bool(user_data and user_data.get("plan") == "pro")
    max_count = _BATCH_LIMIT_PRO if is_pro else _BATCH_LIMIT_FREE
    return max(1, min(int(count), max_count))


def _run_parallel(
    *,
    prompt:      str,
    style_key:   str,
    size_key:    str,
    negative:    str,
    username:    Optional[str],
    ip:          str,
    count:       int,
    use_enhance: bool,
) -> BatchResult:
    results: List[Optional[GeneratedImage]] = [None] * count
    errors:  List[Optional[str]]            = [None] * count
    lock = threading.Lock()

    def _worker(idx: int) -> None:
        try:
            img = generate_image(
                prompt      = prompt,
                style_key   = style_key,
                size_key    = size_key,
                negative    = negative,
                username    = username,
                ip          = ip,
                # Only enhance the first slot to avoid redundant processing
                use_enhance = use_enhance and idx == 0,
            )
            with lock:
                results[idx] = img
        except Exception as exc:
            with lock:
                errors[idx] = str(exc)

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)

    images         = [r for r in results if r is not None]
    partial_errors = [e for e in errors  if e is not None]

    if not images:
        first_error = partial_errors[0] if partial_errors else "All batch generations failed."
        raise RuntimeError(first_error)

    return BatchResult(
        images         = images,
        partial_errors = partial_errors,
        requested      = count,
        generated      = len(images),
    )
