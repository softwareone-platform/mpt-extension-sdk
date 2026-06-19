# Pure-.NET Extension SDK — Plan 1: Foundation + Native Hosting

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap a pure-.NET (net8.0) Marketplace extension SDK in the empty directory `C:\repos\mpt-extension-sdk-dotnet`, porting the existing C# authoring surface and replacing the Python bridge's registration + ingress-auth + egress responsibilities with native .NET — producing a fully working **local-mode** extension host (no Ziti yet).

**Architecture:** Port the proven authoring code (attributes, contexts, dispatch, discovery, manifest, source generator) from the canonical repo `C:\repos\mpt-extension-dotnet-sdk` into a fresh solution, retargeted to net8.0. Then rewire the host pipeline: parse the real `Authorization: Bearer` JWT instead of the bridge's `X-Mpt-Auth` header, and replace the bridge egress proxy with a direct, account-scoped Marketplace `HttpClient` that mints/caches/refreshes account tokens. Registration runs as an `IHostedService`. The SDK stays model-agnostic — `IMarketplaceClient` is generic and serialization options are injectable.

**Tech Stack:** .NET 8 (ASP.NET Core minimal APIs, `IHostedService`, `IHttpClientFactory`), System.Text.Json, xUnit + `Microsoft.AspNetCore.Mvc.Testing` (`TestServer`), Roslyn source generator (netstandard2.0).

**Scope boundaries (deferred to later plans):**
- **Plan 2:** OpenZiti transport (the `OpenZiti.NET` Kestrel binding) + the Abstractions/Ziti package split. Plan 1 ships a single `Mpt.Extensions.Sdk` package; the package split exists to isolate the native Ziti dependency, so it is premature before Plan 2 (YAGNI).
- **Plan 3:** Porting `product-hub-extension` onto the pure-.NET SDK as the acceptance check.

**Source-of-truth for ports:** `C:\repos\mpt-extension-dotnet-sdk` (read-only; do not modify it). Referred to below as `$SRC`. The new work directory `C:\repos\mpt-extension-sdk-dotnet` is referred to as `$DST`.

---

## File structure (end state of Plan 1)

```
$DST/
  Mpt.Extensions.Sdk.slnx
  Directory.Build.props                 # net8.0, shared metadata
  nuget.config                          # nuget.org + PyraCloud (for consumers; SDK itself needs neither)
  .gitignore
  src/
    Mpt.Extensions.Sdk/                  # the one SDK package (authoring + native hosting)
      Attributes/ Contexts/ Events/ Manifest/ Dispatch/ Discovery/ Generated/   # ported as-is
      Marketplace/
        IMarketplaceClient.cs            # ported (generic; unchanged)
        MarketplaceApiException.cs       # ported (unchanged)
        HttpMarketplaceClient.cs         # NEW — direct account-scoped MPT API client
      Auth/
        AuthContext.cs                   # ported + enriched (permissions/claims)
        SoftwareOneJwt.cs                # NEW — decode-not-verify JWT claims
        RequestAuthenticator.cs          # NEW — Bearer → AuthContext (+ exp check)
        IAccountTokenProvider.cs         # NEW
        AccountTokenProvider.cs          # NEW — mint/cache/refresh per-account token
      Hosting/
        ExtensionHostBuilder.cs          # ported + rewired (native auth/client, registration)
        ExtensionEndpoints.cs            # ported + rewired (real JWT, no bridge token/egress header)
        ExtensionOptions.cs              # NEW — typed runtime options (replaces HostOptions)
      Registration/
        IdentityStore.cs                 # NEW — read/write identity file
        RegistrationPayload.cs           # NEW — request/response DTOs + meta block
        RegistrationService.cs           # NEW — POST instances, persist identity
        RegistrationHostedService.cs     # NEW — runs registration on startup (platform mode)
        MetaBuilder.cs                   # NEW — ExtensionManifest → meta object (+ meta.yaml)
      Serialization/MptJson.cs           # ported + made configurable
    Mpt.Extensions.Sdk.SourceGen/        # ported as-is (netstandard2.0)
  tests/
    Mpt.Extensions.Sdk.Tests/            # ported core tests + new tests, rewired for native auth
    Mpt.Extensions.Sdk.SourceGen.Tests/  # ported as-is
```

---

## Phase A — Bootstrap the solution

### Task A1: Initialise the repository and solution skeleton

**Files:**
- Create: `$DST/.gitignore`
- Create: `$DST/Directory.Build.props`
- Create: `$DST/nuget.config`
- Create: `$DST/Mpt.Extensions.Sdk.slnx`

- [ ] **Step 1: Initialise git in the empty work dir**

Run:
```bash
cd 'C:/repos/mpt-extension-sdk-dotnet' && git init -b main && echo done
```
Expected: `Initialized empty Git repository …` then `done`.

- [ ] **Step 2: Create `.gitignore`**

Create `$DST/.gitignore`:
```gitignore
bin/
obj/
*.user
.vs/
identity/
*.identity.json
artifacts/
```

- [ ] **Step 3: Create `Directory.Build.props` (net8.0)**

Create `$DST/Directory.Build.props`:
```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <LangVersion>latest</LangVersion>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>

    <Authors>SoftwareOne</Authors>
    <Company>SoftwareOne</Company>
    <Copyright>SoftwareOne © 2026</Copyright>
    <Version>0.1.0-alpha.1</Version>
    <IsPackable>false</IsPackable>
    <PackageLicenseExpression>Apache-2.0</PackageLicenseExpression>
  </PropertyGroup>
</Project>
```

- [ ] **Step 4: Create `nuget.config`**

Create `$DST/nuget.config` (PyraCloud is for downstream extensions that reference platform contracts; the SDK itself needs only nuget.org):
```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
    <add key="PyraCloud" value="https://pkgs.dev.azure.com/softwareone-pc/_packaging/PyraCloud/nuget/v3/index.json" />
  </packageSources>
</configuration>
```

- [ ] **Step 5: Create the solution file**

Create `$DST/Mpt.Extensions.Sdk.slnx`:
```xml
<Solution>
  <Folder Name="/src/">
    <Project Path="src/Mpt.Extensions.Sdk/Mpt.Extensions.Sdk.csproj" />
    <Project Path="src/Mpt.Extensions.Sdk.SourceGen/Mpt.Extensions.Sdk.SourceGen.csproj" />
  </Folder>
  <Folder Name="/tests/">
    <Project Path="tests/Mpt.Extensions.Sdk.Tests/Mpt.Extensions.Sdk.Tests.csproj" />
    <Project Path="tests/Mpt.Extensions.Sdk.SourceGen.Tests/Mpt.Extensions.Sdk.SourceGen.Tests.csproj" />
  </Folder>
</Solution>
```

- [ ] **Step 6: Verify .NET 8 SDK is available**

Run:
```bash
dotnet --list-sdks
```
Expected: at least one `8.0.x` SDK listed. If only net10 is installed, install the .NET 8 SDK before continuing (or add a `global.json` pinning 8.0).

- [ ] **Step 7: Commit**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
git add -A
git commit -m "chore: bootstrap solution skeleton (net8.0)"
```

---

### Task A2: Copy the design docs into the new repo

**Files:**
- Create: `$DST/docs/superpowers/specs/2026-06-19-dotnet-extension-sdk-design.md`
- Create: `$DST/docs/superpowers/plans/2026-06-19-dotnet-sdk-plan1-foundation-and-native-hosting.md`

- [ ] **Step 1: Copy spec and plan so they travel with the code**

Run (paths are the current worktree of the Python repo where these docs live):
```bash
mkdir -p 'C:/repos/mpt-extension-sdk-dotnet/docs/superpowers/specs' 'C:/repos/mpt-extension-sdk-dotnet/docs/superpowers/plans'
cp 'C:/repos/mpt-extension-sdk/.claude/worktrees/heuristic-leakey-ff4ebd/docs/superpowers/specs/2026-06-19-dotnet-extension-sdk-design.md' 'C:/repos/mpt-extension-sdk-dotnet/docs/superpowers/specs/'
cp 'C:/repos/mpt-extension-sdk/.claude/worktrees/heuristic-leakey-ff4ebd/docs/superpowers/plans/2026-06-19-dotnet-sdk-plan1-foundation-and-native-hosting.md' 'C:/repos/mpt-extension-sdk-dotnet/docs/superpowers/plans/'
```

- [ ] **Step 2: Commit**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
git add -A
git commit -m "docs: import design spec and Plan 1"
```

---

## Phase B — Port the authoring surface (verbatim, net8.0)

> These files are already model-agnostic and net-version-neutral. Copy them as-is; do not edit namespaces (we keep the `Mpt.Extensions.Sdk` root). After copying, build to surface any net10-only API usage (Risk: net10→net8 retarget).

### Task B1: Port the source generator project

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk.SourceGen/` (copy of `$SRC/src/Mpt.Extensions.Sdk.SourceGen/`)

- [ ] **Step 1: Copy the source-generator project**

```bash
mkdir -p 'C:/repos/mpt-extension-sdk-dotnet/src'
cp -r 'C:/repos/mpt-extension-dotnet-sdk/src/Mpt.Extensions.Sdk.SourceGen' 'C:/repos/mpt-extension-sdk-dotnet/src/'
rm -rf 'C:/repos/mpt-extension-sdk-dotnet/src/Mpt.Extensions.Sdk.SourceGen/bin' 'C:/repos/mpt-extension-sdk-dotnet/src/Mpt.Extensions.Sdk.SourceGen/obj'
```

- [ ] **Step 2: Confirm it targets netstandard2.0 (analyzers must)**

Read `$DST/src/Mpt.Extensions.Sdk.SourceGen/Mpt.Extensions.Sdk.SourceGen.csproj`.
Expected: `<TargetFramework>netstandard2.0</TargetFramework>` is set **explicitly inside the csproj** (so the repo-wide net8.0 default does not apply). If the csproj relies on the old `Directory.Build.props` net10 inheritance and has no explicit TFM, add `<TargetFramework>netstandard2.0</TargetFramework>` to its first `<PropertyGroup>`, and add `<TreatWarningsAsErrors>false</TreatWarningsAsErrors>` only if the generator emits analyzer-package warnings.

- [ ] **Step 3: Build just the generator**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet build src/Mpt.Extensions.Sdk.SourceGen/Mpt.Extensions.Sdk.SourceGen.csproj
```
Expected: `Build succeeded`. Fix any netstandard2.0 incompatibilities surfaced.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: port source generator project"
```

### Task B2: Port the authoring code into the core SDK project

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk/` with the subfolders `Attributes/`, `Contexts/`, `Events/`, `Manifest/`, `Dispatch/`, `Discovery/`, `Generated/`, `Marketplace/`, `Auth/`, `Serialization/`
- Create: `$DST/src/Mpt.Extensions.Sdk/Mpt.Extensions.Sdk.csproj`

