"""
app/services/_prompt_enhance.py  (protected helper)

Enriches a short prompt with randomised artistic modifiers.
Works entirely offline — no external API needed.
Skips prompts already longer than 200 characters.
"""
from __future__ import annotations

import random
import re

_LIGHTING: list[str] = [
    "golden hour lighting",
    "dramatic rim lighting",
    "soft diffused light",
    "moody atmospheric lighting",
    "ethereal backlight",
    "neon glow",
    "cinematic volumetric fog",
    "dappled sunlight through leaves",
]

_MOOD: list[str] = [
    "epic and awe-inspiring",
    "serene and peaceful",
    "mysterious and dark",
    "vibrant and energetic",
    "melancholic and nostalgic",
    "magical and dreamlike",
]

_CAMERA: list[str] = [
    "wide-angle shot",
    "close-up macro",
    "aerial bird's-eye view",
    "low-angle dramatic perspective",
    "panoramic vista",
    "shallow depth of field",
]

_QUALITY: list[str] = [
    "ultra detailed, 8k resolution",
    "masterpiece quality",
    "hyper-realistic textures",
    "award-winning digital art",
    "trending on ArtStation",
    "highly detailed concept art",
]

_STYLE_HINTS: dict[str, str] = {
    "realistic":    "photorealistic, shot on Canon EOS R5,",
    "anime":        "anime key-visual, vibrant cel-shading,",
    "oil_painting": "masterful oil painting, visible brushwork,",
    "watercolor":   "delicate watercolor washes, wet-on-wet technique,",
    "cartoon":      "bold cartoon outlines, bright saturated palette,",
    "cyberpunk":    "neon-lit cyberpunk cityscape, rain-soaked reflections,",
    "fantasy":      "epic fantasy illustration, dramatic magical atmosphere,",
    "sketch":       "detailed pencil sketch, cross-hatching, monochrome,",
    "3d_render":    "Octane render, subsurface scattering, global illumination,",
    "vintage":      "vintage 35mm film, Kodachrome tones, slight vignette,",
}


def enhance_prompt(raw_prompt: str, style_key: str = "realistic") -> str:
    """
    Append artistic modifiers to `raw_prompt`.
    Returns the original string unchanged if it already exceeds 200 characters.
    """
    if not raw_prompt or not raw_prompt.strip():
        return raw_prompt
    if len(raw_prompt) > 200:
        return raw_prompt

    hint     = _STYLE_HINTS.get(style_key, "")
    enhanced = (
        f"{raw_prompt.strip()}, {hint} "
        f"{random.choice(_LIGHTING)}, "
        f"{random.choice(_MOOD)} mood, "
        f"{random.choice(_CAMERA)}, "
        f"{random.choice(_QUALITY)}"
    )
    return re.sub(r"\s{2,}", " ", enhanced).strip()
