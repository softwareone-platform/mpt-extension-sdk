# Pure-.NET Extension SDK — Plan 3: Migrate product-hub-extension onto the SDK

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Migrate the real `C:\repos\product-hub-extension` POC off the Python-bridge SDK onto the pure-.NET SDK (`Mpt.Extensions.Sdk` + `Mpt.Extensions.Sdk.Ziti`), proving the SDK works for a real extension (the acceptance check).

**Architecture:** The new SDK preserved the authoring API, so the handler + tests need (essentially) no code change. Work = packaging and deployment wiring: pack the SDK into the POC's local feed, swap package references (drop the obsolete `Mpt.Extensions.Sdk.Marketplace`; the POC already supplies its own `ProductItem`/`ExternalIds`), add the public feeds the Ziti package's `OpenZiti.NET` dependency needs, add the `UseZiti()` platform opt-in, and replace the Python-bridge Docker/compose with a pure-.NET container.

**Tech Stack:** .NET (POC stays net10.0; references net8.0 SDK packages — forward-compatible), the SDK packed as local NuGet, xUnit.

**Working dirs:** `$POC` = `C:\repos\product-hub-extension` (the target; **not currently a git repo**). `$SDK` = `C:\repos\mpt-extension-sdk-dotnet` (source of the packages; 80 tests green; pinned net8 SDK).

**Ground truth captured (do not re-derive):**
- `$POC/ProductHubExtension.csproj`: net10.0; refs `Mpt.Extensions.Sdk 0.1.0-*` + `Mpt.Extensions.Sdk.Marketplace 0.1.0-*`; `DefaultItemExcludes` keeps `ProductHubExtension.Tests/**;.packages/**;identity/**` out.
- `$POC/nuget.config`: ONLY a `local-sdk` source (`./.packages`); nuget.org intentionally omitted.
- `$POC/Program.cs`: configures ProductHub DI, then `var app = ExtensionHostBuilder.Build(builder); app.Run();`.
- `$POC/Handlers/ProductItemCreatedHandler.cs`: `[EventHandler(Event="platform.catalog.productItem.created", Condition="eq(product.id,PRD-7811-7846)")]`, uses `ctx.Marketplace.GetAsync<ProductItem>` / `PutAsync<ProductItem>` and returns `EventResponse.Ok/Delay`.
- `$POC/Models/ProductItem.cs`: own `ProductItem` + `ExternalIds` (model-agnostic — keep).
- `$POC/ProductHubExtension.Tests/*`: handler tests use `new HandlerServices(IServiceProvider, IMarketplaceClient, ILogger)`, `new EventContext(evt, new AuthContext(), services, default)`, `MarketplaceApiException(int,string)` — all match the new SDK's public API. Should pass unchanged.
- New SDK package version: `0.1.0-alpha.1` (from `$SDK/Directory.Build.props`) — matches the POC's `0.1.0-*` wildcard.
- `$POC/Dockerfile`: builds on the bridge base image (`ghcr.io/softwareone-platform/mpt-extension-dotnet-sdk:latest`, Python bridge + .NET) and sets `BRIDGE_CSHARP_CMD`. `$POC/docker-compose.yaml` + `docker-compose.platform.yaml`: bridge-based.

---

## Task 1: Safety net + reference the new SDK packages, build + tests green

This is the acceptance check: by the end, the POC builds and its tests pass against the pure-.NET SDK.

- [ ] **Step 1: Initialise git in the POC as a safety net (it is not under version control)**

```bash
cd 'C:/repos/product-hub-extension'
git init -b main
git add -A
git commit -m "chore: baseline before pure-.NET SDK migration"
```
(If `git init` reports it is already a repo, skip — just commit a baseline.)

- [ ] **Step 2: Pack the new SDK into the POC's local feed**

Pack the two packable SDK projects (Release) straight into the POC's `./.packages`:
```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet pack Mpt.Extensions.Sdk.sln -c Release -o 'C:/repos/product-hub-extension/.packages'
```
Expected: produces `Mpt.Extensions.Sdk.0.1.0-alpha.1.nupkg` and `Mpt.Extensions.Sdk.Ziti.0.1.0-alpha.1.nupkg` in `$POC/.packages`. (The SourceGen project is bundled as the analyzer inside `Mpt.Extensions.Sdk` via its `EnsureAnalyzerBundled` target; pack builds it first. Test/sample projects are `IsPackable=false` and are not packed.) If pack fails on the analyzer-bundled check, run `dotnet build Mpt.Extensions.Sdk.sln -c Release` first, then re-run pack.