- [ ] **Step 1: Copy the authoring source folders (NOT Hosting yet — that gets rewired in Phase D)**

```bash
SRC='C:/repos/mpt-extension-dotnet-sdk/src/Mpt.Extensions.Sdk'
DST='C:/repos/mpt-extension-sdk-dotnet/src/Mpt.Extensions.Sdk'
mkdir -p "$DST"
for d in Attributes Contexts Events Manifest Dispatch Discovery Generated Marketplace Auth Serialization; do
  cp -r "$SRC/$d" "$DST/"
done
```

- [ ] **Step 2: Remove the egress-only Marketplace files (replaced by native client in Phase D)**

```bash
DST='C:/repos/mpt-extension-sdk-dotnet/src/Mpt.Extensions.Sdk'
rm -f "$DST/Marketplace/EgressMarketplaceClient.cs" "$DST/Marketplace/MarketplaceRequest.cs"
```
(We keep `IMarketplaceClient.cs` and `MarketplaceApiException.cs`.)

- [ ] **Step 3: Create the core csproj (net8.0; no bridge analyzer error target needed yet, keep the analyzer bundling)**

Create `$DST/src/Mpt.Extensions.Sdk/Mpt.Extensions.Sdk.csproj`:
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <GenerateDocumentationFile>true</GenerateDocumentationFile>
    <NoWarn>$(NoWarn);CS1591</NoWarn>

    <IsPackable>true</IsPackable>
    <PackageId>Mpt.Extensions.Sdk</PackageId>
    <Title>MPT Extension SDK for .NET</Title>
    <Description>Author SoftwareONE Marketplace extensions in C#. Pure-.NET host: native registration, OpenZiti transport, and account-scoped Marketplace access. Includes the bundled Roslyn source generator.</Description>
    <PackageTags>mpt;marketplace;softwareone;extensions;sdk</PackageTags>
  </PropertyGroup>

  <ItemGroup>
    <FrameworkReference Include="Microsoft.AspNetCore.App" />
  </ItemGroup>

  <ItemGroup>
    <InternalsVisibleTo Include="Mpt.Extensions.Sdk.Tests" />
    <InternalsVisibleTo Include="Mpt.Extensions.Sdk.SourceGen.Tests" />
  </ItemGroup>

  <ItemGroup>
    <ProjectReference Include="..\Mpt.Extensions.Sdk.SourceGen\Mpt.Extensions.Sdk.SourceGen.csproj"
                      OutputItemType="Analyzer" ReferenceOutputAssembly="false" PrivateAssets="all" />
  </ItemGroup>
  <PropertyGroup>
    <_SourceGenDll>..\Mpt.Extensions.Sdk.SourceGen\bin\$(Configuration)\netstandard2.0\Mpt.Extensions.Sdk.SourceGen.dll</_SourceGenDll>
  </PropertyGroup>
  <ItemGroup>
    <None Include="$(_SourceGenDll)" Pack="true" PackagePath="analyzers/dotnet/cs" Visible="false" />
  </ItemGroup>
  <Target Name="EnsureAnalyzerBundled" BeforeTargets="GenerateNuspec">
    <Error Condition="!Exists('$(_SourceGenDll)')"
           Text="Source generator not found at $(_SourceGenDll). Build the solution in this configuration before packing so the analyzer is bundled." />
  </Target>
</Project>
```

- [ ] **Step 4: Temporarily exclude Hosting so the project builds without it**

The copied folders do **not** include `Hosting/`, so the core project has no `ExtensionHostBuilder` yet. That is expected — Phase D adds Hosting. The project should still compile (authoring types only).

Run:
```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet build src/Mpt.Extensions.Sdk/Mpt.Extensions.Sdk.csproj
```
Expected: `Build succeeded`. If any file references `Hosting`/`MptJson`/egress types that were removed, note them — they belong to Phase D and should not be in the copied folders. If `Serialization/MptJson.cs` is referenced by dispatch, keep it (it was copied).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: port authoring surface (attributes, contexts, dispatch, manifest, discovery)"
```

### Task B3: Port the test projects and get the ported tests green

**Files:**
- Create: `$DST/tests/Mpt.Extensions.Sdk.Tests/` (port; minus egress/marketplace-model tests)
- Create: `$DST/tests/Mpt.Extensions.Sdk.SourceGen.Tests/` (port as-is)

- [ ] **Step 1: Copy both test projects**

```bash
SRC='C:/repos/mpt-extension-dotnet-sdk/tests'
DST='C:/repos/mpt-extension-sdk-dotnet/tests'
mkdir -p "$DST"
cp -r "$SRC/Mpt.Extensions.Sdk.Tests" "$DST/"
cp -r "$SRC/Mpt.Extensions.Sdk.SourceGen.Tests" "$DST/"
find "$DST" -type d \( -name bin -o -name obj \) -prune -exec rm -rf {} +
```

- [ ] **Step 2: Remove tests that depend on dropped pieces (egress client, generated Marketplace models)**

```bash
DST='C:/repos/mpt-extension-sdk-dotnet/tests/Mpt.Extensions.Sdk.Tests'
rm -f "$DST/EgressMarketplaceClientTests.cs" "$DST/MarketplaceClientTests.cs"
```
(`MarketplaceClientTests` exercised the generated-models `MarketplaceClient`, which we are not porting. `EgressMarketplaceClientTests` tested the bridge egress client, now removed. `HostIntegrationTests` is kept but rewired in Phase D.)

- [ ] **Step 3: Fix the test csproj (remove the Marketplace-models project reference; net8.0 test stack)**

Overwrite `$DST/tests/Mpt.Extensions.Sdk.Tests/Mpt.Extensions.Sdk.Tests.csproj`:
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <IsPackable>false</IsPackable>
    <TreatWarningsAsErrors>false</TreatWarningsAsErrors>
  </PropertyGroup>

  <ItemGroup>
    <FrameworkReference Include="Microsoft.AspNetCore.App" />
  </ItemGroup>

  <ItemGroup>
    <PackageReference Include="coverlet.collector" Version="6.0.4" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.12.0" />
    <PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="8.0.11" />
    <PackageReference Include="xunit" Version="2.9.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="3.0.0" />
  </ItemGroup>

  <ItemGroup>
    <Using Include="Xunit" />
  </ItemGroup>

  <ItemGroup>
    <ProjectReference Include="..\..\src\Mpt.Extensions.Sdk\Mpt.Extensions.Sdk.csproj" />
  </ItemGroup>
</Project>
```

- [ ] **Step 4: Fix the SourceGen tests csproj the same way (net8.0 test stack, keep its existing project references)**

Open `$DST/tests/Mpt.Extensions.Sdk.SourceGen.Tests/Mpt.Extensions.Sdk.SourceGen.Tests.csproj` and set the same package versions as Step 3 (`Microsoft.NET.Test.Sdk` 17.12.0, `xunit` 2.9.2, `xunit.runner.visualstudio` 3.0.0, `Microsoft.AspNetCore.Mvc.Testing` 8.0.11 if referenced). Keep its `ProjectReference`s to the SDK and SourceGen projects. Remove any reference to `Mpt.Extensions.Sdk.Marketplace`.

- [ ] **Step 5: Move HostIntegrationTests aside until Phase D adds Hosting**

`HostIntegrationTests.cs` references `ExtensionHostBuilder` (added in Phase D). Rename it so it does not break the Phase B build:
```bash
DST='C:/repos/mpt-extension-sdk-dotnet/tests/Mpt.Extensions.Sdk.Tests'
mv "$DST/HostIntegrationTests.cs" "$DST/HostIntegrationTests.cs.pending"
```
(Phase D Task D6 restores and rewires it.)

- [ ] **Step 6: Build and run the ported tests**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet test
```
Expected: solution builds; the ported attribute/dispatch/manifest/discovery/event/auth/source-gen tests **pass**. Fix any net10→net8 issues that surface (e.g., trimmed APIs, `System.Text.Json` version differences). Do not proceed until green.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "test: port authoring + source-gen tests (net8.0), green"
```

---

## Phase C — Make serialization configurable

### Task C1: Replace the static `MptJson` with an injectable options holder

**Files:**
- Modify: `$DST/src/Mpt.Extensions.Sdk/Serialization/MptJson.cs`
- Test: `$DST/tests/Mpt.Extensions.Sdk.Tests/MptJsonTests.cs`

- [ ] **Step 1: Write the failing test**

Create `$DST/tests/Mpt.Extensions.Sdk.Tests/MptJsonTests.cs`:
```csharp
using System.Text.Json;
using Mpt.Extensions.Sdk.Serialization;

namespace Mpt.Extensions.Sdk.Tests;

public class MptJsonTests
{
    [Fact]
    public void Default_options_are_web_camelCase_and_case_insensitive()
    {
        Assert.Equal(JsonNamingPolicy.CamelCase, MptJson.Default.PropertyNamingPolicy);
        Assert.True(MptJson.Default.PropertyNameCaseInsensitive);
    }

    [Fact]
    public void CreateDefault_returns_an_independent_mutable_copy()
    {
        var a = MptJson.CreateDefault();
        var b = MptJson.CreateDefault();
        a.Converters.Add(new JsonStringEnumConverter());
        Assert.NotSame(a, b);
        Assert.Empty(b.Converters); // mutating one copy does not affect another
    }
}
```

- [ ] **Step 2: Run it — expect failure**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet test --filter FullyQualifiedName~MptJsonTests
```
Expected: FAIL — `MptJson.Default` / `MptJson.CreateDefault` do not exist.

- [ ] **Step 3: Implement**

Overwrite `$DST/src/Mpt.Extensions.Sdk/Serialization/MptJson.cs`:
```csharp
using System.Text.Json;

namespace Mpt.Extensions.Sdk.Serialization;

/// <summary>
/// Shared JSON configuration. <see cref="Default"/> is the read-only options the host wire
/// uses (event envelope, manifest, responses). Extensions that deserialize platform contracts
/// supply their own options via <see cref="CreateDefault"/> + their converters.
/// </summary>
public static class MptJson
{
    /// <summary>Web defaults: camelCase, case-insensitive. Do not mutate.</summary>
    public static readonly JsonSerializerOptions Default = CreateDefault();

    /// <summary>A fresh, mutable options instance with the SDK's web defaults.</summary>
    public static JsonSerializerOptions CreateDefault() => new(JsonSerializerDefaults.Web);
}
```

- [ ] **Step 4: Run the test — expect pass**

```bash
dotnet test --filter FullyQualifiedName~MptJsonTests
```
Expected: PASS.

