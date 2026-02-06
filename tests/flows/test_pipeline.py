import pytest

from mpt_extension_sdk.flows.context import Context
from mpt_extension_sdk.flows.pipeline import Pipeline, Step


@pytest.fixture
def mock_context(mocker):
    return mocker.Mock(spec=Context)


def test_pipeline_completes(mocker, mock_context, mpt_client):
    class TestStep(Step):
        def __call__(self, client, context, next_step):
            next_step(client, context)

    # BL
    step1 = TestStep()
    step2 = TestStep()
    test_step_spy = mocker.spy(TestStep, "__call__")
    pipeline = Pipeline(step1, step2)

    pipeline.run(mpt_client, mock_context)  # act

    assert len(pipeline) == 2
    test_step_spy.assert_has_calls([
        mocker.call(step1, mpt_client, mock_context, mocker.ANY),
        mocker.call(step2, mpt_client, mock_context, mocker.ANY),
    ])


def test_pipeline_exit_prematurely(mocker, mock_context, mpt_client):
    class TestStep1(Step):
        def __call__(self, client, context, next_step):
            pass

    # BL
    class TestStep2(Step):
        def __call__(self, client, context, next_step):
            next_step(client, context)

    # BL
    step1 = TestStep1()
    step2 = TestStep2()
    step1_spy = mocker.spy(TestStep1, "__call__")
    step2_spy = mocker.spy(TestStep2, "__call__")
    pipeline = Pipeline(step1, step2)

    pipeline.run(mpt_client, mock_context)  # act

    assert len(pipeline) == 2
    step1_spy.assert_called_once()
    step2_spy.assert_not_called()


def test_pipeline_exception_default_handler(mock_context, mpt_client):
    class TestStep(Step):
        def __call__(self, client, context, next_step):
            raise Exception("exception!")  # noqa:  TRY002

    # BL
    step1 = TestStep()
    step2 = TestStep()
    pipeline = Pipeline(step1, step2)

    with pytest.raises(Exception, match="exception!"):
        pipeline.run(mpt_client, mock_context)
