from app.core.config import Settings


def test_cors_origins_list_defaults_to_wildcard():
    settings = Settings(cors_origins="*")
    assert settings.cors_origins_list == ["*"]


def test_cors_origins_list_splits_and_trims_comma_separated_origins():
    settings = Settings(cors_origins="https://wattledger.example.com, https://www.wattledger.example.com ")
    assert settings.cors_origins_list == [
        "https://wattledger.example.com",
        "https://www.wattledger.example.com",
    ]


def test_cors_origins_list_ignores_empty_entries():
    settings = Settings(cors_origins="https://a.example.com,,https://b.example.com,")
    assert settings.cors_origins_list == ["https://a.example.com", "https://b.example.com"]
