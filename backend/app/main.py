"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1.health import router as health_router
from .api.v1.router import api_router
from .core.config import API_V1_PREFIX, APP_NAME, APP_VERSION, CORS_ORIGINS, DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD
from .core.logging import setup_logging
from .core.middleware import RequestContextMiddleware
from .core.security import hash_password
from .db.database import SessionLocal, init_db
from .db.models import UserRole
from .db.repositories.user_repository import UserRepository
from .core.config import LIVE_SIMULATOR_ENABLED
from .services.inference_engine import inference_engine
from .services.live_simulator import live_simulator
from .websockets.routes import router as ws_router

logger = logging.getLogger(__name__)


async def _seed_admin() -> None:
    async with SessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_email(DEFAULT_ADMIN_EMAIL)
        if user is None:
            await repo.create(
                DEFAULT_ADMIN_EMAIL,
                hash_password(DEFAULT_ADMIN_PASSWORD),
                UserRole.admin,
            )
            await session.commit()
            logger.info("Default admin created: %s", DEFAULT_ADMIN_EMAIL)
        elif user.role != UserRole.admin:
            user.role = UserRole.admin
            await session.commit()
            logger.info("Default admin role restored: %s", DEFAULT_ADMIN_EMAIL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting %s v%s", APP_NAME, APP_VERSION)
    await init_db()
    await _seed_admin()
    from .services.mitigation_service import mitigation_service

    async with SessionLocal() as session:
        await mitigation_service.load_blocklist(session)
        await session.commit()
    inference_engine.load_models()
    logger.info("Models loaded — API ready")
    if LIVE_SIMULATOR_ENABLED:
        live_simulator.start()
    yield
    if LIVE_SIMULATOR_ENABLED:
        await live_simulator.stop()
    logger.info("Shut down API")


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="Real-time DDoS detection using Graph Neural Networks",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health_router)
    app.include_router(api_router, prefix=API_V1_PREFIX)
    app.include_router(ws_router)

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.exception("Unhandled error path=%s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again later."})

    return app


app = create_app()
