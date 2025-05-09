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
def test_initialize(mocker, mock_initializer_options):
    mocked_setup = mocker.patch("django.setup")
    initialize(mock_initializer_options)
    mocked_setup.assert_called_once()
