from fastapi import FastAPI, Request
from loguru import logger

from src.core.errors.exceptions import AppError
from src.core.errors.response import build_error_response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        return build_error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception):
        logger.exception("Unhandled application error")
        return build_error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
        )
