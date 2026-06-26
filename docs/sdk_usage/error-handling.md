# Error Handling

The SDK centralizes runtime error mapping. Extension code expresses business
intent by raising typed exceptions, and the SDK maps each one to the correct
outcome: an event response for event/task routes, or a problem-details response
for API routes. Extensions do not implement their own response mappers.

This page covers the event/pipeline error model. For the API error model
(`application/problem+json`, `APIError` subclasses, `422`/`500` responses) see
[api.md](api.md).

## Exception Hierarchy

The SDK groups exceptions into three families.

Runtime errors (`mpt_extension_sdk.errors.runtime`):

- `ExtRuntimeError` — base runtime exception.
  - `ConfigError` — invalid runtime or metadata configuration.
  - `ValidationError` — a validation failure.

Pipeline errors (`mpt_extension_sdk.errors.pipeline`):

- `PipelineError` — base pipeline exception.
  - `CancelError` — processing should be canceled.
  - `DeferError` — processing should be retried later. Carries
    `delay_seconds` (default `300`; must be greater than `0`).
  - `FailError` — non-retriable failure outside the step-error model.

Step errors (`mpt_extension_sdk.errors.step`):

- `StepError` — base step exception.
  - `SkipStepError` — skip the current step and continue the pipeline.
  - `StopStepError` — stop the pipeline and cancel processing.
  - `DeferStepError` — stop the pipeline and defer for a later retry. Carries
    `delay_seconds` (default `300`).

## Raising Errors From Steps

In day-to-day flow logic you raise step errors. The pipeline translates them
into pipeline errors and invokes the matching hook (see
[contexts-and-pipelines.md](contexts-and-pipelines.md)):

| Raised in a step | Pipeline hook | Result |
| --- | --- | --- |
| `SkipStepError` | `on_step_skipped` | step skipped, pipeline continues |
| `StopStepError` | `on_step_stopped` | re-raised as `CancelError` |
| `DeferStepError` | `on_step_deferred` | re-raised as `DeferError(delay_seconds)` |
| any other `Exception` | `on_step_failed` | re-raised unchanged |

Practical rules for extension authors:

- raise `SkipStepError` when the current step does not apply
- raise `StopStepError` when the pipeline should stop with cancel semantics
- raise `DeferStepError` when third-party state is pending and the flow should be
  retried later
- raise `FailError` only when pipeline-level non-retriable failure semantics are
  needed outside the step-error model

```python
from typing import override

from mpt_extension_sdk.errors.step import DeferStepError, SkipStepError, StopStepError
from mpt_extension_sdk.pipeline import BaseStep, OrderContext


class SubmitVendorOrderStep(BaseStep):
    @override
    async def pre(self, ctx: OrderContext) -> None:
        if not ctx.order.lines:
            raise SkipStepError("Order has no lines to submit.")

    @override
    async def process(self, ctx: OrderContext) -> None:
        result = await submit_to_vendor(ctx)
        if result.is_rejected:
            raise StopStepError("Vendor rejected the order.")
        if result.is_pending:
            raise DeferStepError("Vendor order still pending.", delay_seconds=600)
```

## Defining Custom Errors

Extensions may subclass an SDK error to clarify business intent while keeping
the same runtime behavior:

```python
from mpt_extension_sdk.errors.step import StopStepError


class OrderFailedStopStepError(StopStepError):
    pass
```

## Event Response Mapping

For event and task routes, the SDK maps the final exception to an
`EventResponse` through `map_exception_to_event_response`:

| Exception | Event response |
| --- | --- |
| `CancelError` | `cancel(reason=...)` |
| `DeferError` | `reschedule(seconds=delay_seconds)` |
| `FailError` | `cancel(reason=...)` |
| `ExtRuntimeError` | `cancel(reason="Runtime error")` |
| any other exception | `cancel(reason="Unexpected error")` |

Because `StopStepError` becomes `CancelError` and `DeferStepError` becomes
`DeferError`, raising step errors is enough to drive the event outcome. You
rarely need to construct `CancelError` or `DeferError` directly.
