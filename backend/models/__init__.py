# Importar todos los modelos aquí para que Base.metadata los registre.
# Alembic importa este módulo en env.py para detectar cambios de esquema.
from models.source import Source, SourceType, SourceStatus  # noqa: F401
from models.artist import Artist  # noqa: F401
from models.track import Track  # noqa: F401
from models.track_artist import track_artists  # noqa: F401