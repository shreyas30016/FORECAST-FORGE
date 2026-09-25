"""API error handling and exceptions."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from forecast_forge.logging_config import get_logger

logger = get_logger(__name__)


class APIException(Exception):
    """Base API Exception."""

    def __init__(
        self, code: str, message: str, status_code: int = 400, details: dict | None = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details or {}}},
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected global exceptions without leaking stack traces."""
    logger.error("Unhandled API exception on %s: %s", request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
                "details": {},
            }
        },
    )