- [ ] **Step 5: Update internal references from `MptJson.Options` to `MptJson.Default`**

Search the core project for `MptJson.Options` and replace with `MptJson.Default`:
```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
grep -rl 'MptJson.Options' src tests || echo "none"
```
For each hit, change `MptJson.Options` → `MptJson.Default`. Then:
```bash
dotnet build
```
Expected: `Build succeeded`.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: make MptJson serialization options configurable"
```

---

## Phase D — Native hosting (auth, account tokens, Marketplace client, registration)

> This phase replaces everything the Python bridge did. Build it on **plain Kestrel** — no Ziti. By the end, an extension runs locally end-to-end with real JWT auth and direct MPT API calls.

### Task D1: Decode-not-verify SoftwareONE JWT claims

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk/Auth/SoftwareOneJwt.cs`
- Test: `$DST/tests/Mpt.Extensions.Sdk.Tests/SoftwareOneJwtTests.cs`

- [ ] **Step 1: Write the failing test**

Create `$DST/tests/Mpt.Extensions.Sdk.Tests/SoftwareOneJwtTests.cs`:
```csharp
using System.Text;
using System.Text.Json;
using Mpt.Extensions.Sdk.Auth;

namespace Mpt.Extensions.Sdk.Tests;

public class SoftwareOneJwtTests
{
    // Builds an unsigned-looking JWT: header.payload.signature (signature ignored).
    private static string MakeToken(object payload)
    {
        static string B64Url(byte[] b) =>
            Convert.ToBase64String(b).TrimEnd('=').Replace('+', '-').Replace('/', '_');
        var header = B64Url(Encoding.UTF8.GetBytes("{\"alg\":\"none\",\"typ\":\"JWT\"}"));
        var body = B64Url(JsonSerializer.SerializeToUtf8Bytes(payload));
        return $"{header}.{body}.sig";
    }

    [Fact]
    public void ParseClaims_reads_softwareone_namespaced_claims_and_exp()
    {
        var exp = DateTimeOffset.UtcNow.AddMinutes(5).ToUnixTimeSeconds();
        var token = MakeToken(new Dictionary<string, object>
        {
            ["https://claims.softwareone.com/accountId"] = "ACC-1",
            ["https://claims.softwareone.com/accountType"] = "Client",
            ["https://claims.softwareone.com/extensionId"] = "EXT-9",
            ["exp"] = exp,
        });

        var claims = SoftwareOneJwt.ParseClaims(token);

        Assert.Equal("ACC-1", claims.AccountId);
        Assert.Equal("Client", claims.AccountType);
        Assert.Equal("EXT-9", claims.ExtensionId);
        Assert.Equal(DateTimeOffset.FromUnixTimeSeconds(exp), claims.ExpiresAt);
    }

    [Fact]
    public void ParseClaims_throws_on_malformed_token()
    {
        Assert.Throws<FormatException>(() => SoftwareOneJwt.ParseClaims("not-a-jwt"));
    }
}
```

- [ ] **Step 2: Run it — expect failure**

```bash
dotnet test --filter FullyQualifiedName~SoftwareOneJwtTests
```
Expected: FAIL — `SoftwareOneJwt` does not exist.

- [ ] **Step 3: Implement**

Create `$DST/src/Mpt.Extensions.Sdk/Auth/SoftwareOneJwt.cs`:
```csharp
using System.Text.Json;

namespace Mpt.Extensions.Sdk.Auth;

/// <summary>Parsed SoftwareONE JWT claims. Signature is NOT verified — the platform gateway
/// verifies upstream; the host only decodes to build request context.</summary>
public sealed record SoftwareOneClaims(
    string AccountId,
    string? AccountType,
    string? ExtensionId,
    DateTimeOffset? ExpiresAt);

/// <summary>Decodes (does not verify) SoftwareONE platform JWTs.</summary>
public static class SoftwareOneJwt
{
    private const string Prefix = "https://claims.softwareone.com/";

    public static SoftwareOneClaims ParseClaims(string token)
    {
        var parts = token.Split('.');
        if (parts.Length < 2)
            throw new FormatException("Token is not a well-formed JWT (expected 3 segments).");

        using var doc = JsonDocument.Parse(DecodeSegment(parts[1]));
        var root = doc.RootElement;

        string GetString(string name) =>
            root.TryGetProperty(name, out var v) ? v.GetString() ?? "" : "";

        DateTimeOffset? exp = root.TryGetProperty("exp", out var e) && e.TryGetInt64(out var s)
            ? DateTimeOffset.FromUnixTimeSeconds(s)
            : null;

        var accountId = GetString(Prefix + "accountId");
        var accountType = GetString(Prefix + "accountType");
        var extensionId = GetString(Prefix + "extensionId");

        return new SoftwareOneClaims(
            accountId,
            string.IsNullOrEmpty(accountType) ? null : accountType,
            string.IsNullOrEmpty(extensionId) ? null : extensionId,
            exp);
    }

    private static byte[] DecodeSegment(string segment)
    {
        var s = segment.Replace('-', '+').Replace('_', '/');
        s = (s.Length % 4) switch { 2 => s + "==", 3 => s + "=", _ => s };
        return Convert.FromBase64String(s);
    }
}
```

- [ ] **Step 4: Run the test — expect pass**

```bash
dotnet test --filter FullyQualifiedName~SoftwareOneJwtTests
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: decode-not-verify SoftwareONE JWT claims"
```

### Task D2: Enrich `AuthContext` and add the request authenticator

**Files:**
- Modify: `$DST/src/Mpt.Extensions.Sdk/Auth/AuthContext.cs`
- Create: `$DST/src/Mpt.Extensions.Sdk/Auth/RequestAuthenticator.cs`
- Test: `$DST/tests/Mpt.Extensions.Sdk.Tests/RequestAuthenticatorTests.cs`

- [ ] **Step 1: Add a `Token` property to `AuthContext`**

Edit `$DST/src/Mpt.Extensions.Sdk/Auth/AuthContext.cs` — add (the account-scoped Marketplace client needs the raw bearer token's account id; we also carry the original token for diagnostics):
```csharp
    [JsonPropertyName("token")]
    public string? Token { get; init; }
```
Add it inside the existing `AuthContext` class alongside the other properties. Do not remove existing properties (`AccountId`, `AccountType`, `ExtensionId`, `InstallationId`, `UserId`).

- [ ] **Step 2: Write the failing test**

Create `$DST/tests/Mpt.Extensions.Sdk.Tests/RequestAuthenticatorTests.cs`:
```csharp
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Mpt.Extensions.Sdk.Auth;

namespace Mpt.Extensions.Sdk.Tests;

public class RequestAuthenticatorTests
{
    private static string MakeToken(object payload)
    {
        static string B64Url(byte[] b) =>
            Convert.ToBase64String(b).TrimEnd('=').Replace('+', '-').Replace('/', '_');
        var header = B64Url(Encoding.UTF8.GetBytes("{\"alg\":\"none\"}"));
        return $"{header}.{B64Url(JsonSerializer.SerializeToUtf8Bytes(payload))}.sig";
    }

    private static HttpContext WithBearer(string token)
    {
        var ctx = new DefaultHttpContext();
        ctx.Request.Headers.Authorization = $"Bearer {token}";
        return ctx;
    }

    [Fact]
    public void Authenticate_builds_context_from_valid_token()
    {
        var token = MakeToken(new Dictionary<string, object>
        {
            ["https://claims.softwareone.com/accountId"] = "ACC-1",
            ["https://claims.softwareone.com/accountType"] = "Client",
            ["exp"] = DateTimeOffset.UtcNow.AddMinutes(5).ToUnixTimeSeconds(),
        });

        var auth = new RequestAuthenticator().Authenticate(WithBearer(token));

        Assert.Equal("ACC-1", auth.AccountId);
        Assert.Equal("Client", auth.AccountType);
        Assert.Equal(token, auth.Token);
    }

    [Fact]
    public void Authenticate_throws_when_no_authorization_header()
    {
        Assert.Throws<UnauthorizedAccessException>(
            () => new RequestAuthenticator().Authenticate(new DefaultHttpContext()));
    }

    [Fact]
    public void Authenticate_throws_when_token_expired()
    {
        var token = MakeToken(new Dictionary<string, object>
        {
            ["https://claims.softwareone.com/accountId"] = "ACC-1",
            ["exp"] = DateTimeOffset.UtcNow.AddSeconds(-120).ToUnixTimeSeconds(),
        });
        Assert.Throws<UnauthorizedAccessException>(
            () => new RequestAuthenticator().Authenticate(WithBearer(token)));
    }
}
```

- [ ] **Step 2b: Run it — expect failure**

```bash
dotnet test --filter FullyQualifiedName~RequestAuthenticatorTests
```
Expected: FAIL — `RequestAuthenticator` does not exist.

- [ ] **Step 3: Implement**

Create `$DST/src/Mpt.Extensions.Sdk/Auth/RequestAuthenticator.cs`:
```csharp
using Microsoft.AspNetCore.Http;

namespace Mpt.Extensions.Sdk.Auth;

/// <summary>Builds an <see cref="AuthContext"/> from the platform's Bearer JWT.</summary>
public sealed class RequestAuthenticator
{
    private static readonly TimeSpan ExpiryLeeway = TimeSpan.FromSeconds(30);

    public AuthContext Authenticate(HttpContext http)
    {
        var header = http.Request.Headers.Authorization.ToString();
        if (string.IsNullOrEmpty(header) || !header.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
            throw new UnauthorizedAccessException("Missing or malformed Authorization header.");

        var token = header["Bearer ".Length..].Trim();

        SoftwareOneClaims claims;
        try { claims = SoftwareOneJwt.ParseClaims(token); }
        catch (Exception ex) { throw new UnauthorizedAccessException("Invalid bearer token.", ex); }

        if (claims.ExpiresAt is { } exp && exp + ExpiryLeeway < DateTimeOffset.UtcNow)
            throw new UnauthorizedAccessException("Bearer token has expired.");

        if (string.IsNullOrEmpty(claims.AccountId))
            throw new UnauthorizedAccessException("Token is missing the accountId claim.");

        return new AuthContext
        {
            AccountId = claims.AccountId,
            AccountType = claims.AccountType,
            ExtensionId = claims.ExtensionId,
            Token = token,
        };
    }
}
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
dotnet test --filter FullyQualifiedName~RequestAuthenticatorTests
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: native request authenticator (Bearer JWT -> AuthContext)"
```

### Task D3: Account-token provider (mint / cache / refresh)

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk/Auth/IAccountTokenProvider.cs`
- Create: `$DST/src/Mpt.Extensions.Sdk/Auth/AccountTokenProvider.cs`
- Test: `$DST/tests/Mpt.Extensions.Sdk.Tests/AccountTokenProviderTests.cs`

- [ ] **Step 1: Write the failing test (uses a stub `HttpMessageHandler`)**

Create `$DST/tests/Mpt.Extensions.Sdk.Tests/AccountTokenProviderTests.cs`:
```csharp
using System.Net;
using System.Text;
using System.Text.Json;
using Mpt.Extensions.Sdk.Auth;

namespace Mpt.Extensions.Sdk.Tests;

public class AccountTokenProviderTests
{
    private sealed class StubHandler : HttpMessageHandler
    {
        public int Calls;
        public Func<HttpRequestMessage, string> TokenFor = _ => "tok";
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request, CancellationToken ct)
        {
            Calls++;
            var json = JsonSerializer.Serialize(new { token = TokenFor(request) });
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(json, Encoding.UTF8, "application/json"),
            });
        }
    }

    private static string Jwt(long expUnix)
    {
        static string B64(byte[] b) => Convert.ToBase64String(b).TrimEnd('=').Replace('+','-').Replace('/','_');
        var body = B64(JsonSerializer.SerializeToUtf8Bytes(new Dictionary<string, object> { ["exp"] = expUnix }));
        return $"{B64(Encoding.UTF8.GetBytes("{}"))}.{body}.sig";
    }

    private static AccountTokenProvider Make(StubHandler handler)
    {
        var http = new HttpClient(handler) { BaseAddress = new Uri("https://api.example/") };
        return new AccountTokenProvider(http, extensionApiKey: "idt:EXT:key");
    }

    [Fact]
    public async Task GetTokenAsync_mints_then_caches_for_same_account()
    {
        var handler = new StubHandler { TokenFor = _ => Jwt(DateTimeOffset.UtcNow.AddHours(1).ToUnixTimeSeconds()) };
        var provider = Make(handler);

        var t1 = await provider.GetTokenAsync("ACC-1");
        var t2 = await provider.GetTokenAsync("ACC-1");

        Assert.Equal(t1, t2);
        Assert.Equal(1, handler.Calls); // second call served from cache
    }

    [Fact]
    public async Task GetTokenAsync_refreshes_when_token_near_expiry()
    {
        var handler = new StubHandler { TokenFor = _ => Jwt(DateTimeOffset.UtcNow.AddSeconds(10).ToUnixTimeSeconds()) };
        var provider = Make(handler);

        await provider.GetTokenAsync("ACC-1");
        await provider.GetTokenAsync("ACC-1"); // within leeway -> re-mint

        Assert.Equal(2, handler.Calls);
    }

    [Fact]
    public async Task GetTokenAsync_calls_installations_token_endpoint_with_account_id()
    {
        string? path = null;
        var handler = new StubHandler();
        handler.TokenFor = req => { path = req.RequestUri!.PathAndQuery; return Jwt(DateTimeOffset.UtcNow.AddHours(1).ToUnixTimeSeconds()); };

        await Make(handler).GetTokenAsync("ACC-42");

        Assert.Equal("/public/v1/integration/installations/token?account.id=ACC-42", path);
    }
}
```

- [ ] **Step 2: Run it — expect failure**

```bash
dotnet test --filter FullyQualifiedName~AccountTokenProviderTests
```
Expected: FAIL — types do not exist.

- [ ] **Step 3: Implement the interface**

Create `$DST/src/Mpt.Extensions.Sdk/Auth/IAccountTokenProvider.cs`:
```csharp
namespace Mpt.Extensions.Sdk.Auth;

