"""Errors carrying a message that is safe to show to the user."""


class FrontendError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class InvalidInputError(FrontendError):
    """The user left a required field blank."""


class CorrectionFailedError(FrontendError):
    """The backend could not produce a correction."""
