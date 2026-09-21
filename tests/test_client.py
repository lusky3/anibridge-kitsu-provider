"""Unit tests for KitsuClient."""

from typing import Any

import aiohttp
import msgspec
import pytest

from anibridge.providers.list.kitsu.client import KitsuClient
from anibridge.providers.list.kitsu.config import KitsuListProviderConfig
from anibridge.providers.list.kitsu.models import (
    KitsuAnimeAttributes,
    KitsuAnimeResource,
    KitsuAnimeResponse,
    KitsuLibraryEntryAttributes,
    KitsuLibraryEntryResource,
    KitsuLibraryEntryResponse,
    KitsuOAuthTokenResponse,
    KitsuUserAttributes,
    KitsuUserResource,
    KitsuUsersResponse,
)


class MockResponse:
    """Mock aiohttp response."""

    def __init__(
        self,
        status: int = 200,
        data: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._data = data
        self.headers = headers or {"Content-Type": "application/vnd.api+json"}

    async def read(self) -> bytes:
        return self._data

    async def text(self) -> str:
        return self._data.decode("utf-8")

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
    """Mock aiohttp ClientSession."""

    def __init__(self, responses: list[MockResponse] | None = None) -> None:
        self.responses: list[MockResponse] = responses or []
        self.requests: list[dict[str, Any]] = []
        self.closed = False

    def request(self, method: str, url: str, **kwargs: Any) -> MockResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        if self.responses:
            return self.responses.pop(0)
        return MockResponse(200, b"{}")

    def post(self, url: str, **kwargs: Any) -> MockResponse:
        return self.request("POST", url, **kwargs)

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_client_initialize_with_token(mock_logger: Any) -> None:
    """Test client initialization with a preconfigured token."""
    user_payload = msgspec.json.encode(
        KitsuUsersResponse(
            data=[
                KitsuUserResource(
                    id="100",
                    type="users",
                    attributes=KitsuUserAttributes(name="bob", slug="bob"),
                )
            ]
        )
    )
    session = MockClientSession([MockResponse(200, user_payload)])
    config = KitsuListProviderConfig(token="valid-token")

    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]
    await client.initialize()

    assert client.user is not None
    assert client.user.id == "100"
    assert client.user.attributes.name == "bob"
    assert len(session.requests) == 1
    assert "Authorization" in session.requests[0]["headers"]
    assert session.requests[0]["headers"]["Authorization"] == "Bearer valid-token"


@pytest.mark.asyncio
async def test_client_login_password_grant(mock_logger: Any) -> None:
    """Test login via password grant when username and password are provided."""
    token_payload = msgspec.json.encode(
        KitsuOAuthTokenResponse(
            access_token="new-access-token",
            token_type="bearer",
            refresh_token="new-refresh-token",
            expires_in=7200,
        )
    )
    user_payload = msgspec.json.encode(
        KitsuUsersResponse(
            data=[
                KitsuUserResource(
                    id="101",
                    type="users",
                    attributes=KitsuUserAttributes(name="alice"),
                )
            ]
        )
    )
    session = MockClientSession(
        [
            MockResponse(200, token_payload),
            MockResponse(200, user_payload),
        ]
    )
    config = KitsuListProviderConfig(username="alice", password="password123")

    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]
    await client.initialize()

    assert client.access_token == "new-access-token"
    assert client.refresh_token == "new-refresh-token"
    assert client.user is not None
    assert client.user.id == "101"
    assert len(session.requests) == 2
    assert session.requests[0]["method"] == "POST"
    assert session.requests[0]["json"]["username"] == "alice"


@pytest.mark.asyncio
async def test_client_login_failure(mock_logger: Any) -> None:
    """Test login failure raising ClientResponseError."""
    session = MockClientSession([MockResponse(401, b'{"error": "invalid_grant"}')])
    config = KitsuListProviderConfig(username="alice", password="wrongpassword")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    with pytest.raises(aiohttp.ClientResponseError):
        await client.login("alice", "wrongpassword")


