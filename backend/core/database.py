from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # verifica la conexión antes de usarla (detecta desconexiones)
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base declarativa compartida por todos los modelos SQLAlchemy."""
    pass


def check_db_connection() -> bool:
    """Verifica que la base de datos sea accesible.

    Returns:
        True si la conexión es exitosa, False en caso contrario.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI que provee una sesión de BD por request.

    Garantiza que la sesión se cierre aunque ocurra una excepción.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()