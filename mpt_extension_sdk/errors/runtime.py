class ExtRuntimeError(Exception):
    """Base runtime exception for SDK errors."""


class AsyncTasksRunnerError(ExtRuntimeError):
    """Raised when an async task fails."""

    def __init__(self, message: str, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(message)


class ConfigError(ExtRuntimeError):
    """Raised when runtime or metadata configuration is invalid."""


class ValidationError(ExtRuntimeError):
    """Raised when a validation error occurs."""
