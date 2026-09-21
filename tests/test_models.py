"""Unit tests for models and mapping conversions."""

import msgspec
import pytest
from anibridge.list import ListStatus

from anibridge.providers.list.kitsu.models import (
    KitsuAnimeResponse,
    KitsuErrorResponse,
    KitsuLibraryEntryResponse,
    KitsuOAuthTokenResponse,
    kitsu_rating_to_user_rating,
    kitsu_status_to_list,
    list_status_to_kitsu,
    user_rating_to_kitsu_rating,
)


@pytest.mark.parametrize(
    ("kitsu_status", "reconsuming", "expected"),
    [
        (None, False, None),
        ("current", False, ListStatus.CURRENT),
        ("CURRENT", False, ListStatus.CURRENT),
        ("current", True, ListStatus.REPEATING),
        ("completed", False, ListStatus.COMPLETED),
        ("on_hold", False, ListStatus.PAUSED),
        ("dropped", False, ListStatus.DROPPED),
        ("planned", False, ListStatus.PLANNING),
        ("nonexistent", False, None),
    ],
)
def test_kitsu_status_to_list(
    kitsu_status: str | None, reconsuming: bool, expected: ListStatus | None
) -> None:
    """Test mapping from Kitsu status string to AniBridge ListStatus."""
    assert kitsu_status_to_list(kitsu_status, reconsuming=reconsuming) == expected


@pytest.mark.parametrize(
    ("list_status", "expected_status", "expected_reconsuming"),
    [
        (None, None, False),
        (ListStatus.CURRENT, "current", False),
        (ListStatus.REPEATING, "current", True),
        (ListStatus.COMPLETED, "completed", False),
        (ListStatus.PAUSED, "on_hold", False),
        (ListStatus.DROPPED, "dropped", False),
        (ListStatus.PLANNING, "planned", False),
    ],
)
def test_list_status_to_kitsu(
    list_status: ListStatus | None,
    expected_status: str | None,
    expected_reconsuming: bool,
) -> None:
    """Test mapping from AniBridge ListStatus to Kitsu status tuple."""
    assert list_status_to_kitsu(list_status) == (expected_status, expected_reconsuming)


@pytest.mark.parametrize(
    ("twenty_score", "expected_user_rating"),
    [
        (None, None),
        (2, 10),
        (16, 80),
        (20, 100),
        (0, 0),
        (25, 100),
    ],
)
def test_kitsu_rating_to_user_rating(
    twenty_score: int | None, expected_user_rating: int | None
) -> None:
    """Test converting Kitsu ratingTwenty (2..20) to AniBridge 0..100."""
    assert kitsu_rating_to_user_rating(twenty_score) == expected_user_rating


@pytest.mark.parametrize(
    ("user_rating", "expected_twenty_score"),
    [
        (None, None),
        (0, 2),
        (10, 2),
        (50, 10),
        (78, 16),
        (82, 16),
        (100, 20),
        (120, 20),
    ],
)
def test_user_rating_to_kitsu_rating(
    user_rating: int | None, expected_twenty_score: int | None
) -> None:
    """Test converting AniBridge 0..100 score to Kitsu ratingTwenty (2..20)."""
    assert user_rating_to_kitsu_rating(user_rating) == expected_twenty_score


def test_anime_json_decode() -> None:
    """Test decoding Kitsu anime JSON:API payload."""
    raw_json = b"""{
        "data": {
            "id": "1",
            "type": "anime",
            "attributes": {
                "canonicalTitle": "Cowboy Bebop",
                "titles": {
                    "en": "Cowboy Bebop",
                    "ja_jp": "Cowboy Bebop"
                },
                "subtype": "TV",
                "status": "finished",
                "episodeCount": 26,
                "posterImage": {
                    "medium": "https://kitsu.app/poster.jpg"
                }
            }
        }
    }"""
    resp = msgspec.json.decode(raw_json, type=KitsuAnimeResponse)
    assert resp.data.id == "1"
    assert resp.data.type == "anime"
    assert resp.data.attributes is not None
    assert resp.data.attributes.canonicalTitle == "Cowboy Bebop"
    assert resp.data.attributes.episodeCount == 26
    assert resp.data.attributes.posterImage is not None
    assert resp.data.attributes.posterImage.medium == "https://kitsu.app/poster.jpg"


def test_library_entry_json_decode() -> None:
    """Test decoding Kitsu library entry JSON:API payload."""
    raw_json = b"""{
        "data": {
            "id": "555",
            "type": "libraryEntries",
            "attributes": {
                "status": "current",
                "progress": 12,
                "reconsuming": false,
                "reconsumeCount": 1,
                "notes": "Great series",
                "ratingTwenty": 18,
                "startedAt": "2024-01-01T00:00:00.000Z",
                "finishedAt": null
            },
            "relationships": {
                "anime": {"data": {"id": "1", "type": "anime"}}
            }
        }
    }"""
    resp = msgspec.json.decode(raw_json, type=KitsuLibraryEntryResponse)
    assert resp.data.id == "555"
    assert resp.data.attributes.status == "current"
    assert resp.data.attributes.progress == 12
    assert resp.data.attributes.reconsumeCount == 1
    assert resp.data.attributes.ratingTwenty == 18
    assert resp.data.relationships is not None
    assert resp.data.relationships["anime"]["data"]["id"] == "1"


def test_error_response_decode() -> None:
    """Test decoding Kitsu JSON:API error payload."""
    raw_json = b"""{
        "errors": [
            {
                "title": "Invalid filter",
                "detail": "filter[userId] is required",
                "status": "400"
            }
        ]
    }"""
    resp = msgspec.json.decode(raw_json, type=KitsuErrorResponse)
    assert len(resp.errors) == 1
    assert resp.errors[0].title == "Invalid filter"
    assert resp.errors[0].detail == "filter[userId] is required"
    assert resp.errors[0].status == "400"


def test_oauth_token_response_decode() -> None:
    """Test decoding Kitsu OAuth token payload."""
    raw_json = b"""{
        "access_token": "access-12345",
        "token_type": "bearer",
        "expires_in": 7200,
        "refresh_token": "refresh-67890",
        "scope": "public",
        "created_at": 1700000000
    }"""
    resp = msgspec.json.decode(raw_json, type=KitsuOAuthTokenResponse)
    assert resp.access_token == "access-12345"
    assert resp.token_type == "bearer"
    assert resp.expires_in == 7200
    assert resp.refresh_token == "refresh-67890"
