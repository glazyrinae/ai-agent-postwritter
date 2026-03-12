class AppError(Exception):
    """Base application exception with stable API payload fields."""

    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(AppError):
    status_code = 500
    code = "CONFIGURATION_ERROR"


class OutlineParseError(AppError):
    status_code = 422
    code = "OUTLINE_PARSE_FAILED"


class UpstreamServiceError(AppError):
    status_code = 503
    code = "UPSTREAM_UNAVAILABLE"


class EmptyModelResponseError(AppError):
    status_code = 502
    code = "EMPTY_MODEL_RESPONSE"


class ResourceNotFoundError(AppError):
    status_code = 404
    code = "RESOURCE_NOT_FOUND"


class PersistenceError(AppError):
    status_code = 503
    code = "STORAGE_UNAVAILABLE"


class InvalidStateError(AppError):
    status_code = 409
    code = "INVALID_STATE"
