from fastapi import FastAPI

from api.routes import health

app = FastAPI(
    title="Gestor Musical Centralizado",
    version="0.1.0",
    description="API para consolidar y enriquecer historial musical personal.",
)

# Routers
app.include_router(health.router)

# A medida que se implementen nuevas épicas, los routers se registran aquí:
# app.include_router(tracks.router, prefix="/api/v1")
# app.include_router(artists.router, prefix="/api/v1")
# app.include_router(sources.router, prefix="/api/v1")
# app.include_router(webhook.router, prefix="/api/v1")