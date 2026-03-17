from sqlalchemy import ForeignKey, Table, Column
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

# Tabla de asociación pura (sin columnas adicionales).
# Se define como Table, no como clase mapeada, porque no tiene atributos propios.
track_artists = Table(
    "track_artists",
    Base.metadata,
    Column(
        "track_id",
        UUID(as_uuid=True),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "artist_id",
        UUID(as_uuid=True),
        ForeignKey("artists.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)