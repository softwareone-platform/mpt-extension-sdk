def test_base_fields_fill_base_context(resources):
    result = resources.base_fields()

    assert result == {
        "auth": resources.auth,
        "ext_settings": resources.ext_settings,
        "mpt_api_service": resources.mpt_api_service,
        "runtime_settings": resources.runtime_settings,
        "vendor_mpt_api_service": resources.vendor_mpt_api_service,
    }
