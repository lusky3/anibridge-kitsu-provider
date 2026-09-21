"""Data models and conversions for the Kitsu API."""

from enum import StrEnum
from typing import Any

import msgspec
from anibridge.list import ListStatus

__all__ = [
    "KitsuAnimeAttributes",
    "KitsuAnimeListResponse",
    "KitsuAnimeResource",
    "KitsuAnimeResponse",
    "KitsuError",
    "KitsuErrorResponse",
    "KitsuLibraryEntriesResponse",
    "KitsuLibraryEntryAttributes",
    "KitsuLibraryEntryResource",
    "KitsuLibraryEntryResponse",
    "KitsuOAuthTokenResponse",
    "KitsuPosterImage",
    "KitsuRelationship",
    "KitsuRelationshipData",
    "KitsuStatus",
    "KitsuTitles",
    "KitsuUserAttributes",
    "KitsuUserResource",
    "KitsuUsersResponse",
    "kitsu_rating_to_user_rating",
    "kitsu_status_to_list",
    "list_status_to_kitsu",
    "user_rating_to_kitsu_rating",
]


class KitsuStatus(StrEnum):
    """Kitsu library entry status values."""

    CURRENT = "current"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    DROPPED = "dropped"
    PLANNED = "planned"


def kitsu_status_to_list(
    status: str | None, *, reconsuming: bool = False
) -> ListStatus | None:
    """Convert a Kitsu library entry status to an AniBridge ListStatus.

    Args:
        status (str | None): Raw status string from Kitsu.
        reconsuming (bool): Whether the media is actively being rewatched.

    Returns:
        ListStatus | None: Mapped ListStatus or None.
    """
    if status is None:
        return None

    status_lower = status.lower()
    if status_lower == KitsuStatus.CURRENT:
        return ListStatus.REPEATING if reconsuming else ListStatus.CURRENT
    if status_lower == KitsuStatus.COMPLETED:
        return ListStatus.COMPLETED
    if status_lower == KitsuStatus.ON_HOLD:
        return ListStatus.PAUSED
    if status_lower == KitsuStatus.DROPPED:
        return ListStatus.DROPPED
    if status_lower == KitsuStatus.PLANNED:
        return ListStatus.PLANNING

    return None


def list_status_to_kitsu(status: ListStatus | None) -> tuple[str | None, bool]:
    """Convert an AniBridge ListStatus to a Kitsu status and reconsuming flag.

    Args:
        status (ListStatus | None): AniBridge status to convert.

    Returns:
        tuple[str | None, bool]: (kitsu_status_value, is_reconsuming).
    """
    if status is None:
        return None, False

    if status is ListStatus.CURRENT:
        return KitsuStatus.CURRENT.value, False
    if status is ListStatus.REPEATING:
        return KitsuStatus.CURRENT.value, True
    if status is ListStatus.COMPLETED:
        return KitsuStatus.COMPLETED.value, False
    if status is ListStatus.PAUSED:
        return KitsuStatus.ON_HOLD.value, False
    if status is ListStatus.DROPPED:
        return KitsuStatus.DROPPED.value, False
    if status is ListStatus.PLANNING:
        return KitsuStatus.PLANNED.value, False

    return None, False


def kitsu_rating_to_user_rating(rating_twenty: int | None) -> int | None:
    """Convert Kitsu's ratingTwenty (2..20) to AniBridge 0..100 scale.

    Args:
        rating_twenty (int | None): Kitsu 2-20 scale rating.

    Returns:
        int | None: 0-100 scale rating or None.
    """
    if rating_twenty is None:
        return None
    return max(0, min(100, int(rating_twenty * 5)))


def user_rating_to_kitsu_rating(user_rating: int | None) -> int | None:
    """Convert AniBridge 0..100 scale rating to Kitsu ratingTwenty (2..20).

    Args:
        user_rating (int | None): AniBridge 0-100 scale rating.

    Returns:
        int | None: Kitsu 2-20 scale rating or None.
    """
    if user_rating is None:
        return None
    score = round(user_rating / 5)
    return max(2, min(20, score))


