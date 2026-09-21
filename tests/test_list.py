"""Tests for KitsuListProvider, KitsuListMedia, and KitsuListEntry."""

import copy
from datetime import UTC, datetime
from typing import Any

import aiohttp
import msgspec
import pytest
from anibridge.list import ListMediaType, ListStatus, ListTarget, ListUser

from anibridge.providers.list.kitsu.config import KitsuListProviderConfig
from anibridge.providers.list.kitsu.list import (
    KitsuListEntry,
    KitsuListMedia,
    KitsuListProvider,
    _get_anime_title,
)
from anibridge.providers.list.kitsu.models import (
    KitsuAnimeAttributes,
    KitsuAnimeResource,
    KitsuLibraryEntryAttributes,
    KitsuLibraryEntryResource,
    KitsuLibraryEntryResponse,
    KitsuTitles,
    KitsuUserAttributes,
    KitsuUserResource,
    KitsuUsersResponse,
)


class MockResponse:
    """Mock aiohttp response."""

    def __init__(self, status: int = 200, data: bytes = b"") -> None:
        self.status = status
        self._data = data

    async def read(self) -> bytes:
        return self._data

    def raise_for_status(self) -> None:
        if self.status >= 400:
            request_info = aiohttp.RequestInfo(
                url="https://kitsu.app/test",  # type: ignore[arg-type]
                method="GET",
                headers={},  # type: ignore[arg-type]
                real_url="https://kitsu.app/test",  # type: ignore[arg-type]
            )
            raise aiohttp.ClientResponseError(
                request_info=request_info,
                history=(),
                status=self.status,
                message=f"HTTP Error {self.status}",
            )

    async def __aenter__(self) -> MockResponse:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class MockClientSession:
    """Mock session for testing."""

    def __init__(self, responses: list[MockResponse] | None = None) -> None:
        self.responses = responses or []
        self.requests: list[dict[str, Any]] = []
        self.closed = False

    def request(self, method: str, url: str, **kwargs: Any) -> MockResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        if self.responses:
            return self.responses.pop(0)
        return MockResponse(200, b"{}")

    async def close(self) -> None:
        self.closed = True


# ==============================================================================
# Helper & Media Tests
# ==============================================================================


def test_get_anime_title_fallbacks() -> None:
    """Test title extraction priority and fallback strategies."""
    # 1. canonicalTitle present
    anime1 = KitsuAnimeResource(
        id="1",
        attributes=KitsuAnimeAttributes(canonicalTitle="Title Canonical"),
    )
    assert _get_anime_title(anime1) == "Title Canonical"

    # 2. titles object fallback
    anime2 = KitsuAnimeResource(
        id="2",
        attributes=KitsuAnimeAttributes(
            canonicalTitle=None,
            titles=KitsuTitles(en="English Title"),
        ),
    )
    assert _get_anime_title(anime2) == "English Title"

    # 3. slug fallback
    anime3 = KitsuAnimeResource(
        id="3",
        attributes=KitsuAnimeAttributes(canonicalTitle=None, slug="cool-anime-show"),
    )
    assert _get_anime_title(anime3) == "Cool Anime Show"

    # 4. No attributes
    anime4 = KitsuAnimeResource(id="4", attributes=None)
    assert _get_anime_title(anime4) == "Anime 4"


def test_kitsu_list_media_properties(
    sample_anime_resource: KitsuAnimeResource, mock_logger: Any
) -> None:
    """Test all properties and behaviors of KitsuListMedia."""
    config = KitsuListProviderConfig(token="tok")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    media = KitsuListMedia(provider, sample_anime_resource)

    assert media.key == "12"
    assert media.title == "Cowboy Bebop"
    assert media.external_url == "https://kitsu.app/anime/12"
    assert media.media_type == ListMediaType.TV
    assert media.total_units == 26
    assert (
        media.poster_image
        == "https://kitsu.app/media/anime/poster_images/12/medium.jpg"
    )
    assert "1998" in media.labels
    assert "Tv" in media.labels
    assert "Finished" in media.labels
    assert media.provider() is provider


def test_kitsu_list_media_movie(mock_logger: Any) -> None:
    """Test media_type and total_units when anime is a movie."""
    movie_anime = KitsuAnimeResource(
        id="99",
        attributes=KitsuAnimeAttributes(
            canonicalTitle="Spirited Away",
            subtype="movie",
            episodeCount=None,
        ),
    )
    config = KitsuListProviderConfig(token="tok")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    media = KitsuListMedia(provider, movie_anime)

    assert media.media_type == ListMediaType.MOVIE
    assert media.total_units == 1


