# Pure-.NET Extension SDK — Plan 2: OpenZiti Transport

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add a `Mpt.Extensions.Sdk.Ziti` library that serves the extension host over the OpenZiti overlay using the persisted platform identity — the .NET equivalent of the Python `ziticorn` — so platform-mode extensions receive events/API calls over Ziti instead of plain TCP.

**Architecture:** Isolate the native `OpenZiti.NET` dependency in its own package. Adapt the upstream reference `ZitiConnectionListenerFactory` (a Kestrel `IConnectionListenerFactory`) + `UseZitiTransport` from the openziti/ziti-sdk-csharp `OpenZiti.NET.Samples/src/Kestrel` sample. Map the persisted `channel.identity` to a ziti-loadable identity file and bind the extension's service. Keep local mode on plain Kestrel; opt into Ziti only in platform mode.

**Tech Stack:** .NET 8, `OpenZiti.NET` `1.0.26159.2780` (+ `OpenZiti.NET.native`), ASP.NET Core Kestrel transport abstractions (`Microsoft.AspNetCore.Connections`), `SocketConnectionContextFactory`.

**Pre-resolved by the Plan 2 spike (2026-06-19):**
- B1 (app-embedded) is the chosen approach; the upstream sample already implements the hard part (accepted `ZitiSocket` → real `Socket` → `SocketConnectionContextFactory.Create` → Kestrel `ConnectionContext`). Sample dir: https://github.com/openziti/ziti-sdk-csharp/tree/main/OpenZiti.NET.Samples/src/Kestrel
- `channel.identity` is a standard **enrolled** ziti identity JSON (`ztAPI`, `id.{key,cert,ca}`, `enableHa`) + an extra non-ziti `mrok` key. No enrollment flow needed.
- Key APIs: `new ZitiContext(string identityFile)`; `API.Bind/Listen/Accept`; `ZitiSocket.ToSocket()`; host extension `UseZitiTransport(identity, service)`.

**Working directory:** `C:\repos\mpt-extension-sdk-dotnet` (`$DST`). Source-of-truth for the SDK sample to adapt: the openziti GitHub repo (fetch raw files). 69 tests currently pass; solution `Mpt.Extensions.Sdk.sln`.

**Bind service name — RESOLVED from the Python `mrok` source (v0.9.7, `mrok/proxy/ziticorn.py`).** The Python agent does, verbatim:
```python
ctx, err = openziti.load(str(identity_file), timeout=...)   # load the identity file as-is (mrok key included)
sock = ctx.bind(identity.mrok.extension)                    # bind service = identity.mrok.extension
sock.listen(backlog)                                        # then listen; uvicorn serves on this socket
```
So the **bind service name = the `mrok.extension` field inside the identity file** (e.g. `ext-5034-5001`) — read it from the loaded identity, not from a separate config value. `SDK_ZITI_SERVICE` remains an optional override. Also: `openziti.load` is given the **whole identity file unmodified** (the `mrok` key is ignored by ziti-sdk-c), and `ctx.bind` uses the **default terminator** (none passed) — mirror both in .NET (the `mrok`-strip step is optional safety; pass an empty/null terminator to `API.Bind`).

**Testing reality:** A true end-to-end bind requires a live Ziti controller + a valid enrolled identity (the POC identity points at the real `api.ziti.s1.show` — do NOT bind against production from CI). Automated tests therefore cover the **identity mapper**, **DI/options wiring**, and the **TCP-fallback path** of the listener factory. The live overlay bind is validated by a **manual/deployment smoke** (documented), not CI.

---

## File structure (end state of Plan 2)

```
$DST/
  src/Mpt.Extensions.Sdk.Ziti/
    Mpt.Extensions.Sdk.Ziti.csproj         # net8.0; refs OpenZiti.NET + the core SDK
    ZitiEndPoint.cs                         # marker EndPoint carrying the service name
    ZitiConnectionListenerFactory.cs        # adapted from the upstream sample
    ZitiConnectionListener.cs               # accept-loop -> Channel -> SocketConnectionContextFactory
    ZitiIdentity.cs                         # map persisted channel.identity -> ziti identity file
    ZitiOptions.cs                          # identity path + service name (from config)
    ZitiHostExtensions.cs                   # UseZitiTransport(...) / UseZiti() host wiring
  tests/Mpt.Extensions.Sdk.Ziti.Tests/
    Mpt.Extensions.Sdk.Ziti.Tests.csproj
    ZitiIdentityTests.cs
    ZitiOptionsTests.cs
    ZitiConnectionListenerFactoryTests.cs   # TCP-fallback path only
  docs/ziti-deployment-smoke.md             # manual end-to-end validation steps
```

