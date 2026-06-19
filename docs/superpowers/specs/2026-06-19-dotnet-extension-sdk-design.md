# Pure-.NET Extension SDK — Design

**Date:** 2026-06-19
**Status:** Draft for review (revised after discovering the existing bridge-based SDK and platform NuGet models)
**Authors:** MPT team (via Claude Code)

## Summary

The team is moving SoftwareONE Marketplace extension development to a **pure .NET**
implementation. A bridge-based .NET SDK already exists at `C:\repos\mpt-extension-dotnet-sdk`
(`Mpt.Extensions.Sdk`): it gives extension authors an attribute-driven model
(`[EventHandler]`, `[ApiEndpoint]`, `[Plug]`, `[ScheduleHandler]`), typed contexts, a
manifest source generator, and an `ExtensionHostBuilder` — but it delegates registration,
OpenZiti transport, `meta.yaml`, and Marketplace API calls to a **Python bridge sidecar**.

This design **removes the Python bridge** and reimplements its three responsibilities
natively in .NET, while keeping the existing C# authoring surface. It also adopts the
**platform domain models published on the PyraCloud NuGet feed**
(`Mpt.Models.Platform`, `Mpt.Models.Core`) instead of bespoke/generated models.

The result is a small set of libraries a C# service references to build an extension with
no Python in the container.

## Goals

- Keep the existing, good authoring model from `Mpt.Extensions.Sdk` (attributes, contexts,
  `EventResponse`, source-gen, `ExtensionHostBuilder`).
- Replace the Python bridge with native .NET:
  - **Registration + identity persistence** on startup.
  - **OpenZiti transport** so the host receives platform traffic over the overlay
    (`OpenZiti.NET`), replacing `mrok`/`ziticorn`.
  - **Direct, account-scoped Marketplace API access** (mint/cache/refresh account tokens,
    call the MPT API over Ziti), replacing the bridge `/__egress` proxy.
  - **Native `meta.yaml` generation** from the manifest, replacing the bridge's `meta.py`.
- Reuse platform NuGet domain models (`Mpt.Models.Platform` / `Mpt.Models.Core`).
- Preserve local development without Ziti (plain Kestrel), mirroring today's local mode.

## Non-Goals

- Rewriting the authoring model. The attribute/context/source-gen surface stays.
- Implementing `schedule` traffic end-to-end (routes exist but the platform doesn't drive
  them yet) or expanding `plug` beyond today's static-asset behaviour.
- A managed-code OpenZiti reimplementation. We wrap `OpenZiti.NET` (which wraps `ziti-sdk-c`).

## Decisions (made now; flag if any should change)