def test_kitsu_list_media_minimal(mock_logger: Any) -> None:
    """Test media properties with minimal attributes."""
    minimal_anime = KitsuAnimeResource(id="101", attributes=None)
    config = KitsuListProviderConfig(token="tok")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    media = KitsuListMedia(provider, minimal_anime)

    assert media.labels == []
    assert media.media_type == ListMediaType.TV
    assert media.total_units is None
    assert media.poster_image is None


# ==============================================================================
# Entry Tests
# ==============================================================================


def test_kitsu_list_entry_getters_setters(
    sample_anime_resource: KitsuAnimeResource,
    sample_library_entry_resource: KitsuLibraryEntryResource,
    mock_logger: Any,
) -> None:
    """Test getting and setting all properties on KitsuListEntry."""
    config = KitsuListProviderConfig(token="tok")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    entry = KitsuListEntry(
        provider,
        anime=sample_anime_resource,
        entry=sample_library_entry_resource,
    )

    # Initial state from fixture
    assert entry.key == "12"
    assert entry.title == "Cowboy Bebop"
    assert entry.status == ListStatus.CURRENT
    assert entry.progress == 5
    assert entry.repeats == 0
    assert entry.review == "Enjoying it so far."
    assert entry.user_rating == 80  # 16 * 5
    assert entry.total_units == 26
    assert entry.media().key == "12"
    assert entry.provider() is provider
    assert isinstance(entry.started_at, datetime)
    assert entry.started_at.year == 2024
    assert entry.finished_at is None
    assert len(entry._changed_fields) == 0

    # Status changes
    entry.status = ListStatus.COMPLETED
    assert entry.status == ListStatus.COMPLETED
    assert "status" in entry._changed_fields

    entry.status = ListStatus.REPEATING
    assert entry.status == ListStatus.REPEATING
    assert entry._entry.attributes.reconsuming is True

    # Progress changes
    entry.progress = 26
    assert entry.progress == 26
    assert "progress" in entry._changed_fields

    with pytest.raises(ValueError, match="negative"):
        entry.progress = -1

    # Repeat changes
    entry.repeats = 2
    assert entry.repeats == 2
    assert "repeats" in entry._changed_fields

    with pytest.raises(ValueError, match="negative"):
        entry.repeats = -1

    # Review changes
    entry.review = "Masterpiece!"
    assert entry.review == "Masterpiece!"
    assert "review" in entry._changed_fields

    # Rating changes
    entry.user_rating = 100
    assert entry.user_rating == 100
    assert entry._entry.attributes.ratingTwenty == 20
    assert "user_rating" in entry._changed_fields

    with pytest.raises(ValueError, match="between 0 and 100"):
        entry.user_rating = 150

    with pytest.raises(ValueError, match="between 0 and 100"):
        entry.user_rating = -10

    # Date changes
    now = datetime(2024, 2, 1, 15, 30, tzinfo=UTC)
    entry.finished_at = now
    assert entry.finished_at == now
    assert "finished_at" in entry._changed_fields

    entry.started_at = datetime(2024, 1, 1, 10, 0)  # naive datetime
    assert entry.started_at.tzinfo is not None
    assert "started_at" in entry._changed_fields

    entry.started_at = None
    assert entry.started_at is None
    entry.finished_at = None
    assert entry.finished_at is None


def test_kitsu_list_entry_copy(
    sample_anime_resource: KitsuAnimeResource,
    sample_library_entry_resource: KitsuLibraryEntryResource,
    mock_logger: Any,
) -> None:
    """Test copying a KitsuListEntry creates an isolated duplicate."""
    config = KitsuListProviderConfig(token="tok")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    entry = KitsuListEntry(
        provider,
        anime=sample_anime_resource,
        entry=sample_library_entry_resource,
    )
    entry.progress = 10
    entry_copy = copy.copy(entry)

    assert entry_copy.progress == 10
    assert "progress" in entry_copy._changed_fields
    assert entry_copy is not entry
    assert entry_copy._entry is not entry._entry

    # Modifying copy doesn't affect original
    entry_copy.progress = 20
    assert entry.progress == 10
    assert entry_copy.progress == 20


