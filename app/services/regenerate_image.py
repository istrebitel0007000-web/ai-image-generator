"""
app/services/regenerate_image.py

Single responsibility: look up a past prompt by filename and re-generate.
"""
from __future__ import annotations

from typing import Optional

from app.models import GeneratedImage
from app.services.generate_image import generate_image
from app.services._storage import (
    get_user_history,
    get_guest_history,
)


def regenerate_image(
    *,
    prompt:      Optional[str],
    filename:    Optional[str],
    style_key:   str,
    size_key:    str,
    negative:    str,
    username:    Optional[str],
    ip:          str,
    use_enhance: bool = False,
) -> GeneratedImage:
    """
    Re-run a past generation.
    Resolves the original prompt from history when only a filename is given.
    Raises ValueError when the prompt cannot be resolved.
    """
    resolved_prompt = _resolve_prompt(prompt, filename, username, ip)

    return generate_image(
        prompt      = resolved_prompt,
        style_key   = style_key,
        size_key    = size_key,
        negative    = negative,
        username    = username,
        ip          = ip,
        use_enhance = use_enhance,
    )


# ---------------------------------------------------------------------------
# Protected helpers
# ---------------------------------------------------------------------------

def _resolve_prompt(
    prompt:   Optional[str],
    filename: Optional[str],
    username: Optional[str],
    ip:       str,
) -> str:
    if prompt and prompt.strip():
        return prompt.strip()

    if filename:
        found = _find_in_history(filename, username, ip)
        if found:
            return found

    raise ValueError(
        "Could not find the original prompt. "
        "Either pass 'prompt' directly or a valid 'filename' from your history."
    )


def _find_in_history(
    filename: str,
    username: Optional[str],
    ip:       str,
) -> Optional[str]:
    history = get_user_history(username) if username else get_guest_history(ip)
    for entry in history:
        if entry.get("filename") == filename:
            return entry.get("original_prompt", "")
    return None
