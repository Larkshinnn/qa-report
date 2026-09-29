from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse, Response

from app.core.auth import Db
from app.core.auth import router as auth_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import AppError, ErrorBody
from app.modules.qa_reports.router import router as qa_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(title="QA Report", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
settings = get_settings()
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[host.strip() for host in settings.allowed_hosts.split(",") if host.strip()],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-QA-Request"],
)


@app.middleware("http")
async def local_security(request: Request, call_next: RequestResponseEndpoint) -> Response:
    # Mutations require same-origin + a non-simple header. No CORS is enabled.
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origins = get_settings().allowed_origins.split(",")
        if (
            request.headers.get("origin") not in origins
            or request.headers.get("x-qa-request") != "1"
        ):
            return JSONResponse(
                ErrorBody(detail="Permintaan lintas origin ditolak.").model_dump(), status_code=403
            )
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(AppError)
async def app_error(request: Request, error: AppError) -> JSONResponse:
    return JSONResponse(error.body.model_dump(mode="json"), status_code=error.status)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    # Do not reflect input or pydantic error contexts: they can contain passwords/secrets.
    return JSONResponse(
        ErrorBody(
            detail="Data tidak valid. Periksa kolom wajib dan batas panjang isian."
        ).model_dump(),
        status_code=422,
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        ErrorBody(
            detail="Server tidak dapat menyelesaikan permintaan. "
            "Data yang belum disimpan tetap ada di form."
        ).model_dump(),
        status_code=500,
    )


class Health(BaseModel):
    status: str


@app.get("/api/health")
async def health(db: Db) -> Health:
    await db.execute(text("SELECT 1"))
    return Health(status="ok")


app.include_router(auth_router)
app.include_router(qa_router)