/// <summary>Supplies a valid account-scoped bearer token for Marketplace calls.</summary>
public interface IAccountTokenProvider
{
    Task<string> GetTokenAsync(string accountId, CancellationToken ct = default);
}
```

- [ ] **Step 4: Implement the provider**

Create `$DST/src/Mpt.Extensions.Sdk/Auth/AccountTokenProvider.cs`:
```csharp
using System.Collections.Concurrent;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;

namespace Mpt.Extensions.Sdk.Auth;

/// <summary>
/// Mints per-account tokens via <c>POST /public/v1/integration/installations/token?account.id={id}</c>
/// using the extension API key, caches them, and refreshes within a leeway window. Minting is
/// serialized per account so concurrent requests for the same account mint once.
/// </summary>
public sealed class AccountTokenProvider : IAccountTokenProvider
{
    private static readonly TimeSpan RefreshLeeway = TimeSpan.FromSeconds(60);

    private readonly HttpClient _http;
    private readonly string _extensionApiKey;
    private readonly ConcurrentDictionary<string, (string Token, DateTimeOffset ExpiresAt)> _cache = new();
    private readonly ConcurrentDictionary<string, SemaphoreSlim> _locks = new();

    public AccountTokenProvider(HttpClient http, string extensionApiKey)
    {
        _http = http;
        _extensionApiKey = extensionApiKey;
    }

    public async Task<string> GetTokenAsync(string accountId, CancellationToken ct = default)
    {
        if (TryGetFresh(accountId, out var cached))
            return cached;

        var gate = _locks.GetOrAdd(accountId, _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(ct);
        try
        {
            if (TryGetFresh(accountId, out cached))
                return cached;

            var (token, expiresAt) = await MintAsync(accountId, ct);
            _cache[accountId] = (token, expiresAt);
            return token;
        }
        finally { gate.Release(); }
    }

    private bool TryGetFresh(string accountId, out string token)
    {
        if (_cache.TryGetValue(accountId, out var e) && e.ExpiresAt - RefreshLeeway > DateTimeOffset.UtcNow)
        {
            token = e.Token;
            return true;
        }
        token = "";
        return false;
    }

    private async Task<(string Token, DateTimeOffset ExpiresAt)> MintAsync(string accountId, CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post,
            $"/public/v1/integration/installations/token?account.id={Uri.EscapeDataString(accountId)}");
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _extensionApiKey);

        using var res = await _http.SendAsync(req, ct);
        res.EnsureSuccessStatusCode();

        var body = await res.Content.ReadFromJsonAsync<TokenResponse>(cancellationToken: ct)
            ?? throw new InvalidOperationException("Token endpoint returned an empty body.");
        if (string.IsNullOrEmpty(body.Token))
            throw new InvalidOperationException("Token endpoint returned no token.");

        var expiresAt = SoftwareOneJwt.ParseClaims(body.Token).ExpiresAt
            ?? DateTimeOffset.UtcNow.AddMinutes(5);
        return (body.Token, expiresAt);
    }

    private sealed record TokenResponse(string Token);
}
```
Note: `ReadFromJsonAsync<TokenResponse>` uses Web defaults (camelCase), so the JSON `{"token":"..."}` maps to `Token`.

- [ ] **Step 5: Run the tests — expect pass**

```bash
dotnet test --filter FullyQualifiedName~AccountTokenProviderTests
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: account-scoped token provider (mint/cache/refresh)"
```

### Task D4: Direct account-scoped Marketplace client

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk/Marketplace/HttpMarketplaceClient.cs`
- Test: `$DST/tests/Mpt.Extensions.Sdk.Tests/HttpMarketplaceClientTests.cs`

- [ ] **Step 1: Write the failing test**

Create `$DST/tests/Mpt.Extensions.Sdk.Tests/HttpMarketplaceClientTests.cs`:
```csharp
using System.Net;
using System.Text;
using System.Text.Json.Serialization;
using Mpt.Extensions.Sdk.Auth;
using Mpt.Extensions.Sdk.Marketplace;
using Mpt.Extensions.Sdk.Serialization;

namespace Mpt.Extensions.Sdk.Tests;

public class HttpMarketplaceClientTests
{
    private sealed class CapturingHandler : HttpMessageHandler
    {
        public HttpRequestMessage? Last;
        public string ResponseJson = "{}";
        public HttpStatusCode Status = HttpStatusCode.OK;
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Last = request;
            return Task.FromResult(new HttpResponseMessage(Status)
            {
                Content = new StringContent(ResponseJson, Encoding.UTF8, "application/json"),
            });
        }
    }

    private sealed class StubTokens : IAccountTokenProvider
    {
        public Task<string> GetTokenAsync(string accountId, CancellationToken ct = default) =>
            Task.FromResult($"token-for-{accountId}");
    }

    private sealed class Order
    {
        [JsonPropertyName("id")] public string Id { get; init; } = "";
    }

    private static HttpMarketplaceClient Make(CapturingHandler handler) =>
        new(new HttpClient(handler) { BaseAddress = new Uri("https://api.example/") },
            new StubTokens(), accountId: "ACC-1", MptJson.Default);

    [Fact]
    public async Task GetAsync_attaches_account_token_and_returns_typed_body()
    {
        var handler = new CapturingHandler { ResponseJson = "{\"id\":\"ORD-1\"}" };
        var order = await Make(handler).GetAsync<Order>("/commerce/orders/ORD-1");

        Assert.Equal("ORD-1", order.Id);
        Assert.Equal(HttpMethod.Get, handler.Last!.Method);
        Assert.Equal("/commerce/orders/ORD-1", handler.Last.RequestUri!.PathAndQuery);
        Assert.Equal("token-for-ACC-1", handler.Last.Headers.Authorization!.Parameter);
        Assert.Equal("Bearer", handler.Last.Headers.Authorization.Scheme);
    }

    [Fact]
    public async Task PutAsync_sends_body()
    {
        var handler = new CapturingHandler { ResponseJson = "{\"id\":\"ORD-1\"}" };
        await Make(handler).PutAsync<Order>("/commerce/orders/ORD-1", new { note = "x" });

        Assert.Equal(HttpMethod.Put, handler.Last!.Method);
        Assert.NotNull(handler.Last.Content);
    }

    [Fact]
    public async Task Non_success_throws_MarketplaceApiException_with_status_and_body()
    {
        var handler = new CapturingHandler { Status = HttpStatusCode.NotFound, ResponseJson = "{\"error\":\"nope\"}" };
        var ex = await Assert.ThrowsAsync<MarketplaceApiException>(
            () => Make(handler).GetAsync<Order>("/commerce/orders/ORD-X"));
        Assert.Equal(404, ex.StatusCode);
        Assert.Contains("nope", ex.Message);
    }
}
```
Note: confirm `MarketplaceApiException` exposes an `int StatusCode` and the body in `Message` (it was ported in Task B2; if the property name differs, align the test with the ported type rather than inventing a new one).

- [ ] **Step 2: Run it — expect failure**

```bash
dotnet test --filter FullyQualifiedName~HttpMarketplaceClientTests
```
Expected: FAIL — `HttpMarketplaceClient` does not exist.

- [ ] **Step 3: Implement**

