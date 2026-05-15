"""
tests/generate/test_enhance_prompt.py

Tests for the enhance_prompt service.
One feature per file (§3.2.1).
"""
from __future__ import annotations

from unittest import TestCase


class TestEnhancePrompt(TestCase):

    # ── Success case ──────────────────────────────────────────────────

    def test_enhance_prompt_case_1(self):
        """
        Case: Short English prompt with cyberpunk style.
        Expected: Enhanced prompt contains original text and is longer.
        """
        from app.services.enhance_prompt import enhance_prompt

        result = enhance_prompt(prompt="a dragon", style_key="cyberpunk")

        self.assertIn("a dragon", result["enhanced"])
        self.assertGreater(len(result["enhanced"]), len("a dragon"))
        self.assertEqual(result["language"], "English")
        self.assertEqual(result["original"], "a dragon")

    # ── Success case: Russian input expanded then enhanced ────────────

    def test_enhance_prompt_case_2(self):
        """
        Case: Russian prompt — dragon and castle.
        Expected: Expanded prompt contains English equivalents; enhanced is longer still.
        """
        from app.services.enhance_prompt import enhance_prompt

        result = enhance_prompt(prompt="дракон и замок", style_key="fantasy")

        self.assertEqual(result["language"], "Russian")
        self.assertIn("dragon", result["expanded"].lower())
        self.assertIn("castle", result["expanded"].lower())
        self.assertGreater(len(result["enhanced"]), len(result["expanded"]))

    # ── Failure case: empty prompt ────────────────────────────────────

    def test_enhance_prompt_case_3(self):
        """
        Case: Empty prompt string.
        Expected: Raises ValueError.
        """
        from app.services.enhance_prompt import enhance_prompt

        with self.assertRaises(ValueError):
            enhance_prompt(prompt="", style_key="realistic")

    # ── Failure case: prompt too long ─────────────────────────────────

    def test_enhance_prompt_case_4(self):
        """
        Case: Prompt exceeds 500 character limit.
        Expected: Raises ValueError.
        """
        from app.services.enhance_prompt import enhance_prompt

        with self.assertRaises(ValueError):
            enhance_prompt(prompt="x" * 501, style_key="realistic")
