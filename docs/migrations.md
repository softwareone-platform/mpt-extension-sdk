# Migrations

Shared migration knowledge lives in:

- [knowledge/migrations.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/migrations.md)

This file documents repository-specific migration behavior only.

## Repository Scope

This repository is an SDK and does not expose `mpt-service-cli` schema or data migration commands.

The `migrations` topic here covers SDK compatibility changes that require consumers to adjust configuration or usage.

## Current Migration Notes

### `APIRouter.endpoint` is deprecated

`APIRouter.endpoint` now emits a `DeprecationWarning` when a route is
registered with it. It still registers an authenticated GET route, but it
supports neither a body validator nor a deferrable endpoint.

Consumer action: replace `@router.endpoint(path=..., name=...)` with
`@router.get(path=..., name=...)`. The registered route is the same.

### OTLP exporter is no longer enabled unconditionally

The observability bootstrap used to register the OTLP span exporter whenever
`SDK_OBSERVABILITY_ENABLED` was `true`, even without a reachable collector.
The OTLP exporter is now enabled only when `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
or `OTEL_EXPORTER_OTLP_ENDPOINT` is set.

Consumer action: deployments that relied on the implicit default OTLP endpoint
(`http://localhost:4318`) without declaring the endpoint variable must now set
`OTEL_EXPORTER_OTLP_ENDPOINT` explicitly. Setups that already declare the
endpoint (for example a local Jaeger collector) keep working unchanged.

### Task-backed events run on the async task runner

Handlers registered with `EventRouter.task(...)` used to run inside the
delivery request, and the delivery was answered `OK` or `Cancel` once the
handler returned. They now run on the application-scoped task runner, like
schedules and deferred calls, and follow the same delivery protocol: every
delivery of a non-final task is answered `Defer` on the watchdog cadence, and
`OK` only once the task is final.

Consumer action: none for the handler signature. Review handlers that relied on
the previous behavior:

- a handler now runs within the task's processing deadline, and one that
  exceeds it fails the task;
- task-backed events count towards `SDK_MAX_CONCURRENT_TASKS`, so raise the
  limit if it was sized for schedules and deferred calls only;
- a `DeferError` reschedules the task, and the next delivery follows the
  watchdog cadence rather than `delay_seconds`;
- a handler still running at shutdown is cancelled and its task failed.

Add a section here only when this repository introduces a consumer-facing
compatibility change that requires upgrade guidance.

## When To Update This Document

Update this file when the SDK introduces a consumer-facing compatibility change
that requires upgrade guidance.
