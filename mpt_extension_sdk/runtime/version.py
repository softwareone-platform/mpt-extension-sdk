from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("swo-runtime")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"


def get_version():
    """Get the current version of the package."""
    return __version__
