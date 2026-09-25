"""Domain exceptions for Forecast Forge AI."""


class ForecastForgeError(Exception):
    """Base exception for all domain errors in Forecast Forge AI."""


class ValidationError(ForecastForgeError):
    """Raised when data fails domain validation or physical realism constraints."""


class ProviderError(ForecastForgeError):
    """Base exception for external weather provider communication errors."""

    def __init__(self, message: str, provider_name: str, model_name: str | None = None) -> None:
        super().__init__(message)
        self.provider_name = provider_name
        self.model_name = model_name


class ProviderHTTPError(ProviderError):
    """Raised when an external provider returns an HTTP error status."""

    def __init__(
        self,
        message: str,
        provider_name: str,
        status_code: int,
        model_name: str | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message, provider_name, model_name)
        self.status_code = status_code
        self.response_body = response_body


class ProviderTimeoutError(ProviderError):
    """Raised when an external provider request times out."""


class ProviderRateLimitError(ProviderError):
    """Raised when an external provider rate limits requests (HTTP 429)."""


class ProviderMalformedDataError(ProviderError):
    """Raised when an external provider returns invalid or unparseable data."""
