"""
tests/collections/test_create_collection.py

Tests for the create_collection service.
One feature per file (§3.2.1).
"""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch


class TestCreateCollection(TestCase):

    # ── Success case ──────────────────────────────────────────────────

    @patch("app.services.create_collection.load_collections", return_value={})
    @patch("app.services.create_collection.save_collections")
    def test_create_collection_case_1(self, mock_save, mock_load):
        """
        Case: Valid name and description for a new user.
        Expected: Returns a Collection with correct fields; save is called once.
        """
        from app.services.create_collection import create_collection

        result = create_collection(
            username    = "alice",
            name        = "My Favourites",
            description = "Best generated images",
        )

        self.assertEqual(result.name, "My Favourites")
        self.assertEqual(result.description, "Best generated images")
        self.assertEqual(result.images, [])
        self.assertIsNotNone(result.id)
        mock_save.assert_called_once()

    # ── Failure case: duplicate name ──────────────────────────────────

    @patch("app.services.create_collection.load_collections", return_value={
        "alice": [{"id": "abc123", "name": "My Favourites", "images": []}]
    })
    @patch("app.services.create_collection.save_collections")
    def test_create_collection_case_2(self, mock_save, mock_load):
        """
        Case: Collection with the same name already exists.
        Expected: Raises ValueError; save is never called.
        """
        from app.services.create_collection import create_collection

        with self.assertRaises(ValueError) as ctx:
            create_collection(username="alice", name="My Favourites")

        self.assertIn("already exists", str(ctx.exception).lower())
        mock_save.assert_not_called()

    # ── Failure case: empty name ──────────────────────────────────────

    @patch("app.services.create_collection.load_collections", return_value={})
    @patch("app.services.create_collection.save_collections")
    def test_create_collection_case_3(self, mock_save, mock_load):
        """
        Case: Empty collection name.
        Expected: Raises ValueError; save is never called.
        """
        from app.services.create_collection import create_collection

        with self.assertRaises(ValueError) as ctx:
            create_collection(username="alice", name="   ")

        self.assertIn("empty", str(ctx.exception).lower())
        mock_save.assert_not_called()
