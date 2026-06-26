"""Unify material public media URLs.

Revision ID: f7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "f7a8b9c0d1e2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE biz_material_assets
        SET public_url = COALESCE(
            NULLIF(public_url, ''),
            NULLIF(remote_url, ''),
            NULLIF(third_party_url, '')
        )
        WHERE COALESCE(NULLIF(public_url, ''), NULLIF(remote_url, ''), NULLIF(third_party_url, '')) IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE biz_material_assets
        SET thumbnail_url = NULL
        WHERE thumbnail_url IS NOT NULL
          AND thumbnail_url <> ''
          AND (
            thumbnail_url = public_url
            OR thumbnail_url = remote_url
            OR thumbnail_url = third_party_url
          )
        """
    )


def downgrade() -> None:
    # Legacy columns are intentionally preserved; this data migration is not reversible
    # without guessing which public URL originally came from which alias.
    pass
