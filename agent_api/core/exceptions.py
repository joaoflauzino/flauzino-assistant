class InvalidAssistantResponseError(ValueError):
    def __init__(self, message="Invalid response: missing spending or limit details"):
        self.message = message
        super().__init__(self.message)
