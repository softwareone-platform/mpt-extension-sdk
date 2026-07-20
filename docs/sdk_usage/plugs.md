# UI Plugs

Use `PlugRouter` to declare widgets that MPT can register during extension
instance registration. Plug definitions are metadata only; the SDK does not
build or render frontend assets.

```python
from mpt_extension_sdk import ExtensionApp, Plug, PlugRouter

plug_router = PlugRouter()


@plug_router.register()
def register_plugs() -> list[Plug]:
    return [
        Plug(
            id="adobe",
            name="Adobe",
            description="Adobe widget",
            icon="adobe.png",
            socket="commerce.agreements.agreement",
            condition="eq(product.id,'PRD-1234-5677')",
            href="main-menu.js",
        )
    ]


ext_app = ExtensionApp(prefix="/")
ext_app.include_router(plug_router)
```

The `PlugRouter` instance named `plug_router` owns the `register_plugs`
provider until `ExtensionApp.include_router` attaches it to the extension app.

`href` and `icon` should be filenames or paths relative to the local `static/`
folder, such as `main-menu.js` or `images/icon.png`. The SDK normalizes them
under `/static/` in generated metadata, so `href="main-menu.js"` becomes
`/static/main-menu.js` and `icon="images/icon.png"` becomes
`/static/images/icon.png`. The `mpt-ext meta validate` command checks that every
referenced file exists locally.

## Nested navigation

Use `NavigationPlug` to declare a pure navigation grouping node. A navigation
container ships no bundle, so it has no `href`, and generated metadata omits the
`href` key for it. Its `id` derives a nested socket (`<socket>.<id>`), exposed
as `nested_socket`, under which child plugs mount:

```python
from mpt_extension_sdk import NavigationPlug, Plug, PlugRouter

plug_router = PlugRouter()


@plug_router.register()
def register_plugs() -> list[Plug | NavigationPlug]:
    learn_extensions = NavigationPlug(
        id="learn-extensions",
        name="Learn Extensions",
        socket="portal",
    )
    return [
        learn_extensions,
        Plug(
            id="guide",
            name="Guide",
            description="Extension guide",
            socket=learn_extensions.nested_socket,  # portal.learn-extensions
            href="guide.js",
        ),
        Plug(
            id="examples",
            name="Examples",
            description="Extension examples",
            socket=learn_extensions.nested_socket,
            href="examples.js",
        ),
    ]
```

`NavigationPlug` accepts an optional `description` and `icon`; the icon is
normalized under `/static/` like bundle plug assets. Passing an `href` to a
navigation container raises an error — declare a `Plug` instead when the entry
renders a bundle.

## Modal plugs (open-by-id)

Use `ModalPlug` for plugs that are never mounted on a socket and are opened
programmatically by id instead — confirmation dialogs, multi-step wizards, and
other ad-hoc modals resolved on the frontend with
`useMPTModal().open('<plug-id>')`:

```python
from mpt_extension_sdk import ModalPlug, PlugRouter

plug_router = PlugRouter()


@plug_router.register()
def register_plugs() -> list[ModalPlug]:
    return [
        ModalPlug(
            id="confirm-unsubscribe",
            name="Confirm Unsubscribe",
            description="Unsubscribe confirmation dialog",
            href="dialogs/confirm-unsubscribe.js",
        )
    ]
```

A modal plug declares no `socket`, and generated metadata omits the `socket`
key for it, so the plug never renders as a page action. `href` is required and
`description` / `icon` are optional; asset paths are normalized under
`/static/` like bundle plug assets. Passing a `socket` to a modal plug raises
an error — declare a `Plug` instead when the entry should mount on a platform
socket.
