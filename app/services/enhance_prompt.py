"""
app/services/enhance_prompt.py  (public wrapper)

Single responsibility: enrich a raw prompt with artistic detail.
Delegates to the private _prompt_enhance helper.
"""
from __future__ import annotations

from app.services._language_detect import detect_language
from app.services._prompt_expand   import expand_prompt
from app.services._prompt_enhance  import enhance_prompt as _enhance


def enhance_prompt(*, prompt: str, style_key: str) -> dict:
    """
    Return a dict with original, expanded and enhanced versions of the prompt.
    Raises ValueError when prompt is empty or too long.
    """
    _validate(prompt)
    language = detect_language(prompt)
    expanded = expand_prompt(prompt, language)
    enhanced = _enhance(expanded, style_key)
    return {
        "original": prompt,
        "expanded": expanded,
        "enhanced": enhanced,
        "language": language,
        "style":    style_key,
    }


# ---------------------------------------------------------------------------
# Protected helpers
# ---------------------------------------------------------------------------

def _validate(prompt: str) -> None:
    if not prompt or not prompt.strip():
        raise ValueError("Prompt is required.")
    if len(prompt) > 500:
        raise ValueError("Prompt too long — maximum 500 characters.")