# ==============================================================================
# Provider Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_provider_initialize(mock_logger: Any) -> None:
    """Test provider async initialization and user resolution."""
    user_payload = msgspec.json.encode(
        KitsuUsersResponse(
            data=[
                KitsuUserResource(
                    id="99",
                    type="users",
                    attributes=KitsuUserAttributes(name="spike", slug="spike"),
                )
            ]
        )
    )
    session = MockClientSession([MockResponse(200, user_payload)])
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False

    await provider.initialize()

    user = provider.user()
    assert user is not None
    assert user.key == "99"
    assert user.title == "spike"


@pytest.mark.asyncio
async def test_provider_resolve_mapping_descriptors(mock_logger: Any) -> None:
    """Test descriptor resolution filter."""
    provider = KitsuListProvider(logger=mock_logger)
    descriptors = [
        ("kitsu", "123", None),
        ("kitsu", "456", "season1"),
        ("mal", "789", None),
        ("anilist", "101112", None),
        ("kitsu", "", None),
    ]
    resolved = await provider.resolve_mapping_descriptors(descriptors)  # type: ignore[arg-type]
    assert len(resolved) == 2
    assert resolved[0] == ListTarget(descriptor=("kitsu", "123", None), media_key="123")
    assert resolved[1] == ListTarget(
        descriptor=("kitsu", "456", "season1"), media_key="456"
    )


@pytest.mark.asyncio
async def test_provider_get_entry_existing(
    mock_logger: Any,
    sample_anime_resource: KitsuAnimeResource,
    sample_library_entry_resource: KitsuLibraryEntryResource,
) -> None:
    """Test get_entry when anime and entry both exist."""
    session = MockClientSession()
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False
    provider._user = ListUser(key="42", title="tester")
    provider._client.user = KitsuUserResource(
        id="42", attributes=KitsuUserAttributes(name="tester")
    )
    provider._client._anime_cache["12"] = sample_anime_resource
    provider._client._entry_cache["12"] = sample_library_entry_resource

    entry = await provider.get_entry("12")
    assert entry is not None
    assert entry.key == "12"
    assert entry.status == ListStatus.CURRENT
    assert entry.progress == 5


@pytest.mark.asyncio
async def test_provider_get_entry_not_found(mock_logger: Any) -> None:
    """Test get_entry returns None when anime does not exist."""
    session = MockClientSession([MockResponse(404, b"Not found")])
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False

    entry = await provider.get_entry("999999")
    assert entry is None


@pytest.mark.asyncio
async def test_provider_get_entries_batch(
    mock_logger: Any, sample_anime_resource: KitsuAnimeResource
) -> None:
    """Test batch retrieval of multiple entries."""
    session = MockClientSession([MockResponse(404, b"Not found")])
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False
    provider._client._anime_cache["12"] = sample_anime_resource

    results = await provider.get_entries_batch(["12", "999999"])
    assert len(results) == 2
    assert results[0] is not None
    assert results[0].key == "12"
    assert results[1] is None


@pytest.mark.asyncio
async def test_provider_search(mock_logger: Any) -> None:
    """Test search delegating to client and returning KitsuListEntry list."""
    payload = b"""{
        "data": [
            {
                "id": "1",
                "type": "anime",
                "attributes": {"canonicalTitle": "Naruto"}
            },
            {
                "id": "2",
                "type": "anime",
                "attributes": {"canonicalTitle": "Naruto Shippuden"}
            }
        ]
    }"""
    session = MockClientSession([MockResponse(200, payload)])
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False

    results = await provider.search("Naruto")
    assert len(results) == 2
    assert results[0].title == "Naruto"
    assert results[1].title == "Naruto Shippuden"


@pytest.mark.asyncio
async def test_provider_update_entry_create_new(
    mock_logger: Any, sample_anime_resource: KitsuAnimeResource
) -> None:
    """Test update_entry creating a new library entry when entry.id is empty."""
    created_payload = msgspec.json.encode(
        KitsuLibraryEntryResponse(
            data=KitsuLibraryEntryResource(
                id="1000",
                attributes=KitsuLibraryEntryAttributes(status="current", progress=1),
            )
        )
    )
    session = MockClientSession([MockResponse(201, created_payload)])
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False
    provider._user = ListUser(key="42", title="tester")

    # Entry with no ID (new)
    entry = KitsuListEntry(provider, anime=sample_anime_resource)
    entry.status = ListStatus.CURRENT
    entry.progress = 1

    updated = await provider.update_entry("12", entry)
    assert updated is not None
    assert updated._entry.id == "1000"
    assert len(updated._changed_fields) == 0
    assert len(session.requests) == 1
    assert session.requests[0]["method"] == "POST"


