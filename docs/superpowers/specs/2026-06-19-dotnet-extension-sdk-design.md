# Pure-.NET Extension SDK — Design

**Date:** 2026-06-19
**Status:** Draft for review
**Authors:** MPT team (via Claude Code)

## Summary

The team is moving SoftwareONE Marketplace extension development to a **pure .NET**
implementation. A bridge-based .NET SDK already exists in the work directory
`C:\repos\mpt-extension-sdk-dotnet` (`Mpt.Extensions.Sdk`): it gives extension authors an
attribute-driven model (`[EventHandler]`, `[ApiEndpoint]`, `[Plug]`, `[ScheduleHandler]`),
typed contexts, a manifest source generator, and an `ExtensionHostBuilder` — but it delegates
registration, OpenZiti transport, `meta.yaml`, and Marketplace API calls to a **Python bridge
sidecar**.

This design **removes the Python bridge** and reimplements its responsibilities natively in
.NET, while keeping the existing C# authoring surface. The SDK stays **model-agnostic**: it
ships no Marketplace domain models. The concrete extension chooses its own model types (the
platform NuGet contracts, hand-written DTOs, or anything else) and passes them to the generic
Marketplace client.

The result is a small set of libraries a C# service references to build an extension with no
Python in the container.

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
- Keep the SDK **generic / model-agnostic** — no dependency on any Marketplace model package.
  Provide a configurable serialization hook so an extension can deserialize into whatever model
  types it uses.
- Preserve local development without Ziti (plain Kestrel), mirroring today's local mode.

## Non-Goals

- Rewriting the authoring model. The attribute/context/source-gen surface stays.
- Shipping Marketplace domain models in the SDK. Models are the **extension's** choice.
- Implementing `schedule` traffic end-to-end (routes exist but the platform doesn't drive
  them yet) or expanding `plug` beyond today's static-asset behaviour.
- A managed-code OpenZiti reimplementation. We wrap `OpenZiti.NET` (which wraps `ziti-sdk-c`).

## Decisions (made now; flag if any should change)

1. **Home: `C:\repos\mpt-extension-sdk-dotnet`** — evolve this directory in place. It already
   contains the bridge-based SDK (`src/Mpt.Extensions.Sdk`, `bridge/`, `codegen`, `tests`,
   `tools`). The work: **keep the C# authoring SDK, drop the Python `bridge/`**, and add native
   registration/Ziti/egress. The separate GitHub-linked repo `C:\repos\mpt-extension-dotnet-sdk`
   is left untouched.
   - **Open item:** this directory has **no git remote**. A remote must be wired up before
     publishing/CI.
2. **Target framework: net8.0 (LTS).** The existing `Mpt.Extensions.Sdk` and the
   `product-hub-extension` POC are currently net10.0, so retargeting down to net8.0 may need
   minor fixes (a plan task). net8.0 is the broad-compatibility LTS target for consuming
   services.
3. **Models: the SDK is model-agnostic.** It depends on **no** Marketplace model package. The
   Marketplace client is generic (`GetAsync<T>/PostAsync<T>/PutAsync<T>`), and the consuming
   extension supplies `T` — e.g. the platform NuGet contracts (`Mpt.Models.Platform`) or its own
   DTOs. The SDK exposes a **configurable `JsonSerializerOptions`** so the extension can register
   whatever converters its chosen models need (for platform contracts, e.g. a string↔`Enumeration`
   converter). The SDK's own wire types (event envelope, auth claims, registration payload,
   manifest) remain SDK-owned and need no external models.

## Existing assets we keep (from `Mpt.Extensions.Sdk`)

Verified by reading the source — all already model-agnostic:

- **Attributes** (`Attributes/`): `EventHandlerAttribute` (`Event`, `Condition`, task flag),
  `ApiEndpointAttribute`, `PlugAttribute`, `ScheduleHandlerAttribute`.
- **Contexts** (`Contexts/`): `IExtensionContext`, `EventContext` (carries `Event`,
  `AuthContext`, `IMarketplaceClient`, `ILogger`, `CancellationToken`), `ApiContext`,
  `OrderContext` (exposes only `OrderId` — a string), `ScheduleContext`, `HandlerServices`.