Then remove any stale old packages from the POC feed so the wildcard resolves the fresh ones:
```bash
cd 'C:/repos/product-hub-extension/.packages'
ls *.nupkg
# delete any Mpt.Extensions.Sdk.Marketplace*.nupkg and any older Mpt.Extensions.Sdk*/Ziti* versions if present
rm -f Mpt.Extensions.Sdk.Marketplace*.nupkg
```

- [ ] **Step 3: Add the public feeds the Ziti package needs**

`Mpt.Extensions.Sdk.Ziti` depends on `OpenZiti.NET`, which is NOT in the local feed. Overwrite `$POC/nuget.config` to add nuget.org + PyraCloud while keeping the local feed (this environment can reach both — the SDK itself restored `OpenZiti.NET` here):
```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="local-sdk" value="./.packages" />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
    <add key="PyraCloud" value="https://pkgs.dev.azure.com/softwareone-pc/_packaging/PyraCloud/nuget/v3/index.json" />
  </packageSources>
</configuration>
```

- [ ] **Step 4: Swap package references in the POC csproj**

Edit `$POC/ProductHubExtension.csproj` ItemGroup: REMOVE the `Mpt.Extensions.Sdk.Marketplace` reference (the POC uses its own `ProductItem`/`ExternalIds`), KEEP `Mpt.Extensions.Sdk`, ADD `Mpt.Extensions.Sdk.Ziti`:
```xml
  <ItemGroup>
    <PackageReference Include="Mpt.Extensions.Sdk" Version="0.1.0-*" />
    <PackageReference Include="Mpt.Extensions.Sdk.Ziti" Version="0.1.0-*" />
  </ItemGroup>
```
Leave `TargetFramework` net10.0 and the `DefaultItemExcludes` line unchanged.

- [ ] **Step 5: Restore + build + test the POC against the new SDK**

