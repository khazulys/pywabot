class PyWaBotError(Exception):
    """Base exception class for all pywabot errors."""
    pass

class APIError(PyWaBotError):
    """
    Raised when the Baileys API server returns an error response.
    
    Attributes:
        status_code (int): The HTTP status code of the error response.
        message (str): The error message from the API.
    """
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message

    def __str__(self):
        if self.status_code:
            return f"[Status Code: {self.status_code}] {self.message}"
        return self.message

class ConnectionError(PyWaBotError):
    """Raised for connection-related issues, such as the server being offline."""
    pass

class AuthenticationError(APIError):
    """Raised for authentication or session-related failures."""
    pass

class APIKeyMissingError(PyWaBotError):
    """Raised when the API key is not configured."""
    pass