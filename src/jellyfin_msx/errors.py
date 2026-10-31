class PortalError(Exception):
    def __init__(self, status: int, message: str, *, category: str | None = None):
        self.status = status
        self.message = message
        self.category = category
        super().__init__(message)
