from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.event import EventMetadata
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings


def test_agreement_context_exposes_agreement_id(
    mocker, logger, runtime_settings, agreement_factory
):
    context = AgreementContext(
        logger=logger,
        meta=EventMetadata(
            event_id="EVT-1",
            object_id="AGR-1",
            object_type="Agreement",
            task_id="TASK-1",
        ),
        mpt_api_service=mocker.AsyncMock(spec=MPTAPIService),
        ext_settings=mocker.AsyncMock(spec=BaseExtensionSettings),
        runtime_settings=runtime_settings,
        agreement=agreement_factory("AGR-99"),
    )

    result = context.agreement_id

    assert result == "AGR-99"


async def test_agreement_context_refreshes_agreement(
    mocker, logger, runtime_settings, agreement_factory
):
    service = mocker.AsyncMock(
        spec=MPTAPIService, agreements=mocker.AsyncMock(spec=AgreementService)
    )
    service.agreements.get_by_id = mocker.AsyncMock(return_value=agreement_factory("AGR-2"))
    context = AgreementContext(
        logger=logger,
        meta=EventMetadata(
            event_id="EVT-1",
            object_id="AGR-1",
            object_type="Agreement",
            task_id="TASK-1",
        ),
        mpt_api_service=service,
        ext_settings=mocker.AsyncMock(spec=BaseExtensionSettings),
        runtime_settings=runtime_settings,
        agreement=agreement_factory("AGR-1"),
    )

    await context.refresh_agreement()  # act

    assert context.agreement.id == "AGR-2"
    service.agreements.get_by_id.assert_awaited_once_with("AGR-1")
