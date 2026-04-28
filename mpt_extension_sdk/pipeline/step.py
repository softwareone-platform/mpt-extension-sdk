from abc import ABC, abstractmethod
from asyncio import CancelledError
from typing import Any


class BaseStep(ABC):
    """Base step class for pipeline execution."""

    @property
    def name(self) -> str:
        """Step name."""
        return self.__class__.__name__

    async def run(self, ctx: Any) -> None:
        """Execute the full step lifecycle.

        `post()` runs after `process()` both on success and on failure so the
        step can perform cleanup or compensating actions. If both `process()`
        and `post()` fail, the `post()` exception is raised and chained from
        the original processing error.
        """
        await self.pre(ctx)
        process_error: Exception | CancelledError | None = None
        try:
            await self.process(ctx)
        except (Exception, CancelledError) as error:
            process_error = error
        try:
            await self.post(ctx)
        except Exception as post_error:
            if process_error is not None:
                raise post_error from process_error
            raise
        if process_error is not None:
            raise process_error

    async def pre(self, ctx: Any) -> None:
        """Run pre-processing hook."""
        return  # noqa: WPS324

    @abstractmethod
    async def process(self, ctx: Any) -> None:
        """Run business processing."""
        raise NotImplementedError

    async def post(self, ctx: Any) -> None:
        """Run post-processing hook."""
        return  # noqa: WPS324