Create `$DST/src/Mpt.Extensions.Sdk/Marketplace/HttpMarketplaceClient.cs`:
```csharp
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Mpt.Extensions.Sdk.Auth;

namespace Mpt.Extensions.Sdk.Marketplace;

/// <summary>
/// Calls the Marketplace API directly (over whatever transport the HttpClient is bound to —
/// plain HTTP locally, Ziti on the platform), attaching a fresh account-scoped token per request.
/// Generic: the caller chooses the model type <typeparamref name="T"/>.
/// </summary>
public sealed class HttpMarketplaceClient : IMarketplaceClient
{
    private readonly HttpClient _http;
    private readonly IAccountTokenProvider _tokens;
    private readonly string _accountId;
    private readonly JsonSerializerOptions _json;

    public HttpMarketplaceClient(HttpClient http, IAccountTokenProvider tokens, string accountId,
        JsonSerializerOptions json)
    {
        _http = http;
        _tokens = tokens;
        _accountId = accountId;
        _json = json;
    }

    public Task<T> GetAsync<T>(string path, CancellationToken ct = default) =>
        SendAsync<T>(HttpMethod.Get, path, body: null, ct);

    public Task<T> PostAsync<T>(string path, object? body, CancellationToken ct = default) =>
        SendAsync<T>(HttpMethod.Post, path, body, ct);

    public Task<T> PutAsync<T>(string path, object? body, CancellationToken ct = default) =>
        SendAsync<T>(HttpMethod.Put, path, body, ct);

    private async Task<T> SendAsync<T>(HttpMethod method, string path, object? body, CancellationToken ct)
    {
        using var req = new HttpRequestMessage(method, path);
        var token = await _tokens.GetTokenAsync(_accountId, ct);
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        if (body is not null)
            req.Content = new StringContent(JsonSerializer.Serialize(body, _json), Encoding.UTF8, "application/json");

        using var res = await _http.SendAsync(req, ct);
        var payload = await res.Content.ReadAsStringAsync(ct);

        if (!res.IsSuccessStatusCode)
            throw new MarketplaceApiException((int)res.StatusCode, payload);

        if (string.IsNullOrWhiteSpace(payload))
            throw new MarketplaceApiException((int)res.StatusCode, "Marketplace returned an empty success body.");

        return JsonSerializer.Deserialize<T>(payload, _json)
            ?? throw new MarketplaceApiException((int)res.StatusCode, "Marketplace returned a null body.");
    }
}
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
dotnet test --filter FullyQualifiedName~HttpMarketplaceClientTests
```
Expected: PASS. If `MarketplaceApiException`'s constructor/shape differs from `(int, string)`, adapt this implementation to the ported type (do not change the ported exception).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: direct account-scoped HttpMarketplaceClient (generic)"
```

### Task D5: Typed runtime options

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk/Hosting/ExtensionOptions.cs`
- Test: `$DST/tests/Mpt.Extensions.Sdk.Tests/ExtensionOptionsTests.cs`

- [ ] **Step 1: Write the failing test**

Create `$DST/tests/Mpt.Extensions.Sdk.Tests/ExtensionOptionsTests.cs`:
```csharp
using Microsoft.Extensions.Configuration;
using Mpt.Extensions.Sdk.Hosting;

namespace Mpt.Extensions.Sdk.Tests;

public class ExtensionOptionsTests
{
    [Fact]
    public void FromConfiguration_reads_sdk_env_keys()
    {
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["SDK_EXTENSION_ID"] = "EXT-5034-5001",
            ["SDK_EXTENSION_API_KEY"] = "idt:EXT-5034-5001:secret",
            ["SDK_EXTENSION_URL"] = "https://api.s1.show",
            ["MPT_API_BASE_URL"] = "https://api.s1.show/public/v1",
            ["SDK_IDENTITY_FILE_PATH"] = "./identity/identity.json",
        }).Build();

        var o = ExtensionOptions.FromConfiguration(config);

        Assert.Equal("EXT-5034-5001", o.ExtensionId);
        Assert.Equal("EXT-5034-5001", o.ExternalId); // defaults to extension id when not set
        Assert.Equal("idt:EXT-5034-5001:secret", o.ExtensionApiKey);
        Assert.Equal("https://api.s1.show", o.PlatformUrl);
        Assert.Equal("https://api.s1.show/public/v1", o.MarketplaceApiBaseUrl);
        Assert.Equal("./identity/identity.json", o.IdentityFilePath);
    }

    [Fact]
    public void ExternalId_uses_explicit_value_when_present()
    {
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["SDK_EXTENSION_ID"] = "EXT-1",
            ["SDK_EXTENSION_EXTERNAL_ID"] = "EXT-EXTERNAL",
        }).Build();

        Assert.Equal("EXT-EXTERNAL", ExtensionOptions.FromConfiguration(config).ExternalId);
    }
}
```

- [ ] **Step 2: Run it — expect failure**

```bash
dotnet test --filter FullyQualifiedName~ExtensionOptionsTests
```
Expected: FAIL — `ExtensionOptions` does not exist.

- [ ] **Step 3: Implement (replaces the old bridge-oriented `HostOptions`)**

Create `$DST/src/Mpt.Extensions.Sdk/Hosting/ExtensionOptions.cs`:
```csharp
using Microsoft.Extensions.Configuration;

namespace Mpt.Extensions.Sdk.Hosting;

/// <summary>Runtime options resolved from environment/configuration when the host is built.</summary>
public sealed class ExtensionOptions
{
    public required string ExtensionId { get; init; }
    public required string ExternalId { get; init; }
    public string? ExtensionApiKey { get; init; }
    public string? PlatformUrl { get; init; }
    public string? MarketplaceApiBaseUrl { get; init; }
    public string IdentityFilePath { get; init; } = "identity/identity.json";

    /// <summary>Platform version reported during registration (from meta/config).</summary>
    public string Version { get; init; } = "0.0.0";

    public static ExtensionOptions FromConfiguration(IConfiguration config)
    {
        var extensionId = config["SDK_EXTENSION_ID"] ?? "";
        return new ExtensionOptions
        {
            ExtensionId = extensionId,
            ExternalId = config["SDK_EXTENSION_EXTERNAL_ID"] ?? extensionId,
            ExtensionApiKey = config["SDK_EXTENSION_API_KEY"],
            PlatformUrl = config["SDK_EXTENSION_URL"],
            MarketplaceApiBaseUrl = config["MPT_API_BASE_URL"],
            IdentityFilePath = config["SDK_IDENTITY_FILE_PATH"] ?? "identity/identity.json",
            Version = config["SDK_EXTENSION_VERSION"] ?? "0.0.0",
        };
    }
}
```

- [ ] **Step 4: Run the test — expect pass**

```bash
dotnet test --filter FullyQualifiedName~ExtensionOptionsTests
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: typed ExtensionOptions from configuration"
```

### Task D6: Port + rewire the host pipeline (native auth, native Marketplace client)

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk/Hosting/ExtensionEndpoints.cs` (ported, rewired)
- Create: `$DST/src/Mpt.Extensions.Sdk/Hosting/ExtensionHostBuilder.cs` (ported, rewired)
- Modify (restore): `$DST/tests/Mpt.Extensions.Sdk.Tests/HostIntegrationTests.cs`

- [ ] **Step 1: Port the two Hosting files**

```bash
SRC='C:/repos/mpt-extension-dotnet-sdk/src/Mpt.Extensions.Sdk/Hosting'
DST='C:/repos/mpt-extension-sdk-dotnet/src/Mpt.Extensions.Sdk/Hosting'
cp "$SRC/ExtensionEndpoints.cs" "$DST/ExtensionEndpoints.cs"
cp "$SRC/ExtensionHostBuilder.cs" "$DST/ExtensionHostBuilder.cs"
```

- [ ] **Step 2: Rewire `ExtensionEndpoints.cs` — replace bridge auth/egress with native equivalents**

Make these exact edits in `$DST/src/Mpt.Extensions.Sdk/Hosting/ExtensionEndpoints.cs`:

(a) Replace the `ParseAuth` method body so it uses the real Bearer JWT instead of the `X-Mpt-Auth` header:
```csharp
    private static AuthContext ParseAuth(HttpContext http) =>
        new RequestAuthenticator().Authenticate(http);
```
Add `using Mpt.Extensions.Sdk.Auth;` if not already present.

(b) Remove the bridge-token gate: delete the `Unauthorized(...)` call in `RunGuarded` and the `Unauthorized` method, and drop the `options.BridgeToken` usage. Authentication failures now surface as `UnauthorizedAccessException` from `ParseAuth`; catch them in `RunGuarded` and return 401:
```csharp
        try
        {
            var services = new HandlerServices(
                scope.ServiceProvider, NewClient(httpFactory, http), logger);
            return await body(services, http);
        }
        catch (UnauthorizedAccessException ex)
        {
            logger.LogWarning(ex, "{Label} request to {Path} failed authentication", label, http.Request.Path);
            return Error(StatusCodes.Status401Unauthorized, "unauthorized", ex.Message);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "{Label} handler for {Path} failed", label, http.Request.Path);
            return Error(StatusCodes.Status500InternalServerError, "handler_failed", ex.Message);
        }
```
Important: `ParseAuth` is called inside each route `body` (e.g. `route.Invoke(evt, ParseAuth(h), ...)`), so the `UnauthorizedAccessException` is thrown within the `try` and mapped to 401. Keep it that way.

(c) Replace `NewClient` (which built the bridge `EgressMarketplaceClient` from the `X-Mpt-Egress-Session` header) with one that builds the native account-scoped client. It needs the authenticated account id, the account-token provider, the Marketplace base URL, and the JSON options — all resolved from DI. Change the per-request client construction so it happens **after** auth (it needs the account id). Concretely:
  - Delete the `NewClient(IHttpClientFactory, HttpContext)` method and the `EgressClientName` egress constant usage for client creation.
  - Build `HandlerServices` lazily with a factory that, given the parsed `AuthContext`, returns an `IMarketplaceClient`:
```csharp
        var services = new HandlerServices(
            scope.ServiceProvider,
            marketplaceFor: auth => new HttpMarketplaceClient(
                httpFactory.CreateClient(MarketplaceClientName),
                scope.ServiceProvider.GetRequiredService<IAccountTokenProvider>(),
                auth.AccountId,
                scope.ServiceProvider.GetRequiredService<JsonSerializerOptions>()),
            logger);
