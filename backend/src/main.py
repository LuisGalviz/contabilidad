from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import Counter, Histogram, generate_latest

from src.config import get_settings
from src.infrastructure.database.connection import create_tables
from src.presentation.api.v1 import auth, clients, reports, tenants, users

logger = structlog.get_logger()

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_DURATION = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting_application", env=get_settings().app_env)
    await create_tables()
    yield
    logger.info("shutting_down_application")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="API para gestión financiera y contable multi-tenant",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next: object) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[operator]
        duration = time.perf_counter() - start
        endpoint = request.url.path
        REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
        REQUEST_DURATION.labels(request.method, endpoint).observe(duration)
        response.headers["X-Process-Time"] = str(duration)
        return response

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["tenants"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    app.include_router(clients.router, prefix="/api/v1/clients", tags=["clients"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])

    @app.get("/health", tags=["observability"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "env": settings.app_env}

    @app.get("/metrics", tags=["observability"], include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type="text/plain")

    return app


app = create_app()
