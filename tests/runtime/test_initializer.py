from django.test import override_settings

from mpt_extension_sdk.runtime.initializer import initialize


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={
        "version": 1,
        "root": {
            "handlers": ["rich"],
        },
        "loggers": {
            "mpt_extension_sdk": {},
            "swo.mpt": {},
        },
    },
)
def test_initialize(mocker, mock_initializer_options, mock_app_group_name):
    mocked_setup = mocker.patch("django.setup")
    initialize(mock_initializer_options, group=mock_app_group_name)
    mocked_setup.assert_called_once()


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    USE_APPLICATIONINSIGHTS=True,
    LOGGING={
        "version": 1,
        "root": {
            "handlers": ["rich"],
        },
        "loggers": {
            "mpt_extension_sdk": {},
            "swo.mpt": {},
        },
    },
)
def test_initialize_appinsights_instrumentation(
    mocker,
    monkeypatch,
    mock_initializer_options,
    mock_app_group_name,
    mock_app_insights_connection_string,
):
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        mock_app_insights_connection_string,
    )

    mocker.patch(
        "mpt_extension_sdk.runtime.initializer.get_extension_variables",
        return_value={}
    )
    mocker.patch(
        "mpt_extension_sdk.runtime.initializer.extract_product_ids",
        return_value=[]
    )
    mocker.patch(
        "mpt_extension_sdk.runtime.initializer.get_extension_app_config_name",
        return_value=mock_app_group_name
    )
    mocker.patch("django.setup")

    mock_instrument_logging = mocker.patch(
        "mpt_extension_sdk.runtime.initializer.instrument_logging"
    )
    mock_botocore_instrumentor = mocker.patch(
        "mpt_extension_sdk.runtime.initializer.BotocoreInstrumentor"
    )
    mock_instance = mocker.Mock()
    mock_botocore_instrumentor.return_value = mock_instance

    from mpt_extension_sdk.runtime.initializer import initialize

    initialize(mock_initializer_options, group=mock_app_group_name)

    mock_instrument_logging.assert_called_once()
    mock_botocore_instrumentor.assert_called_once()
    mock_instance.instrument.assert_called_once()


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    USE_APPLICATIONINSIGHTS=False,
    LOGGING={
        "version": 1,
        "root": {
            "handlers": ["rich"],
        },
        "loggers": {
            "mpt_extension_sdk": {},
            "swo.mpt": {},
        },
    },
)
def test_initialize_without_appinsights_instrumentation(
    mocker,
    mock_initializer_options,
    mock_app_group_name,
):
    """Test that Application Insights instrumentation is not called when
    USE_APPLICATIONINSIGHTS is False."""
    mocker.patch(
        "mpt_extension_sdk.runtime.initializer.get_extension_variables",
        return_value={}
    )
    mocker.patch(
        "mpt_extension_sdk.runtime.initializer.extract_product_ids",
        return_value=[]
    )
    mocker.patch(
        "mpt_extension_sdk.runtime.initializer.get_extension_app_config_name",
        return_value=mock_app_group_name
    )
    mocker.patch("django.setup")

    mock_instrument_logging = mocker.patch(
        "mpt_extension_sdk.runtime.initializer.instrument_logging"
    )
    mock_botocore_instrumentor = mocker.patch(
        "mpt_extension_sdk.runtime.initializer.BotocoreInstrumentor"
    )

    from mpt_extension_sdk.runtime.initializer import initialize

    initialize(mock_initializer_options, group=mock_app_group_name)

    # Assert that Application Insights instrumentation functions are NOT called
    mock_instrument_logging.assert_not_called()
    mock_botocore_instrumentor.assert_not_called()


