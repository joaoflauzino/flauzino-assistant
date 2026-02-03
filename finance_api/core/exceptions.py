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


class LimitServiceError(ServiceError):
    def __init__(self, message="Limit Service Error"):
        self.message = message
        super().__init__(self.message)


class SpentServiceError(ServiceError):
    def __init__(self, message="Spent Service Error"):
        self.message = message
        super().__init__(self.message)