`Mpt.Extensions.Sdk.Ziti` depends on `Mpt.Extensions.Sdk` (Hosting) + `OpenZiti.NET`. The core SDK keeps NO dependency on `OpenZiti.NET` (the native dep stays isolated here).

---

## Task 1: Scaffold the Ziti project and confirm the native package restores on net8.0

**Files:** Create `src/Mpt.Extensions.Sdk.Ziti/Mpt.Extensions.Sdk.Ziti.csproj`; modify `Mpt.Extensions.Sdk.sln`.

- [ ] **Step 1: Create the project**

`src/Mpt.Extensions.Sdk.Ziti/Mpt.Extensions.Sdk.Ziti.csproj`:
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <GenerateDocumentationFile>true</GenerateDocumentationFile>
    <NoWarn>$(NoWarn);CS1591</NoWarn>
    <IsPackable>true</IsPackable>
    <PackageId>Mpt.Extensions.Sdk.Ziti</PackageId>
    <Title>MPT Extension SDK — OpenZiti transport</Title>
    <Description>Serve a SoftwareONE Marketplace extension over the OpenZiti overlay (the .NET ziticorn equivalent).</Description>
  </PropertyGroup>
  <ItemGroup>
    <FrameworkReference Include="Microsoft.AspNetCore.App" />
  </ItemGroup>
  <ItemGroup>
    <PackageReference Include="OpenZiti.NET" Version="1.0.26159.2780" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\Mpt.Extensions.Sdk\Mpt.Extensions.Sdk.csproj" />
  </ItemGroup>
  <ItemGroup>
    <InternalsVisibleTo Include="Mpt.Extensions.Sdk.Ziti.Tests" />
  </ItemGroup>
</Project>
```

- [ ] **Step 2: Add to the solution**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet sln Mpt.Extensions.Sdk.sln add src/Mpt.Extensions.Sdk.Ziti/Mpt.Extensions.Sdk.Ziti.csproj
```

- [ ] **Step 3: Add a placeholder type so the project compiles, then restore/build**

Create `src/Mpt.Extensions.Sdk.Ziti/ZitiOptions.cs` with a temporary empty `namespace Mpt.Extensions.Sdk.Ziti; internal sealed class ZitiOptions { }` (replaced in Task 3), then:
```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet build src/Mpt.Extensions.Sdk.Ziti/Mpt.Extensions.Sdk.Ziti.csproj
```
Expected: restore pulls `OpenZiti.NET` + `OpenZiti.NET.native`; **Build succeeded**. If `OpenZiti.NET` fails to resolve on `nuget.org`, confirm the version exists (the spike found `1.0.26159.2780`, published 2026-06-08); pin to the latest available `1.0.*` shown on https://www.nuget.org/packages/OpenZiti.NET . If the native package warns about RID assets, that is expected at pack time, not build.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat(ziti): scaffold OpenZiti transport project (net8.0)"
```

## Task 2: Identity mapping (TDD)

**Files:** Create `src/Mpt.Extensions.Sdk.Ziti/ZitiIdentity.cs`; test `tests/Mpt.Extensions.Sdk.Ziti.Tests/ZitiIdentityTests.cs` (+ the test csproj — see Step 0).

- [ ] **Step 0: Create the Ziti test project** (mirror `Mpt.Extensions.Sdk.Tests.csproj`: same package versions — `Microsoft.NET.Test.Sdk` 17.12.0, `xunit` 2.9.2, `xunit.runner.visualstudio` 3.0.0, `coverlet.collector` 6.0.4, `<Using Include="Xunit" />`, `FrameworkReference Microsoft.AspNetCore.App`), with a `ProjectReference` to `..\..\src\Mpt.Extensions.Sdk.Ziti\Mpt.Extensions.Sdk.Ziti.csproj`. Add it to the solution with `dotnet sln add`.

- [ ] **Step 1: Write the failing test**

`tests/Mpt.Extensions.Sdk.Ziti.Tests/ZitiIdentityTests.cs`:
```csharp
using System.Text.Json;
using Mpt.Extensions.Sdk.Ziti;

