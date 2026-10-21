from starlette.routing import compile_path


class RoutePath:
    """Route path helpers that follow the parameter syntax of the FastAPI router."""

    @classmethod
    def normalize(cls, path: str) -> str:
        """Return the form of a route path used to compare it with other paths."""
        stripped_path = path.rstrip("/") or "/"
        path_format, parameter_names = cls._compile(stripped_path)
        for parameter_name in parameter_names:
            path_format = path_format.replace(f"{{{parameter_name}}}", "{}")
        return path_format

    @classmethod
    def parameter_names(cls, path: str) -> list[str]:
        """Return the path parameter names the FastAPI router resolves for a route path."""
        _, parameter_names = cls._compile(path)
        return parameter_names

    @classmethod
    def _compile(cls, path: str) -> tuple[str, list[str]]:
        try:
            _, path_format, param_convertors = compile_path(path)
        except AssertionError as error:
            raise ValueError(f"Route '{path}' declares an unknown path convertor") from error
        return path_format, list(param_convertors)
