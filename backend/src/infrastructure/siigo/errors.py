from __future__ import annotations


class SiigoError(Exception):
    """Base error for the Siigo integration."""


class SiigoConfigurationError(SiigoError):
    """Siigo is enabled but required settings are missing."""


class SiigoAuthenticationError(SiigoError):
    """Siigo rejected the username/access_key pair."""


class SiigoApiError(SiigoError):
    """Siigo API returned an error response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Siigo API error {status_code}: {detail}")