namespace Mpt.Extensions.Sdk.Ziti.Tests;

public class ZitiIdentityTests
{
    // A realistic persisted channel.identity: standard ziti fields + the extra non-ziti "mrok" key.
    private const string Persisted = """
    {
      "ztAPI": "https://api.ziti.s1.show/edge/client/v1",
      "ztAPIs": null,
      "configTypes": null,
      "id": { "key": "pem:KEY", "cert": "pem:CERT", "ca": "pem:CA" },
      "enableHa": false,
      "mrok": { "extension": "ext-1", "instance": "ins-1", "tags": { "mrok-service": "ext-1" } }
    }
    """;

    [Fact]
    public void WriteZitiIdentityFile_strips_mrok_and_keeps_ziti_fields()
    {
        var dir = Path.Combine(Path.GetTempPath(), $"ziti-{Guid.NewGuid():N}");
        var outPath = Path.Combine(dir, "ziti-identity.json");

        ZitiIdentity.WriteZitiIdentityFile(Persisted, outPath);

        using var doc = JsonDocument.Parse(File.ReadAllText(outPath));
        var root = doc.RootElement;
        Assert.Equal("https://api.ziti.s1.show/edge/client/v1", root.GetProperty("ztAPI").GetString());
        Assert.Equal("pem:CERT", root.GetProperty("id").GetProperty("cert").GetString());
        Assert.False(root.TryGetProperty("mrok", out _)); // non-ziti metadata removed
    }

    [Fact]
    public void ServiceNameFromMrok_returns_mrok_extension()
    {
        // The Python mrok agent binds `identity.mrok.extension` — mirror that exactly.
        Assert.Equal("ext-1", ZitiIdentity.ServiceNameFromMrok(Persisted));
    }

    [Fact]
    public void ServiceNameFromMrok_returns_null_when_absent()
    {
        Assert.Null(ZitiIdentity.ServiceNameFromMrok("{\"ztAPI\":\"x\"}"));
    }
}
```

- [ ] **Step 2: Run, expect FAIL**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet' && dotnet test tests/Mpt.Extensions.Sdk.Ziti.Tests/Mpt.Extensions.Sdk.Ziti.Tests.csproj --filter FullyQualifiedName~ZitiIdentityTests
```

- [ ] **Step 3: Implement**

`src/Mpt.Extensions.Sdk.Ziti/ZitiIdentity.cs`:
```csharp
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Mpt.Extensions.Sdk.Ziti;

/// <summary>
/// Bridges the persisted platform identity (<c>channel.identity</c>) to a ziti-loadable
/// identity file. The persisted JSON is already a standard enrolled ziti identity plus an
/// extra non-ziti <c>mrok</c> metadata key, which we strip before handing it to the loader.
/// </summary>
public static class ZitiIdentity
{
    /// <summary>Write a ziti-ready identity file (mrok stripped) to <paramref name="outPath"/>.</summary>
    public static void WriteZitiIdentityFile(string persistedIdentityJson, string outPath)
    {
        var node = JsonNode.Parse(persistedIdentityJson)?.AsObject()
            ?? throw new InvalidOperationException("Identity JSON is not an object.");
        node.Remove("mrok");

        var dir = Path.GetDirectoryName(outPath);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);
        File.WriteAllText(outPath, node.ToJsonString());
    }

    /// <summary>
    /// The bind service name, taken from <c>mrok.extension</c> — exactly what the Python
    /// mrok agent binds (<c>ctx.bind(identity.mrok.extension)</c>). Null if absent.
    /// </summary>
    public static string? ServiceNameFromMrok(string persistedIdentityJson)
    {
        using var doc = JsonDocument.Parse(persistedIdentityJson);
        if (doc.RootElement.TryGetProperty("mrok", out var mrok) &&
            mrok.TryGetProperty("extension", out var ext))
        {
            return ext.GetString();
        }
        return null;
    }
}
```

- [ ] **Step 4: Run, expect PASS. Step 5: Commit** `git add -A && git commit -m "feat(ziti): map persisted identity to ziti identity file"`

## Task 3: Ziti options (TDD)

**Files:** Replace `src/Mpt.Extensions.Sdk.Ziti/ZitiOptions.cs`; test `tests/Mpt.Extensions.Sdk.Ziti.Tests/ZitiOptionsTests.cs`.

