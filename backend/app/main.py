"""
FastAPI application entrypoint.

    uvicorn app.main:app --reload

Mounts the versioned API, configures CORS for the SPA, and exposes health/root
endpoints. All business logic lives in the analytics engine and services; this
module only wires transport concerns.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import engine

logger = logging.getLogger("eternal.api")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Internal Product Analytics platform for a food-delivery marketplace. "
        "Executive KPIs, cohort/retention/RFM/CLV, delivery operations, coupon & "
        "marketing efficiency, forecasting, AI insights, a decision simulator, and "
        "a SQL explorer — the tools a Product Manager uses to make decisions."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"])
def root():
    return {
        "name": settings.APP_NAME,
        "status": "ok",
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        db_ok = False
        logger.warning("DB health check failed: %s", exc)
    return {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):  # pragma: no cover
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "path": request.url.path},
    )
