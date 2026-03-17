"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enums ---
    source_type_enum = postgresql.ENUM(
        "shazam", "bookmark", "spotify", "txt", "telegram",
        name="source_type_enum",
    )
    source_status_enum = postgresql.ENUM(
        "pending", "processed", "failed", "manual_review",
        name="source_status_enum",
    )
    source_type_enum.create(op.get_bind(), checkfirst=True)
    source_status_enum.create(op.get_bind(), checkfirst=True)

    # --- Tabla: sources ---
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("source_type", sa.Enum(name="source_type_enum"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(name="source_status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detail", sa.Text, nullable=True),
    )

    # --- Tabla: artists ---
    op.create_table(
        "artists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mbid", sa.String(36), unique=True, nullable=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- Tabla: tracks ---
    op.create_table(
        "tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("mbid", sa.String(36), unique=True, nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("album", sa.String(512), nullable=True),
        sa.Column("album_cover_url", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column(
            "genres",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- Tabla: track_artists ---
    op.create_table(
        "track_artists",
        sa.Column(
            "track_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tracks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "artist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artists.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # --- Índices ---
    # Acelera el filtrado por estado (consulta más frecuente del worker)
    op.create_index("ix_sources_status", "sources", ["status"])
    # Acelera búsqueda de duplicados en ingesta batch
    op.create_index("ix_sources_source_type", "sources", ["source_type"])


def downgrade() -> None:
    op.drop_table("track_artists")
    op.drop_table("tracks")
    op.drop_table("artists")
    op.drop_table("sources")

    op.execute("DROP TYPE IF EXISTS source_type_enum")
    op.execute("DROP TYPE IF EXISTS source_status_enum")