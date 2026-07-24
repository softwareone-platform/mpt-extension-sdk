# Migrations

Shared migration knowledge lives in:

- [knowledge/migrations.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/migrations.md)

This file documents repository-specific migration behavior only.

## Repository Scope

This repository is an SDK and does not expose `mpt-service-cli` schema or data migration commands.

The `migrations` topic here covers SDK compatibility changes that require consumers to adjust configuration or usage.

## Current Migration Notes

### OTLP exporter is no longer enabled unconditionally

The observability bootstrap used to register the OTLP span exporter whenever
`SDK_OBSERVABILITY_ENABLED` was `true`, even without a reachable collector.
The OTLP exporter is now enabled only when `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
or `OTEL_EXPORTER_OTLP_ENDPOINT` is set.

Consumer action: deployments that relied on the implicit default OTLP endpoint
(`http://localhost:4318`) without declaring the endpoint variable must now set
`OTEL_EXPORTER_OTLP_ENDPOINT` explicitly. Setups that already declare the
endpoint (for example a local Jaeger collector) keep working unchanged.

### `Order.status` is now typed as `OrderStatus | str`

`mpt_extension_sdk.models.Order.status` changed from a plain `str` to
`OrderStatus | str`, where `OrderStatus` is a new `StrEnum` covering the
documented Marketplace order statuses (`Draft`, `Quoted`, `Processing`,
`Querying`, `Completed`, `Failed`, `Deleted`).

- A known status (case-insensitive) is parsed into an `OrderStatus` member;
  because `OrderStatus` is a `StrEnum`, comparisons against status strings keep
  working. Prefer `OrderStatus` members over raw literals in new code.
- An unknown status is **not** rejected: it is kept as a plain `str` and a
  `mpt_extension_sdk.models.order.UnknownOrderStatusWarning` is emitted, so
  payloads with new or unexpected statuses stay backward compatible.

Consumer action: none required. Code that reads `Order.status` as a string keeps
working; opt into `OrderStatus` where typed comparisons are useful.

Add a section here only when this repository introduces a consumer-facing
compatibility change that requires upgrade guidance.

## When To Update This Document

Update this file when the SDK introduces a consumer-facing compatibility change
that requires upgrade guidance.
