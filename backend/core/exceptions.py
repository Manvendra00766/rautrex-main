class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class MarketDataError(AppError):
    def __init__(self, message: str = "Market data fetch failed"):
        super().__init__(message, status_code=502)

class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)

class RateLimitError(AppError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)

class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)
