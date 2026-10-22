import pytest

from mpt_extension_sdk.routing import (
    APIRouteDefinition,
    HTTPMethod,
    RouteType,
    TaskTimeouts,
    only_deferrable,
)


@pytest.fixture
def api_route_factory():
    def factory(callback, *, deferrable):
        return APIRouteDefinition(
            name="agreements-sync",
            path="/agreements/sync",
            route_type=RouteType.API,
            callback=callback,
            method=HTTPMethod.POST,
            deferrable=deferrable,
        )

    return factory


@pytest.mark.parametrize("deferrable", [False, True])
def test_api_route_not_only_deferrable(api_route_factory, deferrable):
    result = api_route_factory(lambda ctx: None, deferrable=deferrable)

    assert result.only_deferrable is False


def test_api_route_only_deferrable_from_handler(api_route_factory):
    result = api_route_factory(only_deferrable(lambda ctx: None), deferrable=True)

    assert result.only_deferrable is True


def test_api_route_rejects_not_deferrable_handler(api_route_factory):
    route_handler = only_deferrable(lambda ctx: None)

    with pytest.raises(TypeError, match="has an only-deferrable handler but is not deferrable"):
        api_route_factory(route_handler, deferrable=False)


@pytest.mark.parametrize(
    ("max_task_lifespan", "max_task_processing"),
    [(7200, None), (None, 3600), (7200, 3600)],
)
def test_task_timeouts_accepts_declared_limit(max_task_lifespan, max_task_processing):
    result = TaskTimeouts(
        max_task_lifespan=max_task_lifespan, max_task_processing=max_task_processing
    )

    assert result.max_task_lifespan == max_task_lifespan
    assert result.max_task_processing == max_task_processing


def test_task_timeouts_rejects_no_limit():
    with pytest.raises(ValueError, match="must declare max_task_lifespan, max_task_processing"):
        TaskTimeouts()
