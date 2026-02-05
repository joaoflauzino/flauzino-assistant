class FinanceError(Exception):
    def __init__(self, message="Error in finance service"):
        self.message = message
        super().__init__(self.message)


class DatabaseError(FinanceError):
    def __init__(self, message="Database Error"):
        self.message = message
        super().__init__(self.message)


class EntityNotFoundError(FinanceError):
    def __init__(self, message="Entity not found"):
        self.message = message
        super().__init__(self.message)


class EntityConflictError(FinanceError):
    def __init__(self, message="Entity conflict"):
        self.message = message
        super().__init__(self.message)


class ServiceError(FinanceError):
    def __init__(self, message="Service Error"):
        self.message = message
        super().__init__(self.message)


class ValidationError(FinanceError):
    """Raised when validation fails (HTTP 422)."""

    def __init__(self, message="Validation Error"):
        self.message = message
        super().__init__(self.message)
