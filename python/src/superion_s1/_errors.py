from __future__ import annotations

from typing import Any, Mapping, Optional

__all__ = [
    "SuperionError",
    "APIConnectionError",
    "APITimeoutError",
    "APIStatusError",
    "BadRequestError",
    "AuthenticationError",
    "InsufficientBalanceError",
    "RequestTooLargeError",
    "UnprocessableError",
    "RateLimitError",
    "ServiceUnavailableError",
    "InternalServerError",
]


class SuperionError(Exception):
    """Base class for every error raised by this client."""


class APIConnectionError(SuperionError):
    """The API could not be reached (DNS, TLS, connection reset…)."""


class APITimeoutError(APIConnectionError):
    """The request timed out on the client side."""


class APIStatusError(SuperionError):
    """The API answered with a non-2xx status."""

    status_code: int = 0

    def __init__(self, message: str, *, status_code: int, body: Any = None,
                 headers: Optional[Mapping[str, str]] = None) -> None:
        super().__init__(f"{status_code}: {message}")
        self.message = message
        self.status_code = status_code
        self.body = body
        self.headers = dict(headers or {})

    @property
    def retry_after(self) -> Optional[float]:
        value = self.headers.get("retry-after")
        try:
            return float(value) if value is not None else None
        except ValueError:
            return None


class BadRequestError(APIStatusError):
    """400 — invalid JSON, unknown model or malformed question."""


class AuthenticationError(APIStatusError):
    """401 — missing, wrong, rotated or revoked key."""


class InsufficientBalanceError(APIStatusError):
    """402 — Prepaid balance is 0 or below. Add credits at https://punkytigerlabs.com/s1/."""

    @property
    def balance_usd(self) -> Optional[float]:
        return self.body.get("balance_usd") if isinstance(self.body, dict) else None


class RequestTooLargeError(APIStatusError):
    """413 — body over 4 MB."""


class UnprocessableError(APIStatusError):
    """422 — a question or the request exceeds the token limits, or too many options/levels."""


class RateLimitError(APIStatusError):
    """429 — quota used up, per-minute limit or queue full. See ``retry_after``."""


class ServiceUnavailableError(APIStatusError):
    """503 — service temporarily unavailable. See ``retry_after``."""


class InternalServerError(APIStatusError):
    """Other 5xx."""


_BY_STATUS = {
    400: BadRequestError,
    401: AuthenticationError,
    402: InsufficientBalanceError,
    413: RequestTooLargeError,
    422: UnprocessableError,
    429: RateLimitError,
    503: ServiceUnavailableError,
}


def error_for(status_code: int, body: Any, headers: Mapping[str, str]) -> APIStatusError:
    message = body.get("error") if isinstance(body, dict) and "error" in body else str(body or "")
    cls = _BY_STATUS.get(status_code) or (InternalServerError if status_code >= 500 else APIStatusError)
    return cls(message or "error", status_code=status_code, body=body, headers=headers)
