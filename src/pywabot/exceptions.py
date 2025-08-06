"""Custom exception types for the PyWaBot library."""


class PyWaBotError(Exception):
    """Base exception class for all PyWaBot errors."""


class PyWaBotConnectionError(PyWaBotError):
    """Raised when there is an issue connecting to the WhatsApp API server."""


class APIKeyMissingError(PyWaBotError):
    """Raised when the API key is not configured."""


class APIError(PyWaBotError):
    """
    Raised for general API errors.

    Attributes:
        message (str): The error message from the API.
        status_code (int): The HTTP status code of the response.
    """

    def __init__(self, message, status_code=None):
        self.message = message
        self.status_code = status_code
        super().__init__(f"API Error {status_code or ''}: {message}")


class AuthenticationError(APIError):
    """Raised for authentication-related errors (401, 403)."""
