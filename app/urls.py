"""
app/urls.py

All URL registrations.
Naming follows §1.5 (hyphens), §1.6 (CRUD suffixes), §1.4 (plural collections).
"""
from __future__ import annotations

from flask import Flask

from app.views.generate_image              import GenerateImageView
from app.views.batch_generate_images       import BatchGenerateImagesView
from app.views.enhance_prompt              import EnhancePromptView
from app.views.regenerate_image            import RegenerateImageView
from app.views.list_collections            import ListCollectionsView
from app.views.create_collection           import CreateCollectionView
from app.views.delete_collection           import DeleteCollectionView
from app.views.get_collection_detail       import GetCollectionDetailView
from app.views.add_image_to_collection     import AddImageToCollectionView
from app.views.remove_image_from_collection import RemoveImageFromCollectionView
from app.views.get_user_dashboard          import GetUserDashboardView


def register_urls(app: Flask) -> None:
    """Register all application URL rules."""

    # ── Images ────────────────────────────────────────────────────────
    app.add_url_rule(
        "/api/v1/images/generate/",
        view_func=GenerateImageView.as_view("generate-image"),
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/images/batch-generate/",
        view_func=BatchGenerateImagesView.as_view("batch-generate-images"),
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/images/regenerate/",
        view_func=RegenerateImageView.as_view("regenerate-image"),
        methods=["POST"],
    )

    # ── Prompts ───────────────────────────────────────────────────────
    app.add_url_rule(
        "/api/v1/prompts/enhance/",
        view_func=EnhancePromptView.as_view("enhance-prompt"),
        methods=["POST"],
    )

    # ── Collections ───────────────────────────────────────────────────
    app.add_url_rule(
        "/api/v1/collections/list/",
        view_func=ListCollectionsView.as_view("list-collections"),
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/collections/create/",
        view_func=CreateCollectionView.as_view("create-collection"),
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/collections/<collection_id>/detail/",
        view_func=GetCollectionDetailView.as_view("get-collection-detail"),
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/collections/<collection_id>/delete/",
        view_func=DeleteCollectionView.as_view("delete-collection"),
        methods=["DELETE"],
    )
    app.add_url_rule(
        "/api/v1/collections/<collection_id>/add-image/",
        view_func=AddImageToCollectionView.as_view("add-image-to-collection"),
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/v1/collections/<collection_id>/remove-image/",
        view_func=RemoveImageFromCollectionView.as_view("remove-image-from-collection"),
        methods=["DELETE"],
    )

    # ── Dashboard ─────────────────────────────────────────────────────
    app.add_url_rule(
        "/api/v1/dashboard/",
        view_func=GetUserDashboardView.as_view("get-user-dashboard"),
        methods=["GET"],
    )