- [ ] **Step 1: Write the failing test**

```csharp
using Microsoft.Extensions.Configuration;
using Mpt.Extensions.Sdk.Ziti;

namespace Mpt.Extensions.Sdk.Ziti.Tests;

public class ZitiOptionsTests
{
    [Fact]
    public void FromConfiguration_defaults_service_to_extension_id_lowercased()
    {
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["SDK_EXTENSION_ID"] = "EXT-5034-5001",
            ["SDK_IDENTITY_FILE_PATH"] = "./identity/identity.json",
        }).Build();

        var o = ZitiOptions.FromConfiguration(config);

        Assert.Equal("ext-5034-5001", o.ServiceName);
        Assert.Equal("./identity/identity.json", o.IdentityFilePath);
    }

    [Fact]
    public void FromConfiguration_honors_explicit_service_override()
    {
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["SDK_EXTENSION_ID"] = "EXT-1",
            ["SDK_ZITI_SERVICE"] = "custom-svc",
        }).Build();

        Assert.Equal("custom-svc", ZitiOptions.FromConfiguration(config).ServiceName);
    }
}
```

- [ ] **Step 2: Run, expect FAIL. Step 3: Implement** `src/Mpt.Extensions.Sdk.Ziti/ZitiOptions.cs`:
```csharp
using Microsoft.Extensions.Configuration;

namespace Mpt.Extensions.Sdk.Ziti;

/// <summary>Ziti transport options resolved from configuration.</summary>
public sealed class ZitiOptions
{
    /// <summary>Path to the persisted platform identity (same file the registration step writes).</summary>
    public required string IdentityFilePath { get; init; }

    /// <summary>The ziti service the extension binds to receive inbound traffic.</summary>
    public required string ServiceName { get; init; }

    public static ZitiOptions FromConfiguration(IConfiguration config)
    {
        var extensionId = config["SDK_EXTENSION_ID"] ?? "";
        var service = config["SDK_ZITI_SERVICE"];
        if (string.IsNullOrEmpty(service))
            service = extensionId.ToLowerInvariant();
        return new ZitiOptions
        {
            IdentityFilePath = config["SDK_IDENTITY_FILE_PATH"] ?? "identity/identity.json",
            ServiceName = service,
        };
    }
}
```
Service-name resolution priority (authoritative source confirmed from `mrok`): `SDK_ZITI_SERVICE` override → **`ZitiIdentity.ServiceNameFromMrok(identity)` = `mrok.extension`** (what `mrok` binds) → `SDK_EXTENSION_ID` lowercased as a last-resort fallback. `ZitiOptions` here covers the config-only paths; `UseZiti` (Task 5) prefers the identity's `mrok.extension` once the identity file is read. The config default to the lowercased extension id matches the observed `mrok.extension` value, so the two agree.

- [ ] **Step 4: Run, expect PASS. Step 5: Commit** `git add -A && git commit -m "feat(ziti): ZitiOptions from configuration"`

## Task 4: Vendor + adapt the Kestrel transport from the upstream sample

**Files:** Create `ZitiEndPoint.cs`, `ZitiConnectionListenerFactory.cs`, `ZitiConnectionListener.cs`.

> Do NOT hand-invent the OpenZiti API calls. FETCH the upstream sample source and adapt it. These files are the reference implementation; copy their structure and adjust namespaces/types to our project.

- [ ] **Step 1: Fetch the upstream sample sources**

Retrieve (WebFetch on the raw GitHub URLs under `OpenZiti.NET.Samples/src/Kestrel/`):
- `ZitiConnectionListenerFactory.cs`
- `ServiceCollectionExtensions.cs` (for the `UseZitiTransport` wiring — used in Task 5)
- `KestrelSample.cs` (shows end-to-end usage)
Base: https://raw.githubusercontent.com/openziti/ziti-sdk-csharp/main/OpenZiti.NET.Samples/src/Kestrel/
Read them to learn the exact `ZitiSocket`/`API.Bind/Listen/Accept` usage, the `ZitiEndPoint`, the accept-loop + `Channel`, and the `SocketConnectionContextFactory.Create(socket)` call.

- [ ] **Step 2: Vendor `ZitiEndPoint.cs`** — a `System.Net.EndPoint` subclass carrying the bind service name (copy from the sample; namespace `Mpt.Extensions.Sdk.Ziti`).