```
  This requires `HandlerServices` to support resolving the Marketplace client from the auth context. See Step 3 for the `HandlerServices` change. Add `internal const string MarketplaceClientName = "mpt-marketplace";` and `using System.Text.Json;`, `using Mpt.Extensions.Sdk.Marketplace;`.

(d) Keep `/__health` and `/__manifest`, the correlation-id log scope (`x-request-id`/`mpt-task-id`), route mapping, body handling, and the error envelope unchanged.

- [ ] **Step 3: Update `HandlerServices` so the Marketplace client is built from the auth context**

The ported `HandlerServices` currently takes a concrete `IMarketplaceClient`. The native flow needs the account id (from auth) to build the client. Open `$DST/src/Mpt.Extensions.Sdk/Contexts/HandlerServices.cs` and the context types (`EventContext`, `ApiContext`) and adjust so the per-request `IMarketplaceClient` is created once the `AuthContext` is known.

Minimal, low-churn approach: give `HandlerServices` a constructor overload taking a `Func<AuthContext, IMarketplaceClient> marketplaceFor` plus the parsed `AuthContext`, and have `Marketplace` resolve lazily:
```csharp
using Microsoft.Extensions.Logging;
using Mpt.Extensions.Sdk.Auth;
using Mpt.Extensions.Sdk.Marketplace;

namespace Mpt.Extensions.Sdk.Contexts;

public sealed class HandlerServices
{
    private readonly Lazy<IMarketplaceClient> _marketplace;

    public HandlerServices(IServiceProvider services, IMarketplaceClient marketplace, ILogger logger)
        : this(services, _ => marketplace, auth: new AuthContext(), logger) { }

    public HandlerServices(IServiceProvider services, Func<AuthContext, IMarketplaceClient> marketplaceFor,
        AuthContext auth, ILogger logger)
    {
        Services = services;
        Logger = logger;
        _marketplace = new Lazy<IMarketplaceClient>(() => marketplaceFor(auth));
    }

    public IServiceProvider Services { get; }
    public IMarketplaceClient Marketplace => _marketplace.Value;
    public ILogger Logger { get; }
}
```
Then in `ExtensionEndpoints.RunGuarded`, parse auth first and pass it in. Adjust the route bodies so they receive the already-parsed `AuthContext` (parse once per request, not once per `ParseAuth` call). If the ported dispatch signature passes `auth` into the invoker, thread the single parsed `AuthContext` through both `HandlerServices` and the invoker. Keep the change surface minimal and re-run the build after.

- [ ] **Step 4: Rewire `ExtensionHostBuilder.cs` — register native services, drop egress defaults**

Edit `$DST/src/Mpt.Extensions.Sdk/Hosting/ExtensionHostBuilder.cs`:
  - Remove `DefaultEgressUrl` and the `MPT_EGRESS_URL`/`MPT_BRIDGE_TOKEN` `HostOptions` wiring.
  - Resolve `ExtensionOptions.FromConfiguration(builder.Configuration)` and register it as a singleton.
  - Register the shared JSON options: `builder.Services.AddSingleton(MptJson.Default);` (consumers can replace this registration to add converters for platform contracts).
  - Register the account-token provider as a singleton backed by a named HttpClient pointed at the platform URL:
```csharp
builder.Services.AddHttpClient("mpt-tokens", (sp, c) =>
{
    var o = sp.GetRequiredService<ExtensionOptions>();
    c.BaseAddress = new Uri(o.PlatformUrl ?? "http://localhost");
});
builder.Services.AddSingleton<IAccountTokenProvider>(sp =>
{
    var o = sp.GetRequiredService<ExtensionOptions>();
    var http = sp.GetRequiredService<IHttpClientFactory>().CreateClient("mpt-tokens");
    return new AccountTokenProvider(http, o.ExtensionApiKey ?? "");
});
```
  - Register the named Marketplace HttpClient (`ExtensionEndpoints.MarketplaceClientName`) pointed at `MarketplaceApiBaseUrl`, with a 2-minute pooled connection lifetime (as the old egress client had):
```csharp
builder.Services.AddHttpClient(ExtensionEndpoints.MarketplaceClientName, (sp, c) =>
{
    var o = sp.GetRequiredService<ExtensionOptions>();
    c.BaseAddress = new Uri(o.MarketplaceApiBaseUrl ?? "http://localhost");
}).ConfigurePrimaryHttpMessageHandler(() =>
    new SocketsHttpHandler { PooledConnectionLifetime = TimeSpan.FromMinutes(2) });
```
  - Keep the generated-registry vs reflection-discovery branch and `AddStatic` exactly as ported, but pass the rewired `HostOptions`/options object through (or drop `HostOptions` entirely if no longer needed by `ExtensionEndpoints.Map*`). Ensure `Map`/`MapGenerated` no longer require a `BridgeToken`.

- [ ] **Step 5: Restore and rewire `HostIntegrationTests`**

```bash
DST='C:/repos/mpt-extension-sdk-dotnet/tests/Mpt.Extensions.Sdk.Tests'
mv "$DST/HostIntegrationTests.cs.pending" "$DST/HostIntegrationTests.cs"
```
Then overwrite `$DST/tests/Mpt.Extensions.Sdk.Tests/HostIntegrationTests.cs` to use a real Bearer JWT and drop the bridge-token/egress-session/`X-Mpt-Auth` headers:
```csharp
using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Mpt.Extensions.Sdk.Attributes;
using Mpt.Extensions.Sdk.Contexts;
using Mpt.Extensions.Sdk.Events;
using Mpt.Extensions.Sdk.Hosting;

namespace Mpt.Extensions.Sdk.Tests;

public class HostIntegrationTests
{
    public class TestHandlers
    {
        [EventHandler(Event = "order.created", Path = "/events/host-orders")]
        public Task<EventResponse> OnCreated(OrderContext ctx) =>
            Task.FromResult(ctx.OrderId == "ORD-1" ? EventResponse.Ok() : EventResponse.Cancel("unknown"));

        [ApiEndpoint("GET", "/host-me")]
        public Task<object> Me(ApiContext ctx) => Task.FromResult<object>(new { account = ctx.Auth.AccountId });
    }

    private static string Bearer(string accountId)
    {
        static string B64(byte[] b) => Convert.ToBase64String(b).TrimEnd('=').Replace('+','-').Replace('/','_');
        var body = B64(JsonSerializer.SerializeToUtf8Bytes(new Dictionary<string, object>
        {
            ["https://claims.softwareone.com/accountId"] = accountId,
            ["exp"] = DateTimeOffset.UtcNow.AddMinutes(10).ToUnixTimeSeconds(),
        }));
        return $"{B64(Encoding.UTF8.GetBytes("{}"))}.{body}.sig";
    }

    private static TestServer BuildServer()
    {
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        var app = ExtensionHostBuilder.Build(builder, typeof(TestHandlers).Assembly);
        app.Start();
        return (TestServer)app.Services.GetRequiredService<IServer>();
    }

    [Fact]
    public async Task Health_returns_ok()
    {
        using var server = BuildServer();
        var res = await server.CreateClient().GetAsync("/__health");
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
    }

