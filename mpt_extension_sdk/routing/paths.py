from starlette.routing import compile_path


class RoutePath:
    """Route path helpers that follow the parameter syntax of the FastAPI router."""

    @classmethod
    def parameter_names(cls, path: str) -> list[str]:
        """Return the path parameter names the FastAPI router resolves for a route path."""
        try:
            _, _, param_convertors = compile_path(path)
        except AssertionError as error:
            raise ValueError(f"Route '{path}' declares an unknown path convertor") from error
        return list(param_convertors)
