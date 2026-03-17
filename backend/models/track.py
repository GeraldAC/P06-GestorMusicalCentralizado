import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin


class Track(Base, TimestampMixin):
    """Track musical normalizado, enriquecido con metadatos de MusicBrainz y Last.fm."""

    __tablename__ = "tracks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,   # nullable para soportar SET NULL si se borra la source
    )
    mbid: Mapped[str | None] = mapped_column(
        String(36),
        unique=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    album: Mapped[str | None] = mapped_column(String(512), nullable=True)
    album_cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ARRAY nativo de PostgreSQL: evita tabla extra para una relación de solo lectura.
    # SQLAlchemy usa ARRAY(String) — el tipo concreto es VARCHAR[] en la BD.
    genres: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,    # default Python: [] en lugar de NULL
    )

    # Relaciones
    source: Mapped["Source"] = relationship(back_populates="track")
    artists: Mapped[list["Artist"]] = relationship(
        secondary="track_artists",
        back_populates="tracks",
    )