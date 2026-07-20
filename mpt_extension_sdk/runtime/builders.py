from dataclasses import dataclass, field

from mpt_extension_sdk.routing.models import BaseRouteDefinition, PlugRouteDefinition
from mpt_extension_sdk.routing.plugs import ModalPlug, NavigationPlug, Plug
from mpt_extension_sdk.runtime.models import MetaPlug

DeclaredPlug = Plug | NavigationPlug | ModalPlug


@dataclass(kw_only=True)
class PlugMetadataBuilder:
    """Build plug metadata from registered plug providers."""

    _plug_ids: set[str] = field(default_factory=set, init=False, repr=False)
    routes: list[BaseRouteDefinition]

    def build(self) -> list[MetaPlug]:
        """Build plug metadata."""
        self._plug_ids.clear()
        meta_plugs: list[MetaPlug] = []
        for raw_plug in self._iter_plugs():
            plug = self._validate_plug(raw_plug)
            meta_plugs.append(self._create_meta_plug(plug))
        return meta_plugs

    def _create_meta_plug(self, plug: DeclaredPlug) -> MetaPlug:
        """Create a runtime metadata plug from a declared plug.

        Navigation-container plugs carry no bundle, so their metadata has no `href`.
        Modal plugs are opened by id, so their metadata has no `socket`.
        """
        if isinstance(plug, NavigationPlug):
            return MetaPlug(
                id=plug.id,
                name=plug.name,
                description=plug.description,
                icon=plug.icon,
                socket=plug.socket,
            )
        if isinstance(plug, ModalPlug):
            return MetaPlug(
                id=plug.id,
                name=plug.name,
                description=plug.description,
                icon=plug.icon,
                href=plug.href,
            )
        return MetaPlug(
            id=plug.id,
            name=plug.name,
            description=plug.description,
            icon=plug.icon,
            socket=plug.socket,
            condition=plug.condition,
            href=plug.href,
        )

    def _iter_plugs(self) -> list[object]:
        """Return all plugs declared by registered plug providers."""
        plugs: list[object] = []
        for route in self.routes:
            if isinstance(route, PlugRouteDefinition):
                plugs.extend(route.callback())
        return plugs

    def _validate_plug(self, plug: object) -> DeclaredPlug:
        """Validate plug provider output."""
        if not isinstance(plug, DeclaredPlug):
            raise TypeError(
                "Plug providers must return Plug, NavigationPlug, or ModalPlug instances"
            )
        self._validate_unique_plug_id(plug)
        return plug

    def _validate_unique_plug_id(self, plug: DeclaredPlug) -> None:
        """Validate that a plug id has not already been declared."""
        if plug.id in self._plug_ids:
            raise ValueError(f"Plug id '{plug.id}' is already registered")
        self._plug_ids.add(plug.id)
