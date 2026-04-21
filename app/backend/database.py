from pathlib import Path
from supabase import create_client, Client
from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    jwt_secret: str = "sebrae-contratos-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8

    class Config:
        env_file = str(_ENV_FILE)


settings = Settings()

_client: Client | None = None


def get_db() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client