@pytest.mark.asyncio
async def test_get_current_user_empty(mock_logger: Any) -> None:
    """Test get_current_user when API returns an empty user list."""
    empty_payload = msgspec.json.encode(KitsuUsersResponse(data=[]))
    session = MockClientSession([MockResponse(200, empty_payload)])
    config = KitsuListProviderConfig(token="valid-token")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="no user"):
        await client.get_current_user()


@pytest.mark.asyncio
async def test_get_anime_success_and_cache(mock_logger: Any) -> None:
    """Test get_anime fetches from API and caches result."""
    anime_payload = msgspec.json.encode(
        KitsuAnimeResponse(
            data=KitsuAnimeResource(
                id="12",
                attributes=KitsuAnimeAttributes(canonicalTitle="Cowboy Bebop"),
            )
        )
    )
    session = MockClientSession([MockResponse(200, anime_payload)])
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    # First fetch: hits session
    anime = await client.get_anime("12")
    assert anime is not None
    assert anime.id == "12"
    assert anime.attributes.canonicalTitle == "Cowboy Bebop"
    assert len(session.requests) == 1

    # Second fetch: served from cache
    cached_anime = await client.get_anime("12")
    assert cached_anime is anime
    assert len(session.requests) == 1


@pytest.mark.asyncio
async def test_get_anime_404(mock_logger: Any) -> None:
    """Test get_anime returning None on 404."""
    session = MockClientSession([MockResponse(404, b"Not found")])
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    anime = await client.get_anime("999999")
    assert anime is None


@pytest.mark.asyncio
async def test_search_anime(mock_logger: Any) -> None:
    """Test search_anime returns matching anime and caches them."""
    payload = b"""{
        "data": [
            {
                "id": "1",
                "type": "anime",
                "attributes": {"canonicalTitle": "Cowboy Bebop"}
            },
            {
                "id": "2",
                "type": "anime",
                "attributes": {"canonicalTitle": "Cowboy Bebop: The Movie"}
            }
        ]
    }"""
    session = MockClientSession([MockResponse(200, payload)])
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    results = await client.search_anime("Cowboy", limit=2)
    assert len(results) == 2
    assert results[0].id == "1"
    assert results[1].id == "2"
    assert "1" in client._anime_cache
    assert "2" in client._anime_cache


@pytest.mark.asyncio
async def test_get_library_entry_found(mock_logger: Any) -> None:
    """Test get_library_entry when entry is present with included anime."""
    payload = b"""{
        "data": [
            {
                "id": "777",
                "type": "libraryEntries",
                "attributes": {"status": "current", "progress": 3},
                "relationships": {"anime": {"data": {"id": "1", "type": "anime"}}}
            }
        ],
        "included": [
            {
                "id": "1",
                "type": "anime",
                "attributes": {"canonicalTitle": "Cowboy Bebop"}
            }
        ]
    }"""
    session = MockClientSession([MockResponse(200, payload)])
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    entry, anime = await client.get_library_entry(user_id="42", anime_id="1")
    assert entry is not None
    assert entry.id == "777"
    assert entry.attributes.progress == 3
    assert anime is not None
    assert anime.id == "1"
    assert anime.attributes.canonicalTitle == "Cowboy Bebop"
    assert client._entry_cache.get("1") == entry


@pytest.mark.asyncio
async def test_get_library_entry_not_found(mock_logger: Any) -> None:
    """Test get_library_entry when no entry exists."""
    payload = b"""{"data": []}"""
    session = MockClientSession([MockResponse(200, payload)])
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    entry, anime = await client.get_library_entry(user_id="42", anime_id="99")
    assert entry is None
    assert anime is None


