"""Tests for KitsuListProviderConfig."""

import msgspec

from anibridge.providers.list.kitsu.config import KitsuListProviderConfig


def test_default_config() -> None:
    """Test default values of KitsuListProviderConfig."""
    config = KitsuListProviderConfig()
    assert config.token is None
    assert config.username is None
    assert config.password is None
    assert config.rate_limit == 1.0
    assert config.base_url == "https://kitsu.app/api/edge"
    assert config.oauth_url == "https://kitsu.app/api/oauth/token"


def test_custom_config() -> None:
    """Test setting custom values on KitsuListProviderConfig."""
    config = KitsuListProviderConfig(
        token="secret-token",
        username="animefan",
        password="secretpassword",
        rate_limit=2.5,
        base_url="https://custom.kitsu.app/api/edge",
        oauth_url="https://custom.kitsu.app/api/oauth/token",
    )
    assert config.token == "secret-token"
    assert config.username == "animefan"
    assert config.password == "secretpassword"
    assert config.rate_limit == 2.5
    assert config.base_url == "https://custom.kitsu.app/api/edge"
    assert config.oauth_url == "https://custom.kitsu.app/api/oauth/token"


def test_config_from_dict() -> None:
    """Test converting from a raw dict via msgspec."""
    raw = {
        "token": "tok123",
        "rate_limit": 5.0,
    }
    config = msgspec.convert(raw, type=KitsuListProviderConfig)
    assert config.token == "tok123"
    assert config.rate_limit == 5.0
    assert config.base_url == "https://kitsu.app/api/edge"
