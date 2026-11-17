
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("smart_document_assistant")


class AppException(Exception):

    def __init__(
        self,
        message: str,
        status_code: int = 400
    ):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(AppException)
    async def handle_app_exception(
        request: Request,
        exc: AppException
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message
            }
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(
        request: Request,
        exc: Exception
    ):
        logger.exception(
            "Unexpected error on %s %s",
            request.method,
            request.url.path
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An unexpected server error occurred."
            }
        )
