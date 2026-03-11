from fastapi import APIRouter
from sqlalchemy.orm import Session

from core.database import check_db_connection

router = APIRouter(tags=["ops"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Verifica el estado del servicio y la conectividad con la base de datos.

    Returns:
        Estado del servicio y de la conexión a BD.

    Raises:
        HTTPException 503: Si la base de datos no está disponible.
    """
    from fastapi import HTTPException

    db_ok = check_db_connection()

    if not db_ok:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "db": "unavailable"},
        )

    return {"status": "ok", "db": "connected"}