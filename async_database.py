from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://dev:dev@localhost:5432/app"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"
    REDIS_URL: str = "redis://localhost:6379/1"
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

# Async SQLAlchemy needs an async driver; asyncpg uses postgresql+asyncpg://
def _async_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    return url


engine = create_async_engine(_async_database_url(settings.DATABASE_URL), echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db