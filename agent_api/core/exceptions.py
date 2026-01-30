class InvalidAssistantResponseError(ValueError):
    def __init__(self, message="Invalid response: missing spending or limit details"):
        self.message = message
        super().__init__(self.message)


class FinanceServiceError(Exception):
    def __init__(self, message="Error in finance service"):
        self.message = message
        super().__init__(self.message)


class FinanceServerError(FinanceServiceError):
    def __init__(self, message="Error in finance service"):
        self.message = message
        super().__init__(self.message)


class FinanceUnreachableError(FinanceServiceError):
    def __init__(self, message="Finance API internal server error"):
        self.message = message
        super().__init__(self.message)


class InvalidSpentError(FinanceServiceError):
    def __init__(self, message="Invalid spent"):
        self.message = message
        super().__init__(self.message)


class LLMError(Exception):
    def __init__(self, message="LLM Error"):
        self.message = message
        super().__init__(self.message)


class LLMProviderError(LLMError):
    def __init__(self, message="LLM Gemin Error"):
        self.message = message
        super().__init__(self.message)


class LLMParsingError(LLMError):
    def __init__(self, message="LLM Parsing Error"):
        self.message = message
        super().__init__(self.message)


class LLMUnknownError(LLMError):
    def __init__(self, message="Unknown LLM Error"):
        self.message = message
        super().__init__(self.message)
