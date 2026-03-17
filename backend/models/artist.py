import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin


class Artist(Base, TimestampMixin):
    """Artista normalizado con su identificador canónico de MusicBrainz."""

    __tablename__ = "artists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    mbid: Mapped[str | None] = mapped_column(
        String(36),   # formato UUID de MusicBrainz: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        unique=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)

    # Relación N:M hacia tracks vía tabla de asociación
    tracks: Mapped[list["Track"]] = relationship(
        secondary="track_artists",
        back_populates="artists",
    )