class KitsuTitles(msgspec.Struct, omit_defaults=True):
    """Titles object for a Kitsu anime."""

    en: str | None = None
    en_jp: str | None = None
    ja_jp: str | None = None
    canonicalTitle: str | None = None


class KitsuPosterImage(msgspec.Struct, omit_defaults=True):
    """Poster images object for a Kitsu anime."""

    tiny: str | None = None
    small: str | None = None
    medium: str | None = None
    large: str | None = None
    original: str | None = None


class KitsuAnimeAttributes(msgspec.Struct, omit_defaults=True):
    """Attributes object for a Kitsu anime resource."""

    slug: str | None = None
    synopsis: str | None = None
    titles: KitsuTitles | None = None
    canonicalTitle: str | None = None
    subtype: str | None = None
    status: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    episodeCount: int | None = None
    episodeLength: int | None = None
    posterImage: KitsuPosterImage | None = None


class KitsuAnimeResource(msgspec.Struct):
    """JSON:API resource representing a Kitsu anime."""

    id: str
    type: str = "anime"
    attributes: KitsuAnimeAttributes | None = None


class KitsuLibraryEntryAttributes(msgspec.Struct, omit_defaults=True):
    """Attributes object for a Kitsu library entry."""

    status: str | None = None
    progress: int | None = 0
    reconsuming: bool | None = False
    reconsumeCount: int | None = 0
    notes: str | None = None
    ratingTwenty: int | None = None
    startedAt: str | None = None
    finishedAt: str | None = None


class KitsuRelationshipData(msgspec.Struct):
    """Resource identifier object in a JSON:API relationship."""

    id: str
    type: str


class KitsuRelationship(msgspec.Struct):
    """Relationship object containing relationship data."""

    data: KitsuRelationshipData | None = None


class KitsuLibraryEntryResource(msgspec.Struct):
    """JSON:API resource representing a Kitsu library entry."""

    id: str
    type: str = "libraryEntries"
    attributes: KitsuLibraryEntryAttributes = msgspec.field(
        default_factory=KitsuLibraryEntryAttributes
    )
    relationships: dict[str, Any] | None = None


class KitsuUserAttributes(msgspec.Struct):
    """Attributes object for a Kitsu user."""

    name: str
    slug: str | None = None


class KitsuUserResource(msgspec.Struct):
    """JSON:API resource representing a Kitsu user."""

    id: str
    type: str = "users"
    attributes: KitsuUserAttributes | None = None


class KitsuOAuthTokenResponse(msgspec.Struct):
    """OAuth2 token response from Kitsu."""

    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    expires_in: int | None = None
    scope: str | None = None
    created_at: int | None = None


class KitsuAnimeResponse(msgspec.Struct):
    """JSON:API response containing a single anime resource."""

    data: KitsuAnimeResource
    included: list[Any] = []


class KitsuAnimeListResponse(msgspec.Struct):
    """JSON:API response containing a list of anime resources."""

    data: list[KitsuAnimeResource] = []
    included: list[Any] = []


class KitsuLibraryEntryResponse(msgspec.Struct):
    """JSON:API response containing a single library entry resource."""

    data: KitsuLibraryEntryResource
    included: list[Any] = []


class KitsuLibraryEntriesResponse(msgspec.Struct):
    """JSON:API response containing a list of library entry resources."""

    data: list[KitsuLibraryEntryResource] = []
    included: list[Any] = []


class KitsuUsersResponse(msgspec.Struct):
    """JSON:API response containing a list of user resources."""

    data: list[KitsuUserResource] = []


class KitsuError(msgspec.Struct):
    """JSON:API error object."""

    title: str | None = None
    detail: str | None = None
    status: str | None = None
    code: str | None = None


class KitsuErrorResponse(msgspec.Struct):
    """JSON:API error document."""

    errors: list[KitsuError] = []
