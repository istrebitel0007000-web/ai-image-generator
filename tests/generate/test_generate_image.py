"""
tests/generate/test_generate_image.py

Tests for POST /api/v1/images/generate/
One feature per file (§3.2.1).
Each test has a success and failure case (tests_guide §each test must include at least two cases).
External calls are mocked (tests_guide §External resources should be mocked).
"""
from __future__ import annotations

import json
from unittest import TestCase
from unittest.mock import patch, MagicMock

from app.services.generate_image import generate_image, STYLES, SIZES


class TestGenerateImage(TestCase):
    """Tests for the generate_image service."""

    # ── Success case ──────────────────────────────────────────────────

    @patch("app.services.generate_image._fetch_image_bytes")
    @patch("app.services.generate_image._save_image")
    @patch("app.services.generate_image._record_usage")
    @patch("app.services._storage.check_usage_limit", return_value=(True, 3, 10, 7))
    def test_generate_image_case_1(
        self,
        mock_check_usage_limit,
        mock_record_usage,
        mock_save_image,
        mock_fetch_image_bytes,
    ):
        """
        Case: Valid English prompt with realistic style.
        Expected: Returns a GeneratedImage with correct fields.
        """
        mock_fetch_image_bytes.return_value = b"x" * 5000
        mock_save_image.return_value        = "dragon_12345.png"

        result = generate_image(
            prompt      = "A dragon over mountains",
            style_key   = "realistic",
            size_key    = "square",
            negative    = "",
            username    = "testuser",
            ip          = "127.0.0.1",
            use_enhance = False,
        )

        self.assertEqual(result.original_prompt, "A dragon over mountains")
        self.assertEqual(result.style_key, "realistic")
        self.assertEqual(result.language, "English")
        self.assertFalse(result.enhanced)
        self.assertIsNotNone(result.image_url)
        self.assertIsNotNone(result.seed)
        mock_record_usage.assert_called_once()

    # ── Failure case: daily limit reached ────────────────────────────

    @patch("app.services.generate_image.check_usage_limit", return_value=(False, 10, 10, 0))
    def test_generate_image_case_2(self, mock_check_usage_limit):
        """
        Case: Daily limit already reached.
        Expected: Raises PermissionError before any network call is made.
        """
        with self.assertRaises(PermissionError):
            generate_image(
                prompt    = "A castle at sunset",
                style_key = "fantasy",
                size_key  = "square",
                negative  = "",
                username  = "testuser",
                ip        = "127.0.0.1",
            )

    # ── Failure case: empty prompt ─────────────────────────────────

    def test_generate_image_case_3(self):
        """
        Case: Empty prompt string.
        Expected: Raises ValueError before any network call.
        No mocks needed — validation fires before quota check.
        """
        with self.assertRaises(ValueError) as ctx:
            generate_image(
                prompt    = "   ",
                style_key = "realistic",
                size_key  = "square",
                negative  = "",
                username  = None,
                ip        = "127.0.0.1",
            )
        self.assertIn("required", str(ctx.exception).lower())