- [ ] **Step 3: Vendor `ZitiConnectionListenerFactory.cs` + `ZitiConnectionListener.cs`** — adapt the sample's `IConnectionListenerFactory`/`IConnectionListener`:
  - `BindAsync`: when the `EndPoint` is a `ZitiEndPoint`, create `ZitiSocket(SocketType.Stream)`, load the `ZitiContext` from the mapped identity file (produced in Task 2 / wired in Task 5), `API.Bind(socket, ctx, serviceName, terminator)`, `API.Listen(socket, backlog)`, return the listener; otherwise fall back to the default TCP `SocketTransportFactory` behavior (keep the fallback — it makes local/test usage and unit testing possible).
  - The listener runs a background accept loop: `Poll(SelectRead)` → `API.Accept(...)` → write `(ZitiSocket, caller)` to an `UnboundedChannel`; `AcceptAsync` reads the channel, calls `client.ToSocket()`, and returns `SocketConnectionContextFactory.Create(socket)` as the `ConnectionContext`.
  - Honour `CancellationToken`/`UnbindAsync`/`DisposeAsync` with a bounded shutdown (the sample uses ~5s).
  - Keep the OpenZiti context init (`API.InitializeZiti(...)`/run-loop) exactly as the sample does it.

- [ ] **Step 4: Build**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet' && dotnet build src/Mpt.Extensions.Sdk.Ziti/Mpt.Extensions.Sdk.Ziti.csproj
```
Expected: Build succeeded. Resolve any API drift between the sample (which may target a newer SDK) and `1.0.26159.2780` by reading the installed package's types (e.g. via the `dotnet-inspect` skill or the `OpenZiti.NET` source on GitHub) and adjusting calls.

- [ ] **Step 5: Commit** `git add -A && git commit -m "feat(ziti): vendor + adapt Kestrel IConnectionListenerFactory over OpenZiti"`

## Task 5: Host wiring — `UseZiti()` (TDD where possible)

**Files:** Create `ZitiHostExtensions.cs`; test `tests/Mpt.Extensions.Sdk.Ziti.Tests/ZitiConnectionListenerFactoryTests.cs` (TCP-fallback path).

- [ ] **Step 1: Implement `UseZiti()`** in `src/Mpt.Extensions.Sdk.Ziti/ZitiHostExtensions.cs`:
  - An extension `public static WebApplicationBuilder UseZiti(this WebApplicationBuilder builder)` (or `IWebHostBuilder`) that:
    1. resolves `ZitiOptions.FromConfiguration(builder.Configuration)`,
    2. on startup (or inline before Kestrel binds), reads the persisted identity at `IdentityFilePath`, calls `ZitiIdentity.WriteZitiIdentityFile(...)` to a sibling `ziti-identity.json`, and resolves the bind service name as `SDK_ZITI_SERVICE` (if set) else `ZitiIdentity.ServiceNameFromMrok(identity)` (= `mrok.extension`, exactly what the Python `mrok` agent binds via `ctx.bind(identity.mrok.extension)`),
    3. registers the `ZitiConnectionListenerFactory` as `IConnectionListenerFactory` and configures Kestrel to listen on a `ZitiEndPoint(serviceName)` (model the `UseZitiTransport` wiring from the sample's `ServiceCollectionExtensions.cs`).
  - This must compose with the core SDK: the consumer writes `ExtensionHostBuilder.Build(builder)` and, for platform deployment, also calls `builder.UseZiti()` (order per what the wiring requires — document it).
  - IMPORTANT ordering vs registration: the identity file must exist before Ziti binds. The core SDK's `RegistrationHostedService` writes it on startup in platform mode. Ensure `UseZiti` reads the identity at the right time (e.g. resolve/transform lazily at first bind, or document that registration must complete first). If a startup-ordering conflict exists, have `UseZiti` perform registration-or-wait, or expose an explicit `await app.RegisterAsync()` the consumer calls before `RunAsync()`. Choose the simplest correct ordering and document it in `docs/ziti-deployment-smoke.md`.

- [ ] **Step 2: Test the TCP-fallback path** (the only path testable without a live controller). `ZitiConnectionListenerFactoryTests.cs`: assert that `BindAsync` with a normal `IPEndPoint` returns a working TCP `IConnectionListener` (i.e. the factory degrades to TCP for non-Ziti endpoints), proving the factory is wired correctly and safe in local mode. If the adapted factory delegates TCP to `SocketTransportFactory`, a minimal test can bind `IPEndPoint(IPAddress.Loopback, 0)` and assert a non-null listener + `EndPoint`.

- [ ] **Step 3: Build + run the Ziti test project + full solution**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet test Mpt.Extensions.Sdk.sln
```
Expected: all green (existing 69 + the new Ziti unit tests). The core SDK tests are unaffected (no dependency on the Ziti project).

