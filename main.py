from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from async_database import settings
from auth.dependencies import get_current_user
from urls.auth_router import auth_router
from urls.tracking_router import tracking_router

if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from cache.redis_cache import close_redis

    await close_redis()


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(tracking_router)


@app.get("/", dependencies=[Depends(get_current_user)])
async def root():
    return {"message": "Hello World"}