1. **Home: new separate repository** (working name `mpt-extension-sdk-dotnet`), per the
   earlier decision. The reusable parts of `C:\repos\mpt-extension-dotnet-sdk\src\Mpt.Extensions.Sdk`
   (attributes, contexts, dispatch, discovery, manifest, source-gen) are **lifted into the new
   repo**; the Python `bridge/` is dropped. *(If you'd rather evolve the existing repo in place
   and delete `bridge/`, say so — it's less lift-and-shift but mixes old/new history.)*
2. **Target framework: net10.0**, matching the existing `Mpt.Extensions.Sdk` and the
   `product-hub-extension` POC. *(This supersedes the earlier net8.0 choice, which was made
   before we knew the existing SDK and POC are net10.0. The platform models are net8.0 and
   are consumable from net10.0.)*
3. **Domain models: reuse `Mpt.Models.Platform` + `Mpt.Models.Core`** from the PyraCloud
   feed, per direction. See Risk 1 for the serialization-parity work this implies.

## Existing assets we keep (from `Mpt.Extensions.Sdk`)

Verified by reading the source:

- **Attributes** (`Attributes/`): `EventHandlerAttribute` (`Event`, `Condition`, task flag),
  `ApiEndpointAttribute`, `PlugAttribute`, `ScheduleHandlerAttribute`.
- **Contexts** (`Contexts/`): `IExtensionContext`, `EventContext` (carries `Event`,
  `AuthContext`, `IMarketplaceClient`, `ILogger`, `CancellationToken`), `ApiContext`,
  `OrderContext`, `ScheduleContext`, `HandlerServices`.
- **Events** (`Events/`): `Event`, `EventResponse` (`Ok` / `Delay(seconds)` / `Cancel(msg)`).
- **Discovery + source-gen** (`Discovery/`, `Generated/`, the `SourceGen` project):
  `GeneratedHandlerRegistry` (reflection-free) with a reflection fallback.
- **Manifest** (`Manifest/`): `ExtensionManifest`, `RouteDescriptor`, `RouteValidation`,
  `ManifestJson` — the `/__manifest` contract and route-collision checks.
- **Dispatch** (`Dispatch/`): `EventDispatcher`, `ApiDispatcher`, `ScheduleDispatcher`,
  `HandlerInvoker`.
- **Host endpoints** (`Hosting/ExtensionEndpoints.cs`): `/__health`, `/__manifest`, one route
  per event/API/schedule with a shared per-request pipeline.

## What the bridge did that we must absorb (verified)

The bridge sits between the platform and the C# host. Removing it means the SDK must take on:

1. **Registration** — `POST {SDK_EXTENSION_URL}/public/v1/integration/extensions/{extensionId}/instances`
   with `Authorization: Bearer {extensionApiKey}` and body
   `{externalId, version, meta, [channel:{}]}`; persist the returned `channel.identity`
   (keyed under `mrok`) to `SDK_IDENTITY_FILE_PATH`; include `channel:{}` only when there is
   no persisted identity matching the extension id. *(Confirmed against the POC bridge,
   tested on s1.show 2026-06-18.)*
2. **OpenZiti transport** — after registration, serve the host over the Ziti overlay using
   the persisted identity (today: `mrok.agent.ziticorn`).
3. **Ingress auth** — today the bridge parses auth and forwards it as an `X-Mpt-Auth` JSON
   header plus `X-Mpt-Egress-Session`, `x-request-id`, `mpt-task-id`. Natively, the host
   receives the platform's real request: it must **parse `Authorization: Bearer` and decode
   the SoftwareONE JWT claims itself** (replacing `ParseAuth`'s `X-Mpt-Auth` read), and drop
   the bridge-token gate.
4. **Egress** — today `IMarketplaceClient` POSTs `{Method, Path, Body, EgressSessionId}` to
   the bridge `/__egress`, which resolves the account-scoped token and calls the MPT API.
   Natively, a new `IMarketplaceClient` implementation must **call the MPT API directly over
   Ziti and mint/cache/refresh the per-account token itself**.

## meta.yaml (ground truth from the POC)

The registration `meta` block (the basis for `meta.yaml`):

```json
{
  "contractVersion": "1",
  "events": [
    {
      "event": "platform.catalog.productItem.created",
      "path": "/events/platform-catalog-productitem-created",
      "condition": "eq(product.id,PRD-7811-7846)",
      "task": false
    }
  ],
  "apiEndpoints": [],
  "schedules": [],
  "plugs": []
}
```

It is **generated**, not authored: today the bridge calls the host's `GET /__manifest` and
converts it. Natively, the SDK generates `meta.yaml` directly from `ExtensionManifest` before
registration — no host round-trip needed.

## Package architecture

Three packages, isolating the native Ziti dependency:

```
Swo.Mpt.Extensions.Abstractions   (the authoring surface; lifted from Mpt.Extensions.Sdk)
        ▲
        │
Swo.Mpt.Extensions.Hosting        (ASP.NET Core host: endpoints, real-JWT auth, registration,
        ▲                          direct MptApiClient, meta.yaml gen)
        │
Swo.Mpt.Extensions.Ziti           (OpenZiti transport; depends on Hosting + OpenZiti.NET)
```

> Naming TBD — could keep the `Mpt.Extensions.Sdk*` family from the existing repo. The split
> matters more than the names.

### `Swo.Mpt.Extensions.Abstractions`

The current `Mpt.Extensions.Sdk` authoring code, lifted with minimal change: attributes,
`IExtensionContext`/`EventContext`/`ApiContext`/`OrderContext`/`ScheduleContext`, `Event`,
`EventResponse`, `IMarketplaceClient`, manifest types, dispatch, discovery, source-gen.
`AuthContext` is enriched to carry the decoded SoftwareONE claims (accountId, accountType,
extensionId, modules) since the host now decodes the JWT itself.

### `Swo.Mpt.Extensions.Hosting` (the bulk of the new work)

ASP.NET Core integration; depends on `Abstractions` + the platform model packages.

- **`ExtensionHostBuilder.Build(builder)`** — unchanged authoring entrypoint; rewires the
  per-request pipeline to native auth + native Marketplace client and registers the hosted
  services below.
- **Ingress auth**: a `SoftwareOneJwt` claims parser + request authenticator replaces the
  `X-Mpt-Auth` path — extract `Authorization: Bearer`, decode (not verify; the gateway
  verifies) claims `https://claims.softwareone.com/{accountId,accountType,extensionId,modules}`,
  check `exp` with leeway, build `AuthContext`. Bridge-token gate removed.
- **`IMptApiClient` + account tokens**: a direct MPT API client (typed `HttpClient` via
  `IHttpClientFactory`) that injects a fresh **account-scoped token** per request. An
  `IAccountTokenProvider` mints tokens via
  `POST /public/v1/integration/installations/token?account.id={id}` using the extension key,
  caches per account, and refreshes within a leeway window (serialized per account). This is
  the native replacement for the bridge's egress + token resolver. The existing
  `IMarketplaceClient` (generic `GetAsync<T>/PostAsync<T>/PutAsync<T>`) is reimplemented on
  top of it, so handler code is unchanged.
- **Registration hosted service**: on startup (platform mode) build the payload, POST
  instances, persist identity, then signal the transport. Fail fast on non-2xx; never start
  the Ziti transport without an identity.
- **`meta.yaml` generation**: serialize `ExtensionManifest` to the `meta` schema above before
  registration.
- **Config**: typed options bound from the same env vars the bridge used —
  `SDK_EXTENSION_ID`, `SDK_EXTENSION_API_KEY`, `SDK_EXTENSION_URL`, `MPT_API_BASE_URL`,
  `SDK_EXTENSION_EXTERNAL_ID`, `SDK_IDENTITY_FILE_PATH`, plus a local/platform mode switch.

### `Swo.Mpt.Extensions.Ziti`

Isolated `OpenZiti.NET` dependency.

- Maps the persisted `channel.identity` (the `mrok`-keyed JSON) to an OpenZiti identity.
- **Target (B1):** a custom Kestrel `IConnectionListenerFactory` backed by an `OpenZiti.NET`
  service binding, so inbound platform connections arrive over the overlay in-process —
  app-embedded zero trust, single process, matching `ziticorn`. Enabled via
  `builder.UseZitiTransport()`.
- **Fallback (B2):** a `ziti-edge-tunnel` sidecar exposing the service on localhost, Kestrel
  binds localhost. Bring-up only.
- Outbound (`IMptApiClient`) also dials the MPT API over the same Ziti context.

## Data flow

**Startup (platform):**
```
Host start
  → generate meta.yaml from ExtensionManifest
  → RegistrationHostedService: POST instances (Bearer extension key) → persist channel.identity
  → Ziti transport binds Kestrel to the Ziti service using that identity
  → ready
```

**Inbound event/task (no bridge):**
```
Ziti overlay → Kestrel (Ziti transport) → mapped route (e.g. /events/...)
  parse Authorization: Bearer → decode SWO claims → AuthContext
  build HandlerServices { DI scope, IMarketplaceClient(account-scoped), logger }
  dispatch to [EventHandler] → returns EventResponse (Ok/Delay/Cancel)
  → JSON response to platform
```

**Egress (handler → Marketplace, no bridge):**
```
ctx.Marketplace.GetAsync<OrderEntity>("/commerce/orders/ORD-...")
  → IMptApiClient: ensure fresh account token (IAccountTokenProvider) → HTTP over Ziti
  → MPT API → deserialize into platform model
```

## Error handling

- Marketplace client: typed exception with status + body; transient retry on idempotent
  reads and token minting (`Microsoft.Extensions.Http.Resilience`).
- Event handlers: existing `EventResponse` model (`Delay` → platform retry, `Cancel` → stop);
  unhandled exceptions return a structured 500 (platform retries), preserving today's
  semantics now that the host owns the response.
- Registration: fail fast and do not start the transport without an identity.

## Testing strategy

- Authoring/dispatch: keep the existing unit tests from `Mpt.Extensions.Sdk` (host endpoints,
  dispatch, discovery, manifest, route validation) on plain Kestrel via `WebApplicationFactory`.
- Auth: JWT claims parsing, expiry leeway, account scoping.
- Marketplace client: mocked `HttpMessageHandler` — request shape, token injection,
  caching/refresh, error mapping, and **platform-model (de)serialization parity** (see Risk 1).
- Registration: payload shape + identity persistence/reuse, asserted against the captured POC
  payload.
- Ziti: validated by a **throwaway spike first** (Risk 2), then a thin integration smoke test.

## Risks & open questions

1. **Platform models vs public-API JSON (decided to reuse models; this is the cost).**
   `Mpt.Models.Platform` types are server-side RQL entities: PascalCase, `null!` non-nullable
   defaults, and `Status`-style fields are `Enumeration` objects (`{Name, Id, AlternateNames}`),
   not JSON strings. The public API JSON is camelCase, string-valued, and RQL-projected
   (partial). The platform serializes responses through an RQL serializer + custom converters
   (`Presentation.WebApi/Startup.cs`). So deserializing API responses into these models needs
   client-side parity: a camelCase policy, an `Enumeration`-from-string `JsonConverterFactory`,
   optional/omitted-field tolerance, and care with `null!` properties when RQL omits fields.
   **Mitigation:** an early task builds and unit-tests an `MptJson` options set against captured
   real responses for the core resources (Order, Agreement, Subscription, Asset, ProductItem);
   if parity proves expensive for a given resource, fall back to a thin API-shaped DTO for that
   resource only. The generic `IMarketplaceClient.GetAsync<T>` means this is per-resource, not
   all-or-nothing.
2. **Ziti-bound Kestrel transport (highest delivery risk).** Confirm `OpenZiti.NET` exposes a
   `Stream`/socket-level server binding consumable by Kestrel's `IConnectionListenerFactory`
   (vs. only a higher-level HTTP helper). **Mitigation:** throwaway spike as the first task;
   B2 sidecar fallback; the `Ziti` package boundary makes the choice swappable.
3. **Native dependency / packaging.** `OpenZiti.NET` carries a native `ziti-sdk-c` component;
   confirm Linux-container + Windows-dev RID handling. Isolated in one package.
4. **Identity format mapping.** Confirm the platform's `channel.identity` (`mrok`-keyed) maps
   cleanly to what `OpenZiti.NET` loads (already-enrolled identity vs enrollment JWT).
5. **Repo strategy + history.** New repo (lift the reusable code) vs evolve the existing repo
   (delete `bridge/`). Decision 1 above; confirm.
6. **Auth verification boundary.** The bridge/gateway verified the JWT; confirm the same trust
   boundary holds when the .NET host terminates Ziti directly (decode-not-verify stays valid).

## Build sequence (high level — detailed plan follows)

1. Ziti + Kestrel transport spike (resolve Risk 2) — throwaway.
2. New repo + solution scaffold, net10.0, PyraCloud feed (`nuget.config`), CI, NuGet metadata.
3. Lift `Mpt.Extensions.Sdk` authoring code into `Swo.Mpt.Extensions.Abstractions`; keep its tests green.
4. `Swo.Mpt.Extensions.Hosting`: native JWT auth → account-token provider + `IMptApiClient`
   (with platform-model serialization parity, Risk 1) → reimplement `IMarketplaceClient` on it
   → registration hosted service → `meta.yaml` generation. Plain Kestrel; tests.
5. `Swo.Mpt.Extensions.Ziti`: identity mapping → transport (B1, informed by the spike) →
   integration smoke test.
6. Port `product-hub-extension` to the pure-.NET SDK as the reference/acceptance check (drop
   the bridge, confirm parity against s1.show).
