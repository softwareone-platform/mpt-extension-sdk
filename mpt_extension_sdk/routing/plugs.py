from dataclasses import dataclass
from pathlib import PurePosixPath

STATIC_PATH_PREFIX = "/static/"


def _normalize_static_path(path: str) -> str:
    """Return a plug asset path rooted under the public static route."""
    cleaned_path = path.strip()
    if not cleaned_path:
        raise ValueError("Plug static asset path cannot be empty")

    static_root = STATIC_PATH_PREFIX.removesuffix("/")
    if cleaned_path in {static_root, STATIC_PATH_PREFIX}:
        raise ValueError("Plug static asset path must include a file")

    if cleaned_path.startswith(STATIC_PATH_PREFIX):
        relative_path = cleaned_path.removeprefix(STATIC_PATH_PREFIX)
    else:
        relative_path = cleaned_path.lstrip("/")

    path_parts = PurePosixPath(relative_path).parts
    if not path_parts or _has_invalid_path_parts(path_parts):
        raise ValueError("Plug static asset path must stay under the static folder")

    return STATIC_PATH_PREFIX + PurePosixPath(*path_parts).as_posix()


def _has_invalid_path_parts(path_parts: tuple[str, ...]) -> bool:
    """Return whether a static asset path contains unsafe parts."""
    return bool({"", ".", ".."}.intersection(path_parts))


@dataclass(frozen=True)
class Plug:
    """UI plug metadata declared by an extension."""

    id: str
    name: str
    description: str
    socket: str
    href: str
    icon: str | None = None
    condition: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize static asset references."""
        self._validate_required_fields()
        object.__setattr__(self, "href", _normalize_static_path(self.href))
        if self.icon is not None:
            object.__setattr__(self, "icon", _normalize_static_path(self.icon))

    def _validate_required_fields(self) -> None:
        """Validate required plug fields."""
        required_fields = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "socket": self.socket,
            "href": self.href,
        }
        for field_name, field_value in required_fields.items():
            if not field_value.strip():
                raise ValueError(f"Plug {field_name} cannot be empty")
        if self.condition is not None and not self.condition.strip():
            raise ValueError("Plug condition cannot be empty")


@dataclass(frozen=True)
class ModalPlug:
    """Modal plug opened programmatically by id, never mounted on a socket.

    The frontend resolves modal plugs with ``useMPTModal().open('<plug-id>')``,
    so a modal plug declares no ``socket`` and never renders as a page action.
    """

    id: str
    name: str
    href: str
    description: str | None = None
    icon: str | None = None

    def __post_init__(self) -> None:
        """Validate fields and normalize static asset references."""
        self._validate_fields()
        object.__setattr__(self, "id", self.id.strip())
        object.__setattr__(self, "href", _normalize_static_path(self.href))
        if self.icon is not None:
            object.__setattr__(self, "icon", _normalize_static_path(self.icon))

    def _validate_fields(self) -> None:
        """Validate modal plug fields."""
        required_fields = {
            "id": self.id,
            "name": self.name,
            "href": self.href,
        }
        for field_name, field_value in required_fields.items():
            if not field_value.strip():
                raise ValueError(f"Modal plug {field_name} cannot be empty")
        if self.description is not None and not self.description.strip():
            raise ValueError("Modal plug description cannot be empty")


@dataclass(frozen=True)
class NavigationPlug:
    """Navigation-container plug that groups child plugs under a nested socket.

    A navigation container ships no bundle, so it has no ``href``. Its ``id``
    derives a nested socket (``<socket>.<id>``) that child plugs can target.
    """

    id: str
    name: str
    socket: str
    description: str | None = None
    icon: str | None = None

    def __post_init__(self) -> None:
        """Validate fields and normalize structural identifiers and the optional icon."""
        self._validate_fields()
        object.__setattr__(self, "id", self.id.strip())
        object.__setattr__(self, "socket", self.socket.strip())
        if self.icon is not None:
            object.__setattr__(self, "icon", _normalize_static_path(self.icon))

    @property
    def nested_socket(self) -> str:
        """Derived socket that child plugs target to mount under this container."""
        return f"{self.socket}.{self.id}"

    def _validate_fields(self) -> None:
        """Validate navigation plug fields."""
        required_fields = {
            "id": self.id,
            "name": self.name,
            "socket": self.socket,
        }
        for field_name, field_value in required_fields.items():
            if not field_value.strip():
                raise ValueError(f"Navigation plug {field_name} cannot be empty")
        if self.description is not None and not self.description.strip():
            raise ValueError("Navigation plug description cannot be empty")
