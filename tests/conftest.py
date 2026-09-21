"""Pytest fixtures and test helpers for anibridge-kitsu-provider."""

import pytest

from anibridge.providers.list.kitsu.config import KitsuListProviderConfig
from anibridge.providers.list.kitsu.models import (
    KitsuAnimeAttributes,
    KitsuAnimeResource,
    KitsuLibraryEntryAttributes,
    KitsuLibraryEntryResource,
    KitsuPosterImage,
    KitsuTitles,
    KitsuUserAttributes,
    KitsuUserResource,
)


class MockProviderLogger:
    """Mock logger implementing ProviderLogger protocol."""

    def __init__(self) -> None:
        self.logs: list[tuple[str, str]] = []

    def debug(self, msg: object, *args: object, **kwargs: object) -> None:
        self.logs.append(("debug", str(msg) % args if args else str(msg)))

    def info(self, msg: object, *args: object, **kwargs: object) -> None:
        self.logs.append(("info", str(msg) % args if args else str(msg)))

    def success(self, msg: object, *args: object, **kwargs: object) -> None:
        self.logs.append(("success", str(msg) % args if args else str(msg)))

    def warning(self, msg: object, *args: object, **kwargs: object) -> None:
        self.logs.append(("warning", str(msg) % args if args else str(msg)))

    def error(self, msg: object, *args: object, **kwargs: object) -> None:
        self.logs.append(("error", str(msg) % args if args else str(msg)))

    def exception(self, msg: object, *args: object, **kwargs: object) -> None:
        self.logs.append(("exception", str(msg) % args if args else str(msg)))

    def getChild(self, name: str) -> MockProviderLogger:
        return self


@pytest.fixture
def mock_logger() -> MockProviderLogger:
    """Fixture providing a mock ProviderLogger."""
    return MockProviderLogger()


@pytest.fixture
def default_config() -> KitsuListProviderConfig:
    """Fixture providing standard configuration."""
    return KitsuListProviderConfig(
        token="test-token-12345",
        rate_limit=100.0,
        base_url="https://kitsu.app/api/edge",
        oauth_url="https://kitsu.app/api/oauth/token",
    )


@pytest.fixture
def sample_user_resource() -> KitsuUserResource:
    """Fixture providing a sample user resource."""
    return KitsuUserResource(
        id="42",
        type="users",
        attributes=KitsuUserAttributes(name="testuser", slug="testuser"),
    )


@pytest.fixture
def sample_anime_resource() -> KitsuAnimeResource:
    """Fixture providing a sample anime resource."""
    return KitsuAnimeResource(
        id="12",
        type="anime",
        attributes=KitsuAnimeAttributes(
            canonicalTitle="Cowboy Bebop",
            titles=KitsuTitles(
                canonicalTitle="Cowboy Bebop",
                en="Cowboy Bebop",
                en_jp="Cowboy Bebop",
                ja_jp="カウボーイビバップ",
            ),
            slug="cowboy-bebop",
            subtype="TV",
            status="finished",
            startDate="1998-04-03",
            endDate="1999-04-24",
            episodeCount=26,
            episodeLength=25,
            posterImage=KitsuPosterImage(
                medium="https://kitsu.app/media/anime/poster_images/12/medium.jpg",
                large="https://kitsu.app/media/anime/poster_images/12/large.jpg",
            ),
        ),
    )


@pytest.fixture
def sample_library_entry_resource() -> KitsuLibraryEntryResource:
    """Fixture providing a sample library entry resource."""
    return KitsuLibraryEntryResource(
        id="999",
        type="libraryEntries",
        attributes=KitsuLibraryEntryAttributes(
            status="current",
            progress=5,
            reconsuming=False,
            reconsumeCount=0,
            notes="Enjoying it so far.",
            ratingTwenty=16,
            startedAt="2024-01-10T12:00:00.000Z",
            finishedAt=None,
        ),
        relationships={
            "anime": {"data": {"id": "12", "type": "anime"}},
            "user": {"data": {"id": "42", "type": "users"}},
        },
    )
