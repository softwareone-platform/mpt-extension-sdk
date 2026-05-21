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