```bash
cd 'C:/repos/product-hub-extension'
dotnet test ProductHubExtension.Tests/ProductHubExtension.Tests.csproj
```
Expected: restore pulls the new SDK from `local-sdk` and `OpenZiti.NET` from nuget.org/PyraCloud; the handler compiles unchanged; **all handler tests pass** (they target the new SDK's public API). 
- If the source generator (bundled in the `Mpt.Extensions.Sdk` package) does not run when consumed as a package (e.g. handler not discovered), confirm the analyzer is present under `analyzers/dotnet/cs` in the nupkg and that the package reference brings it in; the reflection fallback should still let tests pass (they construct handlers directly). The handler *discovery* is verified at runtime in Task 3's smoke.
- If any compile error surfaces from an SDK API mismatch, fix the POC call site minimally to the new SDK API and note it. (None expected — the test file already matches.)

- [ ] **Step 6: Commit**

```bash
cd 'C:/repos/product-hub-extension'
git add -A
git commit -m "feat: migrate to pure-.NET SDK packages (drop Marketplace pkg, add Ziti)"
```

## Task 2: Native host wiring + remove the Python bridge

- [ ] **Step 1: Add the Ziti platform opt-in to Program.cs**

Edit `$POC/Program.cs` to serve over Ziti in platform mode and plain Kestrel locally, keeping all ProductHub DI. Add `using Mpt.Extensions.Sdk.Ziti;` and the mode switch BEFORE `ExtensionHostBuilder.Build`:
```csharp
using Microsoft.Extensions.DependencyInjection;
using Mpt.Extensions.Sdk.Hosting;
using Mpt.Extensions.Sdk.Ziti;
using ProductHubExtension.ProductHub;

var builder = WebApplication.CreateBuilder(args);

// ProductHub integration (unchanged).
builder.Services.Configure<ProductHubOptions>(
    builder.Configuration.GetSection(ProductHubOptions.Section));
builder.Services.AddHttpClient();
builder.Services.AddSingleton<ProductHubTokenProvider>();
builder.Services.AddHttpClient<IProductHubClient, ProductHubClient>();

// Platform mode serves over the OpenZiti overlay using the persisted identity (registration
// runs first). Anything else runs locally on plain Kestrel and skips registration.
if (string.Equals(builder.Configuration["SDK_MODE"], "platform", StringComparison.OrdinalIgnoreCase))
    builder.UseZiti();
else
    builder.Configuration["SDK_MODE"] = "local";

var app = ExtensionHostBuilder.Build(builder);
app.Run();
```
(Preserve the exact ProductHub registrations already present in the file — read it first and keep them verbatim; only add the `using` + the mode switch.)

- [ ] **Step 2: Replace the bridge Dockerfile with a pure-.NET image**

Overwrite `$POC/Dockerfile` (no Python bridge; ASP.NET Core runtime base; the `OpenZiti.NET.native` linux-x64 asset ships with the published app):
```dockerfile
# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish ProductHubExtension.csproj -c Release -o /app

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /app .
# Platform mode: set SDK_MODE=platform, SDK_EXTENSION_ID, SDK_EXTENSION_API_KEY,
# SDK_EXTENSION_URL, MPT_API_BASE_URL, SDK_IDENTITY_FILE_PATH (see the SDK docs).
ENTRYPOINT ["dotnet", "ProductHubExtension.dll"]
```
(If publishing the Ziti native asset for linux-x64 needs a RID, the runtime base + framework-dependent publish should still carry `OpenZiti.NET.native`'s `runtimes/linux-x64/native` payload; if a smoke later shows the native lib missing, add `-r linux-x64 --self-contained false` to the publish. Leave as-is for now.)

- [ ] **Step 3: Remove the bridge compose files**

```bash
cd 'C:/repos/product-hub-extension'
git rm docker-compose.yaml docker-compose.platform.yaml
```
(They orchestrated the Python bridge sidecar, which no longer exists. If the team wants a local compose, it can be a single-service file later — out of scope here.)

- [ ] **Step 4: Build the publishable app to confirm the container build will succeed**

```bash
cd 'C:/repos/product-hub-extension'
dotnet publish ProductHubExtension.csproj -c Release -o ./bin/publish-check
```
Expected: publish succeeds; `./bin/publish-check` contains `ProductHubExtension.dll` and (under `runtimes/`) the OpenZiti native assets. Then delete the check dir (`rm -rf ./bin/publish-check`) — it's a verification only.

- [ ] **Step 5: Commit**

```bash
cd 'C:/repos/product-hub-extension'
git add -A
git commit -m "feat: pure-.NET host (UseZiti platform opt-in) + drop Python bridge Docker/compose"
```

## Task 3: Local smoke (handler discovery end-to-end)

- [ ] **Step 1: Run the migrated extension locally and confirm discovery + endpoints**

```bash
cd 'C:/repos/product-hub-extension'
dotnet run --project ProductHubExtension.csproj --urls http://127.0.0.1:8902 > /tmp/poc.log 2>&1 &
APP_PID=$!
for i in $(seq 1 25); do sleep 1; if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8902/__health | grep -q 200; then break; fi; done
echo "=== HEALTH ==="; curl -s http://127.0.0.1:8902/__health; echo
echo "=== MANIFEST ==="; curl -s http://127.0.0.1:8902/__manifest; echo
kill $APP_PID 2>/dev/null
```
Expected: `/__health` → `{"status":"ok"}`; `/__manifest` lists the event `platform.catalog.productItem.created` at its path with `condition` `eq(product.id,PRD-7811-7846)` — proving the **bundled source generator discovered the POC's handler from the packaged SDK**. (Default mode is local; no Ziti bind, no registration network call.) Ensure no leftover process holds the port (kill the child; on Windows `taskkill` the `ProductHubExtension` process if needed). If the manifest shows the event, the acceptance check passes.

- [ ] **Step 2: Record the outcome**

If `/__manifest` did NOT list the handler (source generator didn't run from the package), note it as a finding: the reflection fallback would still serve it at runtime, but investigate whether the analyzer is correctly bundled/consumed from the nupkg. Do not silently pass.

- [ ] **Step 3: Final commit (if anything changed during smoke, e.g. a `.gitignore` for bin/)**

Add a `$POC/.gitignore` if absent (ignore `bin/`, `obj/`, `.packages/`, `identity/`), then:
```bash
cd 'C:/repos/product-hub-extension'
git add -A
git commit -m "chore: gitignore + local smoke verified"
```

---

## Self-review notes

- **Acceptance check = Task 1 Step 5** (POC tests pass against the new SDK) **+ Task 3** (handler discovered + served by the packaged SDK at runtime). Together they prove the pure-.NET SDK is a drop-in for a real extension.
- **No handler/test code changes expected** — the new SDK preserved the authoring API (verified against the POC's test file). Any required change is a finding to report, not a silent edit.
- **Bridge fully removed:** Dockerfile rewritten, both compose files deleted, `Mpt.Extensions.Sdk.Marketplace` dropped. The POC keeps its own `ProductItem` model (model-agnostic SDK).
- **Feeds:** the POC's nuget.config gains nuget.org + PyraCloud (needed for `OpenZiti.NET`); this environment reaches both.
- **Safety:** the POC wasn't under version control; Task 1 Step 1 initialises git + a baseline commit so the in-place migration is reversible.
- **Live Ziti** is still only validatable in a real platform environment (the deployment smoke from Plan 2) — out of scope for this local acceptance check.