    [Fact]
    public async Task Posting_event_with_valid_bearer_dispatches()
    {
        using var server = BuildServer();
        var client = server.CreateClient();
        client.DefaultRequestHeaders.Add("Authorization", $"Bearer {Bearer("ACC-1")}");
        var body = new StringContent("{\"id\":\"E1\",\"object\":{\"id\":\"ORD-1\"},\"details\":{}}",
            Encoding.UTF8, "application/json");

        var res = await client.PostAsync("/events/host-orders", body);
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
        Assert.Contains("\"response\":\"OK\"", await res.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task Event_without_bearer_returns_401()
    {
        using var server = BuildServer();
        var body = new StringContent("{\"id\":\"E1\",\"object\":{\"id\":\"ORD-1\"},\"details\":{}}",
            Encoding.UTF8, "application/json");
        var res = await server.CreateClient().PostAsync("/events/host-orders", body);
        Assert.Equal(HttpStatusCode.Unauthorized, res.StatusCode);
    }

    [Fact]
    public async Task Api_endpoint_reads_account_from_bearer()
    {
        using var server = BuildServer();
        var client = server.CreateClient();
        client.DefaultRequestHeaders.Add("Authorization", $"Bearer {Bearer("ACC-7")}");
        var res = await client.GetAsync("/host-me");
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
        Assert.Contains("ACC-7", await res.Content.ReadAsStringAsync());
    }
}
```

- [ ] **Step 6: Build and run the full suite**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet test
```
Expected: all tests pass, including the rewired `HostIntegrationTests`. Iterate on the Step 2–4 edits until green (the rewiring is the most involved change; expect a few compile fixes around `HandlerServices`/`ParseAuth` threading).

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: native host pipeline (Bearer JWT auth + account-scoped Marketplace client)"
```

### Task D7: Identity store

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk/Registration/IdentityStore.cs`
- Test: `$DST/tests/Mpt.Extensions.Sdk.Tests/IdentityStoreTests.cs`

- [ ] **Step 1: Write the failing test**

Create `$DST/tests/Mpt.Extensions.Sdk.Tests/IdentityStoreTests.cs`:
```csharp
using System.Text.Json;
using Mpt.Extensions.Sdk.Registration;

namespace Mpt.Extensions.Sdk.Tests;

public class IdentityStoreTests
{
    [Fact]
    public void Load_returns_empty_when_file_absent()
    {
        var store = new IdentityStore(Path.Combine(Path.GetTempPath(), $"missing-{Guid.NewGuid():N}.json"));
        Assert.Null(store.Load());
    }

    [Fact]
    public void Save_then_Load_round_trips_and_creates_directory()
    {
        var dir = Path.Combine(Path.GetTempPath(), $"id-{Guid.NewGuid():N}");
        var path = Path.Combine(dir, "identity.json");
        var store = new IdentityStore(path);

        using var doc = JsonDocument.Parse("{\"mrok\":{\"extension\":\"EXT-1\"}}");
        store.Save(doc.RootElement);

        var loaded = store.Load();
        Assert.NotNull(loaded);
        Assert.Equal("EXT-1", loaded!.Value.GetProperty("mrok").GetProperty("extension").GetString());
    }

    [Fact]
    public void MatchesExtension_is_case_insensitive()
    {
        var dir = Path.Combine(Path.GetTempPath(), $"id-{Guid.NewGuid():N}");
        var store = new IdentityStore(Path.Combine(dir, "identity.json"));
        using var doc = JsonDocument.Parse("{\"mrok\":{\"extension\":\"EXT-1\"}}");
        store.Save(doc.RootElement);

        Assert.True(store.MatchesExtension("ext-1"));
        Assert.False(store.MatchesExtension("EXT-2"));
    }
}
```

- [ ] **Step 2: Run it — expect failure**

```bash
dotnet test --filter FullyQualifiedName~IdentityStoreTests
```
Expected: FAIL — `IdentityStore` does not exist.

- [ ] **Step 3: Implement**

Create `$DST/src/Mpt.Extensions.Sdk/Registration/IdentityStore.cs`:
```csharp
using System.Text.Json;

namespace Mpt.Extensions.Sdk.Registration;

/// <summary>Reads/writes the persisted OpenZiti identity (the platform's channel.identity).</summary>
public sealed class IdentityStore
{
    private readonly string _path;

    public IdentityStore(string path) => _path = path;

    public JsonElement? Load()
    {
        if (!File.Exists(_path))
            return null;
        using var doc = JsonDocument.Parse(File.ReadAllText(_path));
        return doc.RootElement.Clone();
    }

    public void Save(JsonElement identity)
    {
        var dir = Path.GetDirectoryName(_path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);
        File.WriteAllText(_path, JsonSerializer.Serialize(identity));
    }

    /// <summary>True when the persisted identity's <c>mrok.extension</c> matches (case-insensitive).</summary>
    public bool MatchesExtension(string extensionId)
    {
        var id = Load();
        if (id is null)
            return false;
        if (!id.Value.TryGetProperty("mrok", out var mrok) ||
            !mrok.TryGetProperty("extension", out var ext))
            return false;
        return string.Equals(ext.GetString(), extensionId, StringComparison.OrdinalIgnoreCase);
    }
}
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
dotnet test --filter FullyQualifiedName~IdentityStoreTests
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: identity store (persist platform channel.identity)"
```

### Task D8: Meta builder (manifest → registration meta block)

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk/Registration/MetaBuilder.cs`
- Test: `$DST/tests/Mpt.Extensions.Sdk.Tests/MetaBuilderTests.cs`

> Read the ported `Manifest/ExtensionManifest.cs` and `Manifest/RouteDescriptor.cs` first to use their real property names. The test/impl below assume `manifest.Events` items expose `Event` (string), `Path` (string), `Condition` (string?), and a task flag. Align names to the actual ported types.

- [ ] **Step 1: Write the failing test**

Create `$DST/tests/Mpt.Extensions.Sdk.Tests/MetaBuilderTests.cs`:
```csharp
using System.Text.Json;
using Mpt.Extensions.Sdk.Manifest;
using Mpt.Extensions.Sdk.Registration;

namespace Mpt.Extensions.Sdk.Tests;

public class MetaBuilderTests
{
    [Fact]
    public void Build_emits_contract_version_and_event_entries()
    {
        // Build a manifest with one event route using the real ExtensionManifest API.
        var manifest = SampleManifest.WithOneEvent(
            eventName: "platform.catalog.productItem.created",
            path: "/events/platform-catalog-productitem-created",
            condition: "eq(product.id,PRD-1)",
            isTask: false);

        var meta = MetaBuilder.Build(manifest);
        var json = JsonSerializer.SerializeToElement(meta, MetaBuilder.JsonOptions);

        Assert.Equal("1", json.GetProperty("contractVersion").GetString());
        var evt = json.GetProperty("events")[0];
        Assert.Equal("platform.catalog.productItem.created", evt.GetProperty("event").GetString());
        Assert.Equal("/events/platform-catalog-productitem-created", evt.GetProperty("path").GetString());
        Assert.Equal("eq(product.id,PRD-1)", evt.GetProperty("condition").GetString());
        Assert.False(evt.GetProperty("task").GetBoolean());
        Assert.Equal(0, json.GetProperty("apiEndpoints").GetArrayLength());
    }
}
```
Add a small helper `SampleManifest.WithOneEvent(...)` in the test project that constructs an `ExtensionManifest` with one event route using the ported type's actual constructor/add API. (Inspect `ExtensionManifest`/`RouteDescriptor` to write this — do not guess.)

- [ ] **Step 2: Run it — expect failure**

```bash
dotnet test --filter FullyQualifiedName~MetaBuilderTests
```
Expected: FAIL — `MetaBuilder` does not exist.

- [ ] **Step 3: Implement**

Create `$DST/src/Mpt.Extensions.Sdk/Registration/MetaBuilder.cs` (map the ported manifest's real property names into the wire shape captured from the POC):
```csharp
using System.Text.Json;
using System.Text.Json.Serialization;
using Mpt.Extensions.Sdk.Manifest;

namespace Mpt.Extensions.Sdk.Registration;

/// <summary>The registration <c>meta</c> block (basis for meta.yaml), per the platform wire contract.</summary>
public sealed class MetaConfig
{
    [JsonPropertyName("contractVersion")] public string ContractVersion { get; init; } = "1";
    [JsonPropertyName("events")] public List<MetaEvent> Events { get; init; } = new();
    [JsonPropertyName("apiEndpoints")] public List<MetaApiEndpoint> ApiEndpoints { get; init; } = new();
    [JsonPropertyName("schedules")] public List<object> Schedules { get; init; } = new();
    [JsonPropertyName("plugs")] public List<object> Plugs { get; init; } = new();
}

public sealed class MetaEvent
{
    [JsonPropertyName("event")] public required string Event { get; init; }
    [JsonPropertyName("path")] public required string Path { get; init; }
    [JsonPropertyName("condition")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Condition { get; init; }
    [JsonPropertyName("task")] public bool Task { get; init; }
}

public sealed class MetaApiEndpoint
{
    [JsonPropertyName("method")] public required string Method { get; init; }
    [JsonPropertyName("path")] public required string Path { get; init; }
}

public static class MetaBuilder
{
    public static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = false };

    public static MetaConfig Build(ExtensionManifest manifest)
    {
        var meta = new MetaConfig();
        foreach (var e in manifest.Events)
        {
            meta.Events.Add(new MetaEvent
            {
                // Align these accessors to the real ExtensionManifest event-route type.
                Event = e.Event,
                Path = e.Path,
                Condition = e.Condition,
                Task = e.DeliveryIsTask, // adjust to the real flag name
            });
        }
        foreach (var a in manifest.ApiEndpoints)
        {
            meta.ApiEndpoints.Add(new MetaApiEndpoint { Method = a.Method, Path = a.Path });
        }
        return meta;
    }
}
```
Adjust the property accessors (`e.Event`, `e.Path`, `e.Condition`, `e.DeliveryIsTask`, `a.Method`, `a.Path`) to match the ported `ExtensionManifest` exactly.

- [ ] **Step 4: Run the test — expect pass**

```bash
dotnet test --filter FullyQualifiedName~MetaBuilderTests
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: meta builder (manifest -> registration meta block)"
```

### Task D9: Registration service

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk/Registration/RegistrationPayload.cs`
- Create: `$DST/src/Mpt.Extensions.Sdk/Registration/RegistrationService.cs`
- Test: `$DST/tests/Mpt.Extensions.Sdk.Tests/RegistrationServiceTests.cs`

- [ ] **Step 1: Write the failing test**

Create `$DST/tests/Mpt.Extensions.Sdk.Tests/RegistrationServiceTests.cs`:
```csharp
using System.Net;
using System.Text;
using System.Text.Json;
using Mpt.Extensions.Sdk.Hosting;
using Mpt.Extensions.Sdk.Registration;

namespace Mpt.Extensions.Sdk.Tests;

public class RegistrationServiceTests
{
    private sealed class CapturingHandler : HttpMessageHandler
    {
        public HttpRequestMessage? Last;
        public string? LastBody;
        public string ResponseJson = "{}";
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Last = request;
            LastBody = request.Content is null ? null : await request.Content.ReadAsStringAsync(ct);
            return new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(ResponseJson, Encoding.UTF8, "application/json"),
            };
        }
    }

    private static (RegistrationService svc, CapturingHandler handler, string idPath) Make(string? existingIdentity = null)
    {
        var handler = new CapturingHandler();
        var http = new HttpClient(handler) { BaseAddress = new Uri("https://api.s1.show") };
        var idPath = Path.Combine(Path.GetTempPath(), $"reg-{Guid.NewGuid():N}", "identity.json");
        if (existingIdentity is not null)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(idPath)!);
            File.WriteAllText(idPath, existingIdentity);
        }
        var options = new ExtensionOptions
        {
            ExtensionId = "EXT-1", ExternalId = "EXT-1", ExtensionApiKey = "idt:EXT-1:key",
            PlatformUrl = "https://api.s1.show", IdentityFilePath = idPath, Version = "1.2.3",
        };
        return (new RegistrationService(http, options, new IdentityStore(idPath)), handler, idPath);
    }

    [Fact]
    public async Task Register_posts_to_instances_endpoint_with_bearer_and_persists_identity()
    {
        var (svc, handler, idPath) = Make();
        handler.ResponseJson = "{\"channel\":{\"identity\":{\"mrok\":{\"extension\":\"EXT-1\"}}}}";

        var meta = new MetaConfig();
        await svc.RegisterAsync(meta);

        Assert.Equal(HttpMethod.Post, handler.Last!.Method);
        Assert.Equal("/public/v1/integration/extensions/EXT-1/instances", handler.Last.RequestUri!.PathAndQuery);
        Assert.Equal("idt:EXT-1:key", handler.Last.Headers.Authorization!.Parameter);

        using var sent = JsonDocument.Parse(handler.LastBody!);
        Assert.Equal("EXT-1", sent.RootElement.GetProperty("externalId").GetString());
        Assert.Equal("1.2.3", sent.RootElement.GetProperty("version").GetString());
        Assert.True(sent.RootElement.TryGetProperty("channel", out _)); // fresh -> requests a channel

        Assert.True(File.Exists(idPath));
    }

    [Fact]
    public async Task Register_omits_channel_when_matching_identity_exists()
    {
        var (svc, handler, _) = Make(existingIdentity: "{\"mrok\":{\"extension\":\"EXT-1\"}}");
        handler.ResponseJson = "{}";

        await svc.RegisterAsync(new MetaConfig());

        using var sent = JsonDocument.Parse(handler.LastBody!);
        Assert.False(sent.RootElement.TryGetProperty("channel", out _)); // identity reused
    }
}
```

- [ ] **Step 2: Run it — expect failure**

```bash
dotnet test --filter FullyQualifiedName~RegistrationServiceTests
```
Expected: FAIL — types do not exist.

- [ ] **Step 3: Implement the payload DTO**

Create `$DST/src/Mpt.Extensions.Sdk/Registration/RegistrationPayload.cs`:
```csharp
using System.Text.Json.Serialization;

namespace Mpt.Extensions.Sdk.Registration;

internal sealed class RegistrationPayload
{
    [JsonPropertyName("externalId")] public required string ExternalId { get; init; }
    [JsonPropertyName("version")] public required string Version { get; init; }
    [JsonPropertyName("meta")] public required MetaConfig Meta { get; init; }

    [JsonPropertyName("channel")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public object? Channel { get; init; }
}
```

- [ ] **Step 4: Implement the service**

Create `$DST/src/Mpt.Extensions.Sdk/Registration/RegistrationService.cs`:
```csharp
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Mpt.Extensions.Sdk.Hosting;

namespace Mpt.Extensions.Sdk.Registration;

/// <summary>Registers the extension instance with the platform and persists the returned identity.</summary>
public sealed class RegistrationService
{
    private static readonly JsonSerializerOptions Json = new() { DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull };

    private readonly HttpClient _http;
    private readonly ExtensionOptions _options;
    private readonly IdentityStore _identity;

    public RegistrationService(HttpClient http, ExtensionOptions options, IdentityStore identity)
    {
        _http = http;
        _options = options;
        _identity = identity;
    }

    public async Task RegisterAsync(MetaConfig meta, CancellationToken ct = default)
    {
        var freshChannel = !_identity.MatchesExtension(_options.ExtensionId);
        var payload = new RegistrationPayload
        {
            ExternalId = _options.ExternalId,
            Version = _options.Version,
            Meta = meta,
            Channel = freshChannel ? new { } : null,
        };

        using var req = new HttpRequestMessage(HttpMethod.Post,
            $"/public/v1/integration/extensions/{_options.ExtensionId}/instances")
        {
            Content = new StringContent(JsonSerializer.Serialize(payload, Json), Encoding.UTF8, "application/json"),
        };
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _options.ExtensionApiKey ?? "");

        using var res = await _http.SendAsync(req, ct);
        var body = await res.Content.ReadAsStringAsync(ct);
        if (!res.IsSuccessStatusCode)
            throw new InvalidOperationException(
                $"Extension registration failed ({(int)res.StatusCode}): {body}");

        using var doc = JsonDocument.Parse(string.IsNullOrWhiteSpace(body) ? "{}" : body);
        if (doc.RootElement.TryGetProperty("channel", out var channel) &&
            channel.TryGetProperty("identity", out var identity) &&
            identity.ValueKind == JsonValueKind.Object)
        {
            _identity.Save(identity);
        }
    }
}
```

- [ ] **Step 5: Run the tests — expect pass**

```bash
dotnet test --filter FullyQualifiedName~RegistrationServiceTests
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: registration service (POST instances, persist identity)"
```

### Task D10: Registration hosted service + wire into the host builder

**Files:**
- Create: `$DST/src/Mpt.Extensions.Sdk/Registration/RegistrationHostedService.cs`
- Modify: `$DST/src/Mpt.Extensions.Sdk/Hosting/ExtensionHostBuilder.cs`
- Test: `$DST/tests/Mpt.Extensions.Sdk.Tests/RegistrationHostedServiceTests.cs`

- [ ] **Step 1: Write the failing test**

Create `$DST/tests/Mpt.Extensions.Sdk.Tests/RegistrationHostedServiceTests.cs`:
```csharp
using Mpt.Extensions.Sdk.Registration;

namespace Mpt.Extensions.Sdk.Tests;

public class RegistrationHostedServiceTests
{
    [Fact]
    public async Task StartAsync_does_nothing_in_local_mode()
    {
        var called = false;
        var svc = new RegistrationHostedService(
            register: _ => { called = true; return Task.CompletedTask; },
            platformMode: false);

        await svc.StartAsync(CancellationToken.None);

        Assert.False(called); // local mode skips registration (like uvicorn vs ziticorn)
    }

    [Fact]
    public async Task StartAsync_registers_in_platform_mode()
    {
        var called = false;
        var svc = new RegistrationHostedService(
            register: _ => { called = true; return Task.CompletedTask; },
            platformMode: true);

        await svc.StartAsync(CancellationToken.None);

        Assert.True(called);
    }
}
```

- [ ] **Step 2: Run it — expect failure**

```bash
dotnet test --filter FullyQualifiedName~RegistrationHostedServiceTests
```
Expected: FAIL — `RegistrationHostedService` does not exist.

- [ ] **Step 3: Implement**

Create `$DST/src/Mpt.Extensions.Sdk/Registration/RegistrationHostedService.cs`:
```csharp
using Microsoft.Extensions.Hosting;

namespace Mpt.Extensions.Sdk.Registration;

/// <summary>Runs instance registration on startup in platform mode; a no-op locally.</summary>
public sealed class RegistrationHostedService : IHostedService
{
    private readonly Func<CancellationToken, Task> _register;
    private readonly bool _platformMode;

    public RegistrationHostedService(Func<CancellationToken, Task> register, bool platformMode)
    {
        _register = register;
        _platformMode = platformMode;
    }

    public Task StartAsync(CancellationToken cancellationToken) =>
        _platformMode ? _register(cancellationToken) : Task.CompletedTask;

    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}
```

- [ ] **Step 4: Run the tests — expect pass**

```bash
dotnet test --filter FullyQualifiedName~RegistrationHostedServiceTests
```
Expected: PASS.

- [ ] **Step 5: Wire it into `ExtensionHostBuilder`**

In `$DST/src/Mpt.Extensions.Sdk/Hosting/ExtensionHostBuilder.cs`, after building the manifest (both the generated and reflection branches produce one), register the hosted service. Platform mode is on when an identity/platform URL is configured and `SDK_LOCAL` is not set; expose it as a simple flag:
```csharp
var platformMode = !string.Equals(builder.Configuration["SDK_MODE"], "local", StringComparison.OrdinalIgnoreCase)
    && !string.IsNullOrEmpty(builder.Configuration["SDK_EXTENSION_URL"]);

builder.Services.AddHostedService(sp =>
{
    var options = sp.GetRequiredService<ExtensionOptions>();
    var http = sp.GetRequiredService<IHttpClientFactory>().CreateClient("mpt-tokens");
    var meta = MetaBuilder.Build(currentManifest); // the ExtensionManifest used to map routes
    var registration = new RegistrationService(http, options, new IdentityStore(options.IdentityFilePath));
    return new RegistrationHostedService(ct => registration.RegisterAsync(meta, ct), platformMode);
});
```
Make sure `currentManifest` refers to the `ExtensionManifest` available in scope (the reflection branch has `manifest`; for the generated branch, build a `MetaConfig` from `GeneratedHandlerRegistry` via a small `MetaBuilder.FromGenerated()` overload, or reuse `ManifestJson.FromGenerated()` data). If the generated branch lacks a manifest object, add a `MetaBuilder.Build` overload that reads `GeneratedHandlerRegistry.Events`/`.ApiEndpoints`. Keep both branches registering the hosted service.

- [ ] **Step 6: Build and run the full suite**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet test
```
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: registration hosted service wired into host builder"
```

---

## Phase E — Local end-to-end smoke

### Task E1: Minimal sample extension that builds and serves locally

**Files:**
- Create: `$DST/samples/Sample.LocalExtension/Sample.LocalExtension.csproj`
- Create: `$DST/samples/Sample.LocalExtension/Program.cs`
- Create: `$DST/samples/Sample.LocalExtension/OrderHandlers.cs`
- Modify: `$DST/Mpt.Extensions.Sdk.slnx` (add the sample)

- [ ] **Step 1: Create the sample project**

Create `$DST/samples/Sample.LocalExtension/Sample.LocalExtension.csproj`:
```xml
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="..\..\src\Mpt.Extensions.Sdk\Mpt.Extensions.Sdk.csproj" />
  </ItemGroup>
</Project>
```

- [ ] **Step 2: Create the handler and program**

Create `$DST/samples/Sample.LocalExtension/OrderHandlers.cs`:
```csharp
using Mpt.Extensions.Sdk.Attributes;
using Mpt.Extensions.Sdk.Contexts;
using Mpt.Extensions.Sdk.Events;

namespace Sample.LocalExtension;

public class OrderHandlers
{
    [EventHandler(Event = "order.created", Path = "/events/order-created")]
    public Task<EventResponse> OnCreated(OrderContext ctx)
    {
        ctx.Logger.LogInformation("Received order {OrderId}", ctx.OrderId);
        return Task.FromResult(EventResponse.Ok());
    }
}
```

Create `$DST/samples/Sample.LocalExtension/Program.cs`:
```csharp
using Microsoft.AspNetCore.Builder;
using Mpt.Extensions.Sdk.Hosting;

var builder = WebApplication.CreateBuilder(args);
builder.Configuration["SDK_MODE"] = "local"; // skip registration/Ziti for the smoke test
var app = ExtensionHostBuilder.Build(builder);
app.Run();
```

- [ ] **Step 3: Add the sample to the solution**

Add this line inside a new `<Folder Name="/samples/">` element in `$DST/Mpt.Extensions.Sdk.slnx`:
```xml
  <Folder Name="/samples/">
    <Project Path="samples/Sample.LocalExtension/Sample.LocalExtension.csproj" />
  </Folder>
```

- [ ] **Step 4: Build the whole solution**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet build
```
Expected: `Build succeeded` for all projects including the sample.

- [ ] **Step 5: Run the sample and hit health + an event**

```bash
cd 'C:/repos/mpt-extension-sdk-dotnet'
dotnet run --project samples/Sample.LocalExtension --urls http://127.0.0.1:8900 &
sleep 5
curl -s http://127.0.0.1:8900/__health
echo
curl -s http://127.0.0.1:8900/__manifest
echo
# Event with a decode-only bearer (accountId claim); base64url of {"https://claims.softwareone.com/accountId":"ACC-1","exp":<future>}
```
Expected: `/__health` returns `{"status":"ok"}`; `/__manifest` lists the `order.created` route. Stop the background process afterward (`kill %1`). A 401 on the event without a bearer is expected and acceptable for this smoke test; the unit tests already cover the authenticated path.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "test: local sample extension end-to-end smoke"
```

---

## Self-review notes (already applied)

- **Spec coverage:** Registration (D7–D10), native ingress auth (D1–D2), account tokens (D3), direct generic Marketplace client (D4), configurable serialization (C1), meta block (D8), net8 retarget (A1/B), drop bridge (ports exclude `bridge/`, egress files removed in B2). Ziti transport and the Abstractions/Ziti package split are explicitly deferred to Plan 2; the POC port to Plan 3.
- **`meta.yaml` file:** Plan 1 generates the registration `meta` **object** (required for registration). Writing the `meta.yaml` **file** to disk (tooling/local inspection) is deferred — it needs a YAML serializer (e.g. YamlDotNet) and is not required for the platform handshake, which takes `meta` as JSON in the POST. Add it in Plan 2 alongside Ziti packaging if needed.
- **Adapt-to-ported-types reminders:** Tasks D6 and D8 depend on the exact shapes of the ported `HandlerServices`, `ExtensionManifest`, `RouteDescriptor`, and `MarketplaceApiException`. Each such step says to read the ported type and align names rather than guess — do that before writing the code in those steps.

---

## Execution handoff

After this plan is approved, Plans 2 (Ziti transport spike + package split) and 3 (product-hub-extension port) follow as separate documents.
