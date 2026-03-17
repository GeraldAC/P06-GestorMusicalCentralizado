import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin

import enum


class SourceType(str, enum.Enum):
    shazam = "shazam"
    bookmark = "bookmark"
    spotify = "spotify"
    txt = "txt"
    new_discovery = "new_discovery"


class SourceStatus(str, enum.Enum):
    pending = "pending"
    processed = "processed"
    failed = "failed"
    manual_review = "manual_review"


class Source(Base, TimestampMixin):
    """Registro crudo de cualquier entrada al sistema.

    Actúa como buffer de ingesta: todo dato que entre queda persistido
    aquí antes de ser procesado por el worker de enriquecimiento.
    """

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type_enum"),
        nullable=False,
    )
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, name="source_status_enum"),
        nullable=False,
        default=SourceStatus.pending,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relación inversa: una source puede derivar en un track
    track: Mapped["Track"] = relationship(back_populates="source", uselist=False)