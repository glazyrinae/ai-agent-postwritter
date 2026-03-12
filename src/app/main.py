from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.app.container import build_container
from src.app.routers import register_routers
from src.app.settings import settings
from src.core.errors import ConfigurationError
from src.core.errors.handlers import register_exception_handlers
from src.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.api_bearer_token.strip():
        raise ConfigurationError("API_BEARER_TOKEN must not be empty.")
    app.state.container = build_container(settings)
    logger.info("Application startup completed")
    yield
    logger.info("Application shutdown completed")


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(
        title=settings.app_name,
        description="API for vLLM + LoRA agents and long-form IT article generation",
        version=settings.app_version,
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    register_routers(application)
    return application


app = create_app()
