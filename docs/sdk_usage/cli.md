# CLI And Metadata

The SDK ships the `mpt-ext` command (a Typer application) for the common
developer tasks of running an extension and managing its metadata. Running an
extension package built on the SDK exposes:

```bash
mpt-ext run --local
mpt-ext run
mpt-ext meta generate
mpt-ext meta validate
```

## Running The Extension

- `mpt-ext run --local` starts the local `FastAPI + uvicorn` runtime, intended
  for development and debugging.
- `mpt-ext run` starts the platform runtime (`mrok`/`ziticorn`): it builds
  metadata, registers the extension instance, and serves the extension.

## Metadata (`meta.yaml`)

The metadata artifact is generated from `ExtensionApp` and the route decorators,
so it stays in sync with the Python declarations and does not have to be
maintained by hand. The generated document contains:

- `openapi` — the OpenAPI path
- `version` — the metadata version (default `1.0.0`)
- `events` — one entry per event/task route (`event`, `condition`, `path`,
  `task`)
- `plugs` — one entry per registered plug, when the extension declares any

```yaml
openapi: /bypass/openapi.json
version: 1.0.0
events:
  - event: platform.commerce.order.created
    condition: "and(eq(type,Purchase),in(product.id,(PRD-5516-5707)))"
    path: /api/v2/events/orders/purchase
    task: true
plugs:
  - id: adobe
    name: Adobe
    description: Adobe widget
    icon: /static/adobe.png
    socket: commerce.agreements.agreement
    href: /static/main-menu.js
```

### `mpt-ext meta generate`

Writes `meta.yaml` from `ext_app.to_meta_config()`. Use it to (re)generate the
checked-in metadata after changing routes or plugs.

### `mpt-ext meta validate`

Validates the extension metadata and exits non-zero on any failure. It:

- validates that every plug `href` and `icon` resolves to an existing file under
  the local `static/` folder
- compares the checked-in `meta.yaml` against the metadata generated from the
  extension app

When validation fails, the command writes the freshly generated document to
`meta.generated.yaml` next to `meta.yaml` so the difference can be inspected,
and prints the reason. The CLI does not build frontend assets, validate
JavaScript modules, or check that the public `/static` endpoint is reachable; it
only validates the local static asset references declared by `PlugRouter`.