- **Events** (`Events/`): `Event`/`EventObject`/`EventDetails`/`EventTask` (generic envelope,
  ids + `objectType` string), `EventResponse` (`Ok` / `Delay(seconds)` / `Cancel(msg)`).
- **Marketplace** (`Marketplace/`): generic `IMarketplaceClient`, `MarketplaceApiException`.
- **Discovery + source-gen** (`Discovery/`, `Generated/`, the `SourceGen` project):
  `GeneratedHandlerRegistry` (reflection-free) with a reflection fallback.
- **Manifest** (`Manifest/`): `ExtensionManifest`, `RouteDescriptor`, `RouteValidation`,
  `ManifestJson` — the `/__manifest` contract and route-collision checks.
- **Dispatch** (`Dispatch/`): `EventDispatcher`, `ApiDispatcher`, `ScheduleDispatcher`,
  `HandlerInvoker`.
- **Host endpoints** (`Hosting/ExtensionEndpoints.cs`): `/__health`, `/__manifest`, one route
  per event/API/schedule with a shared per-request pipeline.

## What the bridge did that we must absorb (verified)

Removing the Python bridge means the SDK must take on:

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
   Ziti and mint/cache/refresh the per-account token itself**, deserializing into the caller's
   `T` with the configurable options.

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

Three packages, isolating the native Ziti dependency. **None of them depend on any Marketplace
model package** — models stay on the extension side.

```
Swo.Mpt.Extensions.Abstractions   (authoring surface; lifted from Mpt.Extensions.Sdk)
        ▲
        │
Swo.Mpt.Extensions.Hosting        (ASP.NET Core host: endpoints, real-JWT auth, registration,
        ▲                          generic account-scoped Marketplace client, meta.yaml gen)
        │
Swo.Mpt.Extensions.Ziti           (OpenZiti transport; depends on Hosting + OpenZiti.NET)
```

> Naming TBD — could keep the `Mpt.Extensions.Sdk*` family from the existing repo. The split
> matters more than the names.

### `Swo.Mpt.Extensions.Abstractions`

The current `Mpt.Extensions.Sdk` authoring code, lifted with minimal change: attributes,
contexts, `Event`, `EventResponse`, generic `IMarketplaceClient`, manifest types, dispatch,
discovery, source-gen. `AuthContext` is enriched to carry the decoded SoftwareONE claims
(accountId, accountType, extensionId, modules) since the host now decodes the JWT itself.

### `Swo.Mpt.Extensions.Hosting` (the bulk of the new work)

ASP.NET Core integration; depends only on `Abstractions` (no model packages).

- **`ExtensionHostBuilder.Build(builder)`** — unchanged authoring entrypoint; rewires the
  per-request pipeline to native auth + native Marketplace client and registers the hosted
  services below.
- **Ingress auth**: a `SoftwareOneJwt` claims parser + request authenticator replaces the
  `X-Mpt-Auth` path — extract `Authorization: Bearer`, decode (not verify; the gateway
  verifies) claims `https://claims.softwareone.com/{accountId,accountType,extensionId,modules}`,
  check `exp` with leeway, build `AuthContext`. Bridge-token gate removed.
- **Generic Marketplace client + account tokens**: a direct MPT API client (typed `HttpClient`
  via `IHttpClientFactory`) that injects a fresh **account-scoped token** per request. An
  `IAccountTokenProvider` mints tokens via
  `POST /public/v1/integration/installations/token?account.id={id}` using the extension key,
  caches per account, and refreshes within a leeway window (serialized per account). The existing
  generic `IMarketplaceClient` (`GetAsync<T>/PostAsync<T>/PutAsync<T>`) is reimplemented on top
  of it, so handler code is unchanged. Deserialization uses an **injectable `JsonSerializerOptions`**
  (default: camelCase, case-insensitive); an extension using platform contracts registers any
  needed converters (e.g. `Enumeration`) there.
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
- Outbound (the Marketplace client) also dials the MPT API over the same Ziti context.

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
ctx.Marketplace.GetAsync<TOrder>("/commerce/orders/ORD-...")   // TOrder is the EXTENSION's type
  → IMptApiClient: ensure fresh account token (IAccountTokenProvider) → HTTP over Ziti
  → MPT API → deserialize into TOrder using the configured JsonSerializerOptions
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
  caching/refresh, error mapping, and correct deserialization into a caller-supplied `T` with a
  custom converter (proving the serialization hook).