@pytest.mark.asyncio
async def test_create_library_entry(mock_logger: Any) -> None:
    """Test create_library_entry POST request."""
    response_payload = msgspec.json.encode(
        KitsuLibraryEntryResponse(
            data=KitsuLibraryEntryResource(
                id="888",
                attributes=KitsuLibraryEntryAttributes(status="planned", progress=0),
            )
        )
    )
    session = MockClientSession([MockResponse(201, response_payload)])
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    created = await client.create_library_entry(
        user_id="42", anime_id="1", attributes={"status": "planned"}
    )
    assert created.id == "888"
    assert created.attributes.status == "planned"
    assert len(session.requests) == 1
    req = session.requests[0]
    assert req["method"] == "POST"
    assert req["json"]["data"]["relationships"]["user"]["data"]["id"] == "42"
    assert req["json"]["data"]["relationships"]["media"]["data"]["id"] == "1"


@pytest.mark.asyncio
async def test_update_library_entry(mock_logger: Any) -> None:
    """Test update_library_entry PATCH request."""
    response_payload = msgspec.json.encode(
        KitsuLibraryEntryResponse(
            data=KitsuLibraryEntryResource(
                id="888",
                attributes=KitsuLibraryEntryAttributes(status="current", progress=5),
            )
        )
    )
    session = MockClientSession([MockResponse(200, response_payload)])
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    updated = await client.update_library_entry("888", {"progress": 5})
    assert updated.id == "888"
    assert updated.attributes.progress == 5
    req = session.requests[0]
    assert req["method"] == "PATCH"
    assert req["url"].endswith("/library-entries/888")
    assert req["json"]["data"]["attributes"]["progress"] == 5


@pytest.mark.asyncio
async def test_delete_library_entry(mock_logger: Any) -> None:
    """Test delete_library_entry DELETE request."""
    session = MockClientSession([MockResponse(204, b"")])
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    await client.delete_library_entry("888")
    req = session.requests[0]
    assert req["method"] == "DELETE"
    assert req["url"].endswith("/library-entries/888")


@pytest.mark.asyncio
async def test_get_user_library_entries_pagination(mock_logger: Any) -> None:
    """Test get_user_library_entries pagination."""
    payload = b"""{
        "data": [
            {
                "id": "1",
                "type": "libraryEntries",
                "attributes": {"status": "completed"},
                "relationships": {"anime": {"data": {"id": "10", "type": "anime"}}}
            }
        ],
        "included": [
            {"id": "10", "type": "anime", "attributes": {"canonicalTitle": "Trigun"}}
        ]
    }"""
    session = MockClientSession([MockResponse(200, payload)])
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    entries, anime_list, has_more = await client.get_user_library_entries("42", limit=1)
    assert len(entries) == 1
    assert len(anime_list) == 1
    assert has_more is True  # len(entries) >= limit
    assert client._entry_cache.get("10") == entries[0]


@pytest.mark.asyncio
async def test_api_error_handling(mock_logger: Any) -> None:
    """Test error parsing on HTTP error response."""
    error_payload = b"""{
        "errors": [
            {
                "title": "Forbidden",
                "detail": "You cannot access this resource",
                "status": "403"
            }
        ]
    }"""
    session = MockClientSession([MockResponse(403, error_payload)])
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]

    with pytest.raises(aiohttp.ClientResponseError) as exc_info:
        await client._request("GET", "https://kitsu.app/api/edge/secret")
    assert exc_info.value.status == 403


@pytest.mark.asyncio
async def test_clear_cache_and_close(mock_logger: Any) -> None:
    """Test clear_cache and close methods."""
    session = MockClientSession()
    config = KitsuListProviderConfig(token="tok")
    client = KitsuClient(logger=mock_logger, config=config, session=session)  # type: ignore[arg-type]
    client._anime_cache["1"] = KitsuAnimeResource(id="1")
    client._entry_cache["1"] = KitsuLibraryEntryResource(id="1")

    client.clear_cache()
    assert len(client._anime_cache) == 0
    assert len(client._entry_cache) == 0

    await client.close()
    # Test closing an owned session
    owned_client = KitsuClient(logger=mock_logger, config=config)
    owned_sess = owned_client.session
    assert not owned_sess.closed
    await owned_client.close()
    assert owned_sess.closed
