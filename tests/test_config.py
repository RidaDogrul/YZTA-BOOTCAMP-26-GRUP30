from src.utils.config import Settings


def test_settings_loads_default_values():
    settings = Settings()

    assert settings.app_name == "Otonom Data Cleanroom & Tahminleme Ajanı"
    assert settings.app_env in {"local", "dev", "test", "prod"}
    assert settings.database_url is not None


def test_safe_dict_masks_secrets():
    settings = Settings(
        google_api_key="secret-key",
        aws_access_key_id="access-key",
        aws_secret_access_key="secret-access-key",
    )

    safe_data = settings.safe_dict()

    assert safe_data["google_api_key"] == "***masked***"
    assert safe_data["aws_access_key_id"] == "***masked***"
    assert safe_data["aws_secret_access_key"] == "***masked***"