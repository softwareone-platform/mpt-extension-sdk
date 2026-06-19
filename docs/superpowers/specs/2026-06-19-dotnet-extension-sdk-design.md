# .NET Extension SDK — Design

**Date:** 2026-06-19
**Status:** Approved for planning
**Authors:** MPT team (via Claude Code)

## Summary

The team is shifting SoftwareONE Marketplace extension development from the Python
`mpt-extension-sdk` to a pure .NET implementation. This document designs a small set of
reusable .NET libraries that a C# extension service can reference to get the same
capabilities the Python SDK provides today: a typed Marketplace API client, an extension
hosting/runtime model (instance registration, event/API routing, typed contexts,
pipelines), and OpenZiti-based platform transport.

The .NET libraries live in a **new, separate repository** (working name
`mpt-extension-sdk-dotnet`). They target **net8.0 (LTS)** and ship as NuGet packages.

## Goals

- Provide a typed, ergonomic Marketplace API client for C# services (orders, agreements,
  subscriptions, assets, products, installations, tasks, templates).
- Reproduce the two-token auth model: a long-lived extension key for bootstrap, and
  per-account JWT tokens that are minted, cached, and auto-refreshed.
- Reproduce instance registration and identity persistence.
- Provide an ASP.NET Core hosting model so a service can declare event/task handlers and
  API endpoints, receive typed contexts, and process them through pipelines.
- Connect to the platform over OpenZiti, matching today's `ziticorn` transport, while
  keeping local development on plain Kestrel.

## Non-Goals

- Porting the Python `Plug` and `Schedule` route families. (`Plug` is declarative
  metadata + static assets; `Schedule` is modeled but not mounted in the Python runtime.)
  These can be added later; they are out of scope for the first deliverable.
- Porting the Typer-based `mpt-ext` CLI. Metadata generation is provided as a library
  capability and (optionally) a `dotnet` tool later.
- A drop-in line-by-line port. We map Python concepts onto idiomatic .NET
  (minimal-API/builder style, `HttpClient`, `IHostedService`, DI) rather than mirroring
  Python class structure.

## Reference: what the Python SDK does today

The behaviours we are reproducing (verified against `mpt_extension_sdk/`):

- **Registration** (`runtime/bootstrap/registration.py`): builds
  `{externalId, version, meta}`, adds `channel: {}` when no matching identity exists, then
  `POST /public/v1/integration/extensions/{extensionId}/instances` with a bearer extension
  key. The response's `channel.identity` (OpenZiti credentials, keyed under `mrok`) is
  persisted to an identity file.
- **Transport** (`runtime/runner.py`): local mode runs `uvicorn`; platform mode calls
  `register_instance()` then serves the ASGI app through `ziticorn.run(app, identityFile, …)`.
- **API client** (`services/mpt_api_service/`): `MPTAPIService` wraps an async client and
  exposes sub-services. Account scoping is done by an account-token provider that injects a
  fresh per-account JWT on every request (60s refresh leeway, per-account lock).
- **Routing** (`routing/`): `EventRouter` (event vs task delivery), `ApiRouter` (REST).
- **Pipeline** (`pipeline/`): `BasePipeline`/`BaseStep` with `pre/process/post` lifecycle
  and `Defer`/`Skip`/`Stop`/`Fail` control-flow signals; typed `OrderContext` /
  `AgreementContext` built by a context factory from the inbound event.
- **Auth** (`api/auth/`, `jwt.py`): extracts `Authorization: Bearer`, decodes (does not
  verify — the gateway verifies) SoftwareONE claims
  (`https://claims.softwareone.com/{accountId,accountType,extensionId,modules}`), checks
  `exp` with a leeway.

## Package architecture

Three NuGet packages, split so the heavy/native Ziti dependency is isolated:

```
Swo.Mpt.ApiClient          (HttpClient only)
        ▲
        │
Swo.Mpt.Extensions.Hosting (ASP.NET Core; depends on ApiClient)
        ▲
        │
Swo.Mpt.Extensions.Ziti    (depends on Hosting + OpenZiti.NET)
```

A consuming service references:

- `ApiClient` alone for pure outbound API access, **or**
- `Hosting` to author an extension that runs on plain Kestrel (local dev), **or**
- `Hosting` + `Ziti` for platform deployment over the Ziti overlay.

### `Swo.Mpt.ApiClient`

Mirrors `services/mpt_api_service`, `api/auth`, and `models`.

- **Domain models**: records for Agreement, Order, Subscription, Asset, Product,
  ProductItem, Installation, Task, Template, plus shared types (Account, Address, Contact,
  Parameter, Price, Licensee, Authorization, ExternalId, Audit). System.Text.Json with
  source-generated contexts.
- **`IMptApiClient`** exposing sub-clients:
  `Agreements`, `Orders`, `Subscriptions`, `Assets`, `Products`, `ProductItems`,
  `Installations`, `Tasks`, `Templates`, `AccountTokens`.
  Operations follow the Python services, e.g. `Orders.GetByIdAsync`, `Orders.CompleteAsync`,
  `Orders.QueryAsync`, `Orders.FailAsync`, `Orders.UpdateAsync`;
  `Agreements.GetAllAsync` (paginated), `GetByIdAsync`, `UpdateAsync`;
  `Assets.CreateAsync` / `CreateOrderAssetAsync`; `Subscriptions.Create*`; etc.
- **Pagination**: `PaginatedCollection<T> { Limit, Offset, Total, IReadOnlyList<T> Resources }`
  with an `IAsyncEnumerable<T>` convenience wrapper for auto-paging.
- **Auth**:
  - `SoftwareOneJwt.ParseClaims(token)` — decode (not verify) claims; typed accessors for
    accountId, accountType (`Client`/`Operations`/`Vendor`), extensionId, modules; expiry
    check with leeway.
  - `IAccountTokenProvider` — given an account id, returns a valid token, minting via
    `POST /public/v1/integration/installations/token?account.id={id}` using the extension
    key, caching per account, refreshing within a leeway window, serialized per-account.
  - Two factory paths matching Python `from_config` (extension key) and
    `from_auth_context` (account-scoped). Account scoping is implemented as a
    `DelegatingHandler` that injects the fresh per-account token.
- Configured through `IHttpClientFactory` + typed `MptApiOptions` (base URL, extension key,
  timeouts). No ASP.NET Core dependency.

### `Swo.Mpt.Extensions.Hosting`

Mirrors `runtime`, `routing`, `pipeline`, `extension_app`. ASP.NET Core integration.

- **Authoring API** (builder style over ASP.NET Core):
  ```csharp
  var builder = ExtensionApp.CreateBuilder(args);
  builder.Events.OnTask("order.created", async (OrderContext ctx) => { ... });
  builder.Events.OnEvent("agreement.updated", async (AgreementContext ctx) => { ... });
  builder.Api.MapGet("/things/{id}", (ApiContext ctx, string id) => Results.Ok());
  var app = builder.Build();
  await app.RunAsync();
  ```
- **Contexts**: `ExtensionContext` (base: logger, `IMptApiClient`, settings, auth),
  `EventContext` (+ event metadata, mutable state bag), `OrderContext` (+ `Order`,
  `RefreshOrderAsync`), `AgreementContext` (+ `Agreement`, `RefreshAgreementAsync`),
  `ApiContext` (+ request, auth). A context factory inspects the inbound event's object
  type, fetches the Order/Agreement via the account-scoped client, and builds the right
  typed context.
- **Pipeline engine**: `IPipelineStep` with `PreAsync`/`ProcessAsync`/`PostAsync`
  (`post` always runs); `Pipeline` runs steps sequentially; control-flow via exceptions
  `DeferStepException`, `SkipStepException`, `StopStepException`, `FailException`. The event
  handler maps these onto task lifecycle calls.
- **Registration + lifecycle**: an `IHostedService` runs registration on startup
  (build payload → POST instances → persist identity), then hands off to the configured
  transport. Plain-Kestrel transport is the default in this package.
- **Metadata**: generate `meta.yaml` (events and their metadata) before startup, matching
  the Python `meta_config` contract.
- **Request handling**: minimal-API endpoints that authenticate the JWT, build the
  account-scoped client + typed context, invoke the handler/pipeline, and translate results
  into task lifecycle calls (`Tasks.Start/Complete/Fail/Reschedule`). Correlation-id and
  task-id headers flow through `Activity`/logging scope.

### `Swo.Mpt.Extensions.Ziti`

Mirrors `mrok`/`ziticorn`. Isolated native dependency (`OpenZiti.NET`).

- Maps the persisted platform identity (`channel.identity`, the `mrok`-keyed JSON) to an
  OpenZiti identity the SDK can load.
- Provides the Ziti-bound server transport that replaces Kestrel's default TCP listener,
  registered via `builder.UseZitiTransport()`.
- **Target transport (B1):** a custom Kestrel `IConnectionListenerFactory` backed by an
  `OpenZiti.NET` service binding, so inbound platform connections arrive over the overlay
  in-process (app-embedded zero trust, single process — matches `ziticorn`).
- **Documented fallback (B2):** a `ziti-edge-tunnel` sidecar exposes the service on
  localhost and Kestrel binds localhost. Used only for bring-up if B1 is blocked.

## Data flow

**Startup (platform):**
```
Host start
  → RegistrationHostedService
      build {externalId, version, meta} (+ channel:{} if no matching identity)
      POST /public/v1/integration/extensions/{extensionId}/instances  (Bearer extension key)
      persist channel.identity → identity file
  → Ziti transport binds Kestrel to the Ziti service using that identity
  → ready
```

**Inbound event/task:**
```
Ziti overlay → Kestrel (Ziti transport) → minimal-API endpoint
  authenticate JWT (parse claims, check exp)
  resolve account-scoped IMptApiClient (account token via IAccountTokenProvider)
  context factory: fetch Order/Agreement → build OrderContext/AgreementContext
  Tasks.StartAsync(taskId)            (task delivery only)
  run handler / pipeline
    Defer  → Tasks.RescheduleAsync
    Stop   → cancel
    Fail   → Tasks.FailAsync
    ok     → Tasks.CompleteAsync
  return response
```

## Error handling

- API client: typed `MptApiException` carrying status code + Marketplace error body;
  transient-retry policy (e.g. via `Microsoft.Extensions.Http.Resilience`) on idempotent
  reads and token minting.
- Hosting: handler exceptions map to HTTP responses for API routes and to task lifecycle
  outcomes for events; pipeline control-flow exceptions are first-class (not errors).
- Registration: fail fast with a clear message on non-2xx; never start the transport
  without an identity in platform mode.

## Testing strategy

- `ApiClient`: unit tests against a mocked `HttpMessageHandler` (request shape, auth header
  injection, pagination, token caching/refresh/leeway, error mapping). No network.
- `Hosting`: `WebApplicationFactory`-based tests on plain Kestrel — auth, context building,
  handler dispatch, pipeline control-flow → task lifecycle mapping, registration payload.
- `Ziti`: validated first by a **throwaway spike** (see Risks), then a thin integration
  smoke test; the transport seam lets all `Hosting` tests run without Ziti.

## Risks & open questions

1. **Ziti-bound Kestrel transport (highest risk).** Must confirm `OpenZiti.NET` exposes a
   `Stream`/socket-level server binding consumable by Kestrel's
   `IConnectionListenerFactory`, rather than only a higher-level HTTP helper. **Mitigation:**
   the first task in the implementation plan is a throwaway spike that stands up a Ziti
   service binding feeding Kestrel and serves one request end-to-end. The rest of the design
   assumes B1 but is gated on the spike; B2 (sidecar) is the fallback. The `Ziti` package
   boundary makes the choice swappable without touching `Hosting`.
2. **Native dependency / packaging.** `OpenZiti.NET` carries a native `ziti-sdk-c`
   component (`OpenZiti.NET.native`); confirm Linux container + Windows dev support and RID
   handling. Isolating it in one package limits blast radius.
3. **Identity format mapping.** The platform returns identity under a `mrok` key; confirm
   the exact JSON maps cleanly to what `OpenZiti.NET` loads (enrollment vs already-enrolled
   identity).
4. **`meta.yaml` schema fidelity.** Reproduce the Python `meta_config` output exactly so
   the platform accepts the registration payload; pin against a captured sample.
5. **JWT verification boundary.** Python decodes-without-verifying because the gateway
   verifies. Confirm the same trust boundary holds for the .NET service behind Ziti.

## Build sequence (high level — detailed plan follows)

1. Ziti+Kestrel transport spike (resolve Risk 1) — throwaway.
2. New repo + solution scaffold, CI, net8.0, NuGet metadata.
3. `Swo.Mpt.ApiClient`: models → auth/JWT → account-token provider → sub-clients →
   pagination → error handling, with tests.
4. `Swo.Mpt.Extensions.Hosting`: contexts → builder/authoring API → registration hosted
   service → event/API dispatch → pipeline engine → meta generation, on plain Kestrel,
   with tests.
5. `Swo.Mpt.Extensions.Ziti`: identity mapping → transport (B1, informed by the spike) →
   integration smoke test.
6. Sample/reference extension service + consumer docs.
