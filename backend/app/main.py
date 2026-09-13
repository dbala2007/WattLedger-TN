"""FastAPI application entry point.

Run locally with:  uv run uvicorn app.main:app --reload --port 8001
Then open:          http://127.0.0.1:8001/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.meters import router as meters_router
from app.api.readings import router as readings_router
from app.api.tariffs import router as tariffs_router
from app.core.config import settings
from app.core.logging import get_logger
from app.db.seed_data import seed_default_meters_if_missing, seed_default_tariff_plan_if_missing
from app.db.session import create_db_and_tables, engine
from app.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    NotFoundError,
    TariffConfigurationError,
)
from app.domain.readings import ReadingValidationError

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts - makes sure the SQLite tables exist
    # so a fresh checkout works without a separate manual migration step.
    logger.info("Starting WattLedger TN backend, ensuring database tables exist.")
    create_db_and_tables()
    with Session(engine) as session:
        seed_default_tariff_plan_if_missing(session)
        seed_default_meters_if_missing(session)
    yield


app = FastAPI(title="WattLedger TN API", version="0.1.0", lifespan=lifespan)

# Defaults to "*" for local development (the Flutter web dev server runs on
# an unpredictable localhost port), but production's .env sets CORS_ORIGINS
# to the real deployed origin(s) - CLAUDE.md section 14 requires this be
# restricted before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(meters_router)
app.include_router(readings_router)
app.include_router(tariffs_router)
app.include_router(billing_router)


# Translate domain-layer exceptions into the right HTTP status codes, in one
# place, instead of repeating try/except in every API endpoint.
@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ReadingValidationError)
def handle_validation_error(request: Request, exc: ReadingValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors})


@app.exception_handler(TariffConfigurationError)
def handle_tariff_configuration_error(request: Request, exc: TariffConfigurationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(InvalidCredentialsError)
def handle_invalid_credentials(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(EmailAlreadyRegisteredError)
def handle_email_already_registered(request: Request, exc: EmailAlreadyRegisteredError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ValueError)
def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
