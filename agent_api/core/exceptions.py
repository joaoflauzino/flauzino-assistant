class InvalidAssistantResponseError(ValueError):
    def __init__(self, message="Invalid response: missing spending or limit details"):
        self.message = message
        super().__init__(self.message)


class ServiceError(Exception):
    def __init__(self, message="Service Error"):
        self.message = message
        super().__init__(self.message)


class FinanceServerError(ServiceError):
    def __init__(self, message="Error in finance service"):
        self.message = message
        super().__init__(self.message)


class FinanceUnreachableError(ServiceError):
    def __init__(self, message="Finance API internal server error"):
        self.message = message
        super().__init__(self.message)


class InvalidSpentError(ServiceError):
    def __init__(self, message="Invalid spent"):
        self.message = message
        super().__init__(self.message)


class LLMProviderError(Exception):
    def __init__(self, message="LLM Gemini Error"):
        self.message = message
        super().__init__(self.message)


class LLMParsingError(ServiceError):
    def __init__(self, message="LLM Parsing Error"):
        self.message = message
        super().__init__(self.message)


class DatabaseError(ServiceError):
    def __init__(self, message="Database Error"):
        self.message = message
        super().__init__(self.message)


class OCRProcessingError(ServiceError):
    def __init__(self, message="OCR Processing Error"):
        self.message = message
        super().__init__(self.message)


class InvalidImageError(ServiceError):
    def __init__(self, message="Invalid or corrupted image file"):
        self.message = message
        super().__init__(self.message)

