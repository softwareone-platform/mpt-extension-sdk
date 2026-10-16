from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class TaskResult:
    """Reference to the resource that holds the outcome of a deferred call.

    The platform Task `result` field holds a relative URI, so a handler points at a
    resource instead of returning a document.
    """

    uri: str

    def __post_init__(self) -> None:
        """Reject a URI that is not relative.

        Raises:
            ValueError: If the URI does not start with `/`.
        """
        if not self.uri.startswith("/"):
            raise ValueError("Task result must be a relative URI starting with '/'")

    @classmethod
    def reference(cls, uri: str) -> Self:
        """Build a result that points at a platform resource.

        Args:
            uri: Relative URI, such as `/public/v1/commerce/agreements/AGR-1234-1234-1234`.

        Returns:
            The result the SDK stores on the Task when the handler returns.

        Raises:
            ValueError: If the URI does not start with `/`.
        """
        return cls(uri=uri)
