import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


def _http_status_name(status_code: int) -> str:
    mapping = {
        400: "INVALID_ARGUMENT",
        401: "UNAUTHENTICATED",
        403: "PERMISSION_DENIED",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "ALREADY_EXISTS",
        422: "INVALID_ARGUMENT",
    }
    return mapping.get(status_code, "ERROR")


class ApiError(Exception):
    """Application error mapped to AIP-193-style JSON (no stack traces to clients)."""

    def __init__(self, *, http_status: int, status: str, message: str) -> None:
        self.http_status = http_status
        self.status = status
        self.message = message
        super().__init__(message)


def error_payload(http_status: int, status: str, message: str) -> dict:
    return {"error": {"code": http_status, "message": message, "status": status}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        status = _http_status_name(exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.status_code, status, message),
        )

    @app.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_payload(exc.http_status, exc.status, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        parts = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", ()) if x != "body")
            msg = err.get("msg", "Invalid value")
            parts.append(f"{loc}: {msg}" if loc else msg)
        message = "; ".join(parts) if parts else "Invalid request"
        return JSONResponse(
            status_code=422,
            content=error_payload(422, "INVALID_ARGUMENT", message),
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(_request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(422, "INVALID_ARGUMENT", str(exc)),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, StarletteHTTPException):
            message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            status = _http_status_name(exc.status_code)
            return JSONResponse(
                status_code=exc.status_code,
                content=error_payload(exc.status_code, status, message),
            )
        log.exception("Unhandled error: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_payload(500, "INTERNAL", "An unexpected error occurred."),
        )
