"""Application error codes and exception types.

Provider-specific and internal failures are mapped to a small set of stable
error codes so the API can return consistent, non-leaky error responses.
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    INVALID_USERNAME = "INVALID_USERNAME"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    PROFILE_PROTECTED = "PROFILE_PROTECTED"
    PROFILE_SUSPENDED = "PROFILE_SUSPENDED"
    NO_POSTS_AVAILABLE = "NO_POSTS_AVAILABLE"
    CREDENTIALS_MISSING = "CREDENTIALS_MISSING"
    RATE_LIMITED = "RATE_LIMITED"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    NETWORK_ERROR = "NETWORK_ERROR"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Default user-facing messages. Internal detail is never exposed here.
ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_USERNAME: "The username is invalid.",
    ErrorCode.PROFILE_NOT_FOUND: "This profile could not be found.",
    ErrorCode.PROFILE_PROTECTED: "This profile is protected and cannot be analyzed.",
    ErrorCode.PROFILE_SUSPENDED: "This profile is suspended or unavailable.",
    ErrorCode.NO_POSTS_AVAILABLE: "This profile has no public posts to analyze.",
    ErrorCode.CREDENTIALS_MISSING: "X API credentials are not configured.",
    ErrorCode.RATE_LIMITED: "The X API rate limit has been reached. Please try again later.",
    ErrorCode.UNSUPPORTED_LANGUAGE: "The detected language is not supported for full analysis.",
    ErrorCode.ANALYSIS_FAILED: "The analysis could not be completed.",
    ErrorCode.NETWORK_ERROR: "A network error occurred while contacting the data source.",
    ErrorCode.PROVIDER_ERROR: "The data provider returned an unexpected error.",
    ErrorCode.NOT_FOUND: "The requested resource was not found.",
    ErrorCode.VALIDATION_ERROR: "The request was invalid.",
    ErrorCode.INTERNAL_ERROR: "An internal error occurred.",
}


class AppError(Exception):
    """Base application error carrying a stable error code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        *,
        http_status: int = 400,
    ) -> None:
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "An error occurred.")
        self.http_status = http_status
        super().__init__(self.message)


class ProviderError(AppError):
    """Raised by data providers; already mapped to an ErrorCode."""


class ProfileNotFoundError(ProviderError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(ErrorCode.PROFILE_NOT_FOUND, message, http_status=404)


class ProfileProtectedError(ProviderError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(ErrorCode.PROFILE_PROTECTED, message, http_status=403)


class ProfileSuspendedError(ProviderError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(ErrorCode.PROFILE_SUSPENDED, message, http_status=404)


class RateLimitedError(ProviderError):
    def __init__(self, message: str | None = None, retry_after: int | None = None) -> None:
        super().__init__(ErrorCode.RATE_LIMITED, message, http_status=429)
        self.retry_after = retry_after


class CredentialsMissingError(ProviderError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(ErrorCode.CREDENTIALS_MISSING, message, http_status=503)