- [ ] **Step 4: Commit** `git add -A && git commit -m "feat(ziti): UseZiti() host wiring + TCP-fallback test"`

## Task 6: Update the sample + document the deployment smoke

**Files:** Modify `samples/Sample.LocalExtension/Program.cs` (show the platform-mode opt-in, guarded); create `docs/ziti-deployment-smoke.md`.

- [ ] **Step 1: Show the opt-in in the sample (without breaking local run)**

In `samples/Sample.LocalExtension/Program.cs`, demonstrate the pattern without requiring Ziti locally:
```csharp
using Microsoft.AspNetCore.Builder;
using Mpt.Extensions.Sdk.Hosting;
using Mpt.Extensions.Sdk.Ziti;

var builder = WebApplication.CreateBuilder(args);
var platform = string.Equals(builder.Configuration["SDK_MODE"], "platform", StringComparison.OrdinalIgnoreCase);
if (platform)
    builder.UseZiti();          // serve over the Ziti overlay using the persisted identity
else
    builder.Configuration["SDK_MODE"] = "local"; // local dev: plain Kestrel, skip registration

var app = ExtensionHostBuilder.Build(builder);
app.Run();
```
Add a `ProjectReference` to `Mpt.Extensions.Sdk.Ziti` in the sample csproj. Build the solution; confirm the sample still runs locally (plain Kestrel) exactly as in Plan 1's smoke (`/__health` → ok). Do NOT attempt a live Ziti bind here.

- [ ] **Step 2: Write `docs/ziti-deployment-smoke.md`** — the manual end-to-end validation: set `SDK_MODE=platform`, `SDK_EXTENSION_ID`, `SDK_EXTENSION_API_KEY`, `SDK_EXTENSION_URL`, `MPT_API_BASE_URL`, `SDK_IDENTITY_FILE_PATH`; run; confirm registration persists the identity, the Ziti transport binds the service, and a platform-routed event reaches a handler. Note the prerequisite (a real enrolled identity + reachable controller) and that this is NOT run in CI.

- [ ] **Step 3: Build + full suite + commit**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet build Mpt.Extensions.Sdk.sln && dotnet test Mpt.Extensions.Sdk.sln
git add -A && git commit -m "docs(ziti): sample opt-in + deployment smoke guide"
```

---

## Self-review notes

- **Spec coverage:** the `Swo.Mpt.Extensions.Ziti` package (here `Mpt.Extensions.Sdk.Ziti`), identity mapping, B1 transport, `UseZiti()` wiring, and the local/platform split are all covered. The native dep stays isolated (core SDK unchanged). The Abstractions/Hosting/Ziti three-way split from the spec is realized as: core `Mpt.Extensions.Sdk` (authoring + hosting) + `Mpt.Extensions.Sdk.Ziti` — the Abstractions/Hosting split was deemed unnecessary for now (YAGNI; the isolation that mattered was the native Ziti dep, which this achieves).
- **Open question (bind service name)** is flagged at the top and at Task 3/4 — resolve with the platform team; only the default in `ZitiOptions` changes if it differs.
- **Testing honesty:** no silent claim of end-to-end coverage — the live overlay bind is a documented manual smoke (Task 6), because it needs a real controller + identity. Automated tests cover identity mapping, options, and the TCP-fallback path.
- **API drift:** Task 4 explicitly says to adapt the sample to the pinned `OpenZiti.NET 1.0.26159.2780` API by reading the installed package types, since the sample tracks `main`.

## Execution handoff

After Plan 2, the SDK serves over Ziti in platform mode. Remaining future work (separate): Plan 3 — port `product-hub-extension` onto the pure-.NET SDK as the acceptance check (drop its bridge, supply its own models, validate against s1.show), which also exercises the deployment smoke.
