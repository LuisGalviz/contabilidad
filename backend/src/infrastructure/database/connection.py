from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.app_debug,
    )


engine = _make_engine()
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables() -> None:
    from src.infrastructure.database import models as _  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def run_migrations() -> None:
    """Aplica las migraciones Alembic pendientes (equivalente a `alembic upgrade head`).

    Es síncrono: `alembic/env.py` levanta su propio engine async internamente, así
    que debe ejecutarse fuera del event loop (p. ej. vía `asyncio.to_thread`). Sirve
    tanto para una BD nueva (crea todo desde 0001) como para una existente (aplica
    solo lo que falte). La serialización entre varios workers se maneja con un
    advisory lock en `env.py`.
    """
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    backend_root = Path(__file__).resolve().parents[3]  # .../backend
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    command.upgrade(cfg, "head")


async def get_session() -> AsyncSession:  # type: ignore[misc]
    async with AsyncSessionLocal() as session:
        yield session