@pytest.mark.asyncio
async def test_provider_update_entry_existing(
    mock_logger: Any,
    sample_anime_resource: KitsuAnimeResource,
    sample_library_entry_resource: KitsuLibraryEntryResource,
) -> None:
    """Test update_entry modifying an existing library entry via PATCH."""
    updated_payload = msgspec.json.encode(
        KitsuLibraryEntryResponse(
            data=KitsuLibraryEntryResource(
                id="999",
                attributes=KitsuLibraryEntryAttributes(status="completed", progress=26),
            )
        )
    )
    session = MockClientSession([MockResponse(200, updated_payload)])
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False
    provider._user = ListUser(key="42", title="tester")

    entry = KitsuListEntry(
        provider,
        anime=sample_anime_resource,
        entry=sample_library_entry_resource,
    )
    entry.status = ListStatus.COMPLETED
    entry.progress = 26

    updated = await provider.update_entry("12", entry)
    assert updated is not None
    assert updated._entry.id == "999"
    assert len(updated._changed_fields) == 0
    assert len(session.requests) == 1
    assert session.requests[0]["method"] == "PATCH"


@pytest.mark.asyncio
async def test_provider_update_entries_batch(
    mock_logger: Any,
    sample_anime_resource: KitsuAnimeResource,
    sample_library_entry_resource: KitsuLibraryEntryResource,
) -> None:
    """Test update_entries_batch updates multiple entries."""
    session = MockClientSession()
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False

    entry = KitsuListEntry(
        provider,
        anime=sample_anime_resource,
        entry=sample_library_entry_resource,
    )
    # No changes, should return immediately without request
    results = await provider.update_entries_batch([entry])
    assert len(results) == 1
    assert results[0] is entry


@pytest.mark.asyncio
async def test_provider_delete_entry(
    mock_logger: Any,
    sample_anime_resource: KitsuAnimeResource,
    sample_library_entry_resource: KitsuLibraryEntryResource,
) -> None:
    """Test delete_entry calls DELETE and evicts entry from cache."""
    session = MockClientSession([MockResponse(204, b"")])
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False
    provider._user = ListUser(key="42", title="tester")
    provider._client._entry_cache["12"] = sample_library_entry_resource

    await provider.delete_entry("12")
    assert "12" not in provider._client._entry_cache
    assert len(session.requests) == 1
    assert session.requests[0]["method"] == "DELETE"


@pytest.mark.asyncio
async def test_provider_backup_and_restore_list(mock_logger: Any) -> None:
    """Test backing up and restoring user list."""
    backup_entries = b"""{
        "data": [
            {
                "id": "500",
                "type": "libraryEntries",
                "attributes": {"status": "completed", "progress": 12},
                "relationships": {"anime": {"data": {"id": "100", "type": "anime"}}}
            }
        ]
    }"""
    session = MockClientSession(
        [
            MockResponse(200, backup_entries),  # for backup
            MockResponse(
                200, b'{"data": {"id": "500", "type": "libraryEntries"}}'
            ),  # for update in restore
        ]
    )
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False
    provider._user = ListUser(key="42", title="tester")

    backup_json = await provider.backup_list()
    assert "500" in backup_json
    assert "completed" in backup_json

    await provider.restore_list(backup_json)
    assert len(session.requests) == 2
    assert session.requests[1]["method"] == "PATCH"


@pytest.mark.asyncio
async def test_provider_clear_cache_and_close(mock_logger: Any) -> None:
    """Test clear_cache and close delegates to client."""
    session = MockClientSession()
    config = KitsuListProviderConfig(token="test-token")
    provider = KitsuListProvider(logger=mock_logger, config=msgspec.to_builtins(config))
    provider._client._session = session  # type: ignore[assignment]
    provider._client._owns_session = False

    provider._client._anime_cache["1"] = KitsuAnimeResource(id="1")
    await provider.clear_cache()
    assert len(provider._client._anime_cache) == 0

    await provider.close()
