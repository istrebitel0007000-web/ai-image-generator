"""
tests/generate/test_language_detect.py

Tests for the _language_detect helper.
Declarative style, no loops (tests_guide §declarative style).
"""
from __future__ import annotations

from unittest import TestCase

from app.services._language_detect import detect_language


class TestDetectLanguage(TestCase):

    def test_detect_language_case_1(self):
        """
        Case: Plain English prompt.
        Expected: Returns 'English'.
        """
        self.assertEqual(detect_language("A dragon flying over mountains"), "English")

    def test_detect_language_case_2(self):
        """
        Case: Russian Cyrillic text with high density.
        Expected: Returns 'Russian'.
        """
        self.assertEqual(detect_language("Закат над горами дракон"), "Russian")

    def test_detect_language_case_3(self):
        """
        Case: Uzbek Latin word list match.
        Expected: Returns 'Uzbek'.
        """
        self.assertEqual(detect_language("Samarqand ko'k gumbazlari"), "Uzbek")

    def test_detect_language_case_4(self):
        """
        Case: Arabic script with high character density.
        Expected: Returns 'Arabic'.
        """
        self.assertEqual(detect_language("غروب الشمس على البحر"), "Arabic")

    def test_detect_language_case_5(self):
        """
        Case: Turkish distinctive vocabulary.
        Expected: Returns 'Turkish'.
        """
        self.assertEqual(detect_language("İstanbul gökyüzü gece"), "Turkish")

    def test_detect_language_case_6(self):
        """
        Case: Chinese CJK characters above threshold.
        Expected: Returns 'Chinese'.
        """
        self.assertEqual(detect_language("夜晚的城市霓虹灯"), "Chinese")

    def test_detect_language_case_7(self):
        """
        Case: Empty string.
        Expected: Defaults to 'English'.
        """
        self.assertEqual(detect_language(""), "English")
