from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada leída desde variables de entorno.

    Pydantic-settings valida tipos en tiempo de arranque: si falta una variable
    obligatoria, la aplicación falla con un mensaje claro antes de aceptar tráfico.
    """

    model_config = SettingsConfigDict(
        env_file=".env",           # ignorado dentro de Docker (vars ya están inyectadas)
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Base de datos
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"      # nombre del servicio en docker-compose
    postgres_port: int = 5432

    # Redis / Celery
    redis_url: str

    # Integraciones externas
    lastfm_api_key: str
    telegram_bot_token: str
    musicbrainz_user_agent: str

    @property
    def database_url(self) -> str:
        """URL de conexión sincrónica para SQLAlchemy y Alembic."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Instancia singleton — importar desde aquí en todo el proyecto
settings = Settings()