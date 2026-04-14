# Migrations

Shared migration knowledge lives in:

- [knowledge/migrations.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/migrations.md)

This file documents repository-specific migration behavior only.

## Repository Scope

This repository is an SDK and does not expose `mpt-service-cli` schema or data migration commands.

The `migrations` topic here covers SDK compatibility changes that require consumers to adjust configuration or usage.

## Current Migration Notes

### API Base URL Change

The SDK now standardizes Marketplace API requests on `/public/v1/`.

Repository-specific guidance:

- `MPTClient` appends `/public/v1/` to the configured base URL
- `MPT_API_BASE_URL` should not include `/v1` or `/public/v1`
- older configurations remain accepted for backward compatibility, but they are legacy input forms
- legacy inputs still resolve to the standardized final API path

Use:

```bash
export MPT_API_BASE_URL=https://api.example.com
```

Do not use:

```bash
export MPT_API_BASE_URL=https://api.example.com/v1
```

## When To Update This Document

Update this file when the SDK introduces a consumer-facing compatibility change that requires upgrade guidance.
