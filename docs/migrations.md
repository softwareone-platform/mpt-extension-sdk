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


Add a section here only when this repository introduces a consumer-facing
compatibility change that requires upgrade guidance.

## When To Update This Document

Update this file when the SDK introduces a consumer-facing compatibility change
that requires upgrade guidance.
