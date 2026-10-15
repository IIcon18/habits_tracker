import asyncio
import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.routes.events import broker
from app.core.config import settings
from app.core.exceptions import Conflict, DomainError, InvalidInput, NotFound
from app.core.notify import asyncpg_dsn, listen


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Изменения из бота и других запросов → открытые потоки /api/events.
    listener = asyncio.create_task(listen(asyncpg_dsn(settings.database_url), broker.publish))
    try:
        yield
    finally:
        listener.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener


app = FastAPI(title="Капля API", lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "X-Timezone"],
    )

app.include_router(api_router)

_STATUS = {
    NotFound: status.HTTP_404_NOT_FOUND,
    Conflict: status.HTTP_409_CONFLICT,
    InvalidInput: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


@app.exception_handler(DomainError)
async def domain_error(_: Request, exc: DomainError) -> JSONResponse:
    code = next((c for cls, c in _STATUS.items() if isinstance(exc, cls)), status.HTTP_400_BAD_REQUEST)
    return JSONResponse({"detail": exc.message}, status_code=code)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