- Registration: payload shape + identity persistence/reuse, asserted against the captured POC
  payload.
- Ziti: validated by a **throwaway spike first** (Risk 1), then a thin integration smoke test.

## Risks & open questions

1. **Ziti-bound Kestrel transport — RESOLVED (spike, 2026-06-19).** `OpenZiti.NET`
   `1.0.26159.2780` targets **net8.0** with **linux-x64/win-x64** natives, and the repo ships a
   reference **`ZitiConnectionListenerFactory : IConnectionListenerFactory`** + a
   `UseZitiTransport(identity, service)` host extension. An accepted `ZitiSocket` converts to a
   real `System.Net.Sockets.Socket`, fed to Kestrel's own `SocketConnectionContextFactory` — no
   hand-rolled `IDuplexPipe`. **Decision: B1 (app-embedded), adapting the upstream sample.** B2
   (sidecar) dropped. The accept API is synchronous, bridged to Kestrel via a background
   accept-loop + `Channel` (as in the sample).
2. **Native dependency / packaging.** `OpenZiti.NET` carries a native `ziti-sdk-c` component;
   confirm Linux-container + Windows-dev RID handling, and net8.0 compatibility of the package.
   Isolated in one package.
3. **Identity format mapping — RESOLVED (inspected a real POC identity, 2026-06-19).** The
   persisted `channel.identity` IS a standard **enrolled** OpenZiti identity JSON
   (`ztAPI`, `id.{key,cert,ca}` PEM, `enableHa`) plus an extra non-ziti **`mrok`** metadata key
   (`extension`/`instance`/`domain`/`tags`). So: no enrollment-JWT flow; just write the JSON to a
   file (optionally strip `mrok`) and load by path. **Open:** confirm the **bind service name**
   with the platform team — the identity carries `mrok.tags.mrok-service` = the extension id
   (e.g. `ext-5034-5001`), which is the likely service to bind.
4. **net10 → net8 retarget.** The existing SDK/POC are net10.0; retargeting may surface
   net10-only API usage to fix. Expected small.
5. **Auth verification boundary.** The bridge/gateway verified the JWT; confirm the same trust
   boundary holds when the .NET host terminates Ziti directly (decode-not-verify stays valid).
6. **Serialization ergonomics (extension-side, not SDK).** Extensions that use the platform
   contracts need a string↔`Enumeration` converter + camelCase. Not an SDK dependency, but we
   should document the recommended options and consider an **optional** tiny helper package
   (e.g. `Swo.Mpt.Extensions.Contracts`) that ships those converters for convenience. YAGNI for
   the first cut.

## Build sequence (high level — detailed plan follows)

1. Ziti + Kestrel transport spike (resolve Risk 1) — throwaway.
2. In `C:\repos\mpt-extension-sdk-dotnet`: retarget to net8.0, then remove the Python `bridge/`
   and its build wiring; keep the C# solution building.
3. Restructure the existing `Mpt.Extensions.Sdk` into the package split (Abstractions / Hosting /
   Ziti); keep its existing tests green throughout.
4. `Swo.Mpt.Extensions.Hosting`: native JWT auth → account-token provider + account-scoped
   Marketplace client (generic, injectable serializer options) → reimplement `IMarketplaceClient`
   on it → registration hosted service → `meta.yaml` generation. Plain Kestrel; tests.
5. `Swo.Mpt.Extensions.Ziti`: identity mapping → transport (B1, informed by the spike) →
   integration smoke test.
6. Port `product-hub-extension` to the pure-.NET SDK as the reference/acceptance check (drop
   the bridge, supply its own models, confirm parity against s1.show).
