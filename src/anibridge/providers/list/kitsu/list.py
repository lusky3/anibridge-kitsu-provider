"""Kitsu list provider implementation for AniBridge."""

import copy
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Self, cast

import msgspec
from anibridge.list import (
    ListEntry,
    ListMedia,
    ListMediaType,
    ListProvider,
    ListStatus,
    ListTarget,
    ListUser,
)
from anibridge.utils.types import MappingDescriptor, ProviderLogger

from anibridge.providers.list.kitsu.client import KitsuClient
from anibridge.providers.list.kitsu.config import KitsuListProviderConfig
from anibridge.providers.list.kitsu.models import (
    KitsuAnimeResource,
    KitsuLibraryEntryAttributes,
    KitsuLibraryEntryResource,
    kitsu_rating_to_user_rating,
    kitsu_status_to_list,
    list_status_to_kitsu,
    user_rating_to_kitsu_rating,
)

__all__ = ["KitsuListEntry", "KitsuListMedia", "KitsuListProvider"]


def _get_anime_title(anime: KitsuAnimeResource) -> str:
    """Extract the best display title from a Kitsu anime resource."""
    if anime.attributes is None:
        return f"Anime {anime.id}"
    if anime.attributes.canonicalTitle:
        return anime.attributes.canonicalTitle
    if anime.attributes.titles:
        for t in (
            anime.attributes.titles.canonicalTitle,
            anime.attributes.titles.en,
            anime.attributes.titles.en_jp,
            anime.attributes.titles.ja_jp,
        ):
            if t:
                return t
    if anime.attributes.slug:
        return anime.attributes.slug.replace("-", " ").title()
    return f"Anime {anime.id}"


class KitsuListMedia(ListMedia["KitsuListProvider"]):
    """AniBridge media wrapper for Kitsu anime resources."""

    def __init__(self, provider: KitsuListProvider, anime: KitsuAnimeResource) -> None:
        """Initialize the Kitsu media wrapper.

        Args:
            provider (KitsuListProvider): The list provider instance.
            anime (KitsuAnimeResource): The raw Kitsu anime resource.
        """
        title = _get_anime_title(anime)
        super().__init__(provider, str(anime.id), title)
        self._anime = anime

    @property
    def external_url(self) -> str | None:
        """Return the external URL for the media on Kitsu."""
        return f"https://kitsu.app/anime/{self.key}"

    @property
    def labels(self) -> Sequence[str]:
        """Return any labels associated with the media (e.g. year, format, status)."""
        labels: list[str] = []
        if self._anime.attributes is None:
            return labels
        if self._anime.attributes.startDate:
            labels.append(self._anime.attributes.startDate[:4])
        if self._anime.attributes.subtype:
            labels.append(self._anime.attributes.subtype.replace("_", " ").title())
        if self._anime.attributes.status:
            labels.append(self._anime.attributes.status.replace("_", " ").title())
        return labels

    @property
    def media_type(self) -> ListMediaType:
        """Get the type of media (e.g., TV, MOVIE)."""
        if self._anime.attributes and self._anime.attributes.subtype:
            subtype = self._anime.attributes.subtype.lower()
            if subtype in ("movie", "special"):
                return ListMediaType.MOVIE
        return ListMediaType.TV

    @property
    def total_units(self) -> int | None:
        """Return the total number of units (episodes) for the media."""
        if self._anime.attributes and self._anime.attributes.episodeCount is not None:
            return self._anime.attributes.episodeCount
        if self.media_type is ListMediaType.MOVIE:
            return 1
        return None

    @property
    def poster_image(self) -> str | None:
        """Return the best available cover image URL for the media."""
        if self._anime.attributes is None or self._anime.attributes.posterImage is None:
            return None
        img = self._anime.attributes.posterImage
        return img.medium or img.large or img.original or img.small or img.tiny

    def provider(self) -> KitsuListProvider:
        """Return the provider associated with this media item."""
        return self._provider


class KitsuListEntry(ListEntry["KitsuListProvider"]):
    """AniBridge list entry backed by Kitsu library entries."""

    def __init__(
        self,
        provider: KitsuListProvider,
        anime: KitsuAnimeResource,
        entry: KitsuLibraryEntryResource | None = None,
    ) -> None:
        """Initialize the Kitsu list entry.

        Args:
            provider (KitsuListProvider): The list provider instance.
            anime (KitsuAnimeResource): The associated anime resource.
            entry (KitsuLibraryEntryResource | None):
                Existing library entry if present.
        """
        title = _get_anime_title(anime)
        super().__init__(provider, str(anime.id), title)
        self._anime = anime
        self._media = KitsuListMedia(provider, anime)
        if entry is None:
            entry = KitsuLibraryEntryResource(
                id="",
                type="libraryEntries",
                attributes=KitsuLibraryEntryAttributes(),
            )
        self._entry = entry
        self._changed_fields: set[str] = set()

    def __copy__(self) -> Self:
        """Return an isolated copy of the list entry."""
        anime = copy.deepcopy(self._anime)
        entry = copy.deepcopy(self._entry)
        copied = type(self)(self._provider, anime=anime, entry=entry)
        copied._changed_fields = self._changed_fields.copy()
        return copied

    @property
    def status(self) -> ListStatus | None:
        """Watch status for the entry."""
        return kitsu_status_to_list(
            self._entry.attributes.status,
            reconsuming=bool(self._entry.attributes.reconsuming),
        )

    @status.setter
    def status(self, value: ListStatus | None) -> None:
        """Update the status for the entry."""
        kitsu_status, reconsuming = list_status_to_kitsu(value)
        self._entry.attributes.status = kitsu_status
        self._entry.attributes.reconsuming = reconsuming
        self._changed_fields.add("status")

    @property
    def progress(self) -> int:
        """Progress integer (episodes watched)."""
        return self._entry.attributes.progress or 0

    @progress.setter
    def progress(self, value: int | None) -> None:
        """Update the progress integer for the entry."""
        if value is not None and value < 0:
            raise ValueError("Progress cannot be negative.")
        self._entry.attributes.progress = value
        self._changed_fields.add("progress")

    @property
    def repeats(self) -> int:
        """Repeat count for the entry."""
        return self._entry.attributes.reconsumeCount or 0

    @repeats.setter
    def repeats(self, value: int | None) -> None:
        """Update the repeat count for the entry."""
        if value is not None and value < 0:
            raise ValueError("Repeat count cannot be negative.")
        self._entry.attributes.reconsumeCount = value
        self._changed_fields.add("repeats")

    @property
    def review(self) -> str | None:
        """Review/notes for the entry."""
        return self._entry.attributes.notes

    @review.setter
    def review(self, value: str | None) -> None:
        """Update the review/notes for the entry."""
        self._entry.attributes.notes = value
        self._changed_fields.add("review")

    @property
    def user_rating(self) -> int | None:
        """User rating on a 0-100 scale."""
        return kitsu_rating_to_user_rating(self._entry.attributes.ratingTwenty)

    @user_rating.setter
    def user_rating(self, value: int | None) -> None:
        """Update user rating on a 0-100 scale."""
        if value is not None and (value < 0 or value > 100):
            raise ValueError("Ratings must be between 0 and 100.")
        self._entry.attributes.ratingTwenty = user_rating_to_kitsu_rating(value)
        self._changed_fields.add("user_rating")

    @property
    def started_at(self) -> datetime | None:
        """Timestamp when the user started the entry."""
        raw = self._entry.attributes.startedAt
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
        except Exception:
            return None

    @started_at.setter
    def started_at(self, value: datetime | None) -> None:
        """Update the start timestamp for the entry."""
        if value is None:
            self._entry.attributes.startedAt = None
        else:
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            else:
                value = value.astimezone(UTC)
            self._entry.attributes.startedAt = value.isoformat().replace("+00:00", "Z")
        self._changed_fields.add("started_at")

    @property
    def finished_at(self) -> datetime | None:
        """Timestamp when the user completed the entry."""
        raw = self._entry.attributes.finishedAt
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
        except Exception:
            return None

    @finished_at.setter
    def finished_at(self, value: datetime | None) -> None:
        """Update the completion timestamp for the entry."""
        if value is None:
            self._entry.attributes.finishedAt = None
        else:
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            else:
                value = value.astimezone(UTC)
            self._entry.attributes.finishedAt = value.isoformat().replace("+00:00", "Z")
        self._changed_fields.add("finished_at")

    @property
    def total_units(self) -> int | None:
        """Total units for the media."""
        return self._media.total_units

    def media(self) -> KitsuListMedia:
        """Get the media item associated with this entry."""
        return self._media

    def provider(self) -> KitsuListProvider:
        """Get the provider associated with this entry."""
        return self._provider


class KitsuListProvider(ListProvider):
    """List provider implementation backed by Kitsu's JSON:API."""

    NAMESPACE = "kitsu"
    MAPPING_PROVIDERS = frozenset({"kitsu"})

    def __init__(self, *, logger: ProviderLogger, config: dict | None = None) -> None:
        """Initialize the Kitsu list provider.

        Args:
            logger (ProviderLogger): Injected AniBridge logger.
            config (dict | None): Provider configuration dictionary.
        """
        super().__init__(logger=logger, config=config)
        self.parsed_config = msgspec.convert(config or {}, type=KitsuListProviderConfig)
        self._client = KitsuClient(logger=self.log, config=self.parsed_config)
        self._user: ListUser | None = None

    async def initialize(self) -> None:
        """Asynchronously initialize the provider and authenticate client."""
        self.log.debug("Initializing KitsuListProvider")
        await self._client.initialize()
        if self._client.user is not None:
            name = (
                self._client.user.attributes.name
                if self._client.user.attributes
                else ""
            )
            self._user = ListUser(key=str(self._client.user.id), title=name)
            self.log.debug(
                "KitsuListProvider initialized for user id=%s (%s)",
                self._user.key,
                self._user.title,
            )

    async def backup_list(self) -> str:
        """Backup the user's entire library list from Kitsu.

        Returns:
            str: JSON string containing list entries.
        """
        if not self._user:
            raise RuntimeError("Cannot backup list without an authenticated user")

        self.log.debug("Starting Kitsu library backup for user %s", self._user.key)
        all_entries: list[dict[str, Any]] = []
        offset = 0
        limit = 500

        while True:
            entries, _, has_more = await self._client.get_user_library_entries(
                user_id=self._user.key, limit=limit, offset=offset
            )
            for entry in entries:
                all_entries.append(
                    {
                        "id": entry.id,
                        "attributes": msgspec.to_builtins(entry.attributes),
                        "relationships": entry.relationships,
                    }
                )
            if not has_more or not entries:
                break
            offset += limit

        self.log.debug(
            "Completed Kitsu library backup with %s entries", len(all_entries)
        )
        return json.dumps(all_entries, separators=(",", ":"))

    async def restore_list(self, backup: str) -> None:
        """Restore library entries from a serialized backup JSON string.

        Args:
            backup (str): Serialized backup string.
        """
        if not self._user:
            raise RuntimeError("Cannot restore list without an authenticated user")

        data: list[dict[str, Any]] = json.loads(backup)
        self.log.debug("Restoring Kitsu library backup with %s entries", len(data))

        for item in data:
            entry_id = item.get("id")
            attrs = item.get("attributes", {})
            rels = item.get("relationships", {})
            media_rel = rels.get("anime") or rels.get("media") or {}
            media_data = media_rel.get("data") if isinstance(media_rel, dict) else None
            anime_id = (
                str(media_data.get("id")) if isinstance(media_data, dict) else None
            )

            if entry_id:
                try:
                    await self._client.update_library_entry(entry_id, attrs)
                except Exception:
                    if anime_id:
                        await self._client.create_library_entry(
                            self._user.key, anime_id, attrs
                        )
            elif anime_id:
                await self._client.create_library_entry(self._user.key, anime_id, attrs)

    async def delete_entry(self, key: str) -> None:
        """Delete a library entry by its media key.

        Args:
            key (str): Unique media key (anime ID).
        """
        if not self._user:
            self.log.debug("Skipping delete_entry for %s: no user", key)
            return

        entry, _ = await self._client.get_library_entry(self._user.key, key)
        if entry is None or not entry.id:
            self.log.debug("No Kitsu library entry found to delete for anime %s", key)
            return

        await self._client.delete_library_entry(entry.id)
        if key in self._client._entry_cache:
            del self._client._entry_cache[key]
        self.log.debug("Deleted Kitsu library entry %s for anime %s", entry.id, key)

    async def resolve_mapping_descriptors(
        self, descriptors: Sequence[MappingDescriptor]
    ) -> Sequence[ListTarget]:
        """Resolve mapping descriptors into list media keys.

        Args:
            descriptors (Sequence[MappingDescriptor]): Descriptors to resolve.

        Returns:
            Sequence[ListTarget]: Resolved targets.
        """
        return [
            ListTarget(descriptor=(provider, entry_id, scope), media_key=entry_id)
            for provider, entry_id, scope in descriptors
            if provider in self.MAPPING_PROVIDERS and entry_id
        ]

    async def get_entry(self, key: str) -> KitsuListEntry | None:
        """Retrieve a list entry by its media key.

        Args:
            key (str): Unique media key (anime ID).

        Returns:
            KitsuListEntry | None: The entry or None if the anime doesn't exist.
        """
        anime = await self._client.get_anime(key)
        if anime is None:
            return None

        entry: KitsuLibraryEntryResource | None = None
        if self._user is not None:
            entry, _ = await self._client.get_library_entry(self._user.key, key)

        return KitsuListEntry(self, anime=anime, entry=entry)

    async def get_entries_batch(
        self, keys: Sequence[str]
    ) -> Sequence[KitsuListEntry | None]:
        """Retrieve multiple list entries by their media keys.

        Args:
            keys (Sequence[str]): Media keys to fetch.

        Returns:
            Sequence[KitsuListEntry | None]: Sequence of entries matching input order.
        """
        entries: list[KitsuListEntry | None] = []
        for key in keys:
            try:
                entry = await self.get_entry(key)
            except Exception:
                self.log.exception("Error fetching entry for anime key '%s'", key)
                entry = None
            entries.append(entry)
        return entries

    async def search(self, query: str) -> Sequence[KitsuListEntry]:
        """Search Kitsu for anime entries matching the query.

        Args:
            query (str): Search string.

        Returns:
            Sequence[KitsuListEntry]: Matching entries.
        """
        animes = await self._client.search_anime(query, limit=10)
        results: list[KitsuListEntry] = []
        for anime in animes:
            entry = self._client._entry_cache.get(anime.id)
            results.append(KitsuListEntry(self, anime=anime, entry=entry))
        self.log.debug("Kitsu search for %r returned %s results", query, len(results))
        return tuple(results)

    async def update_entry(
        self, key: str, entry: ListEntry[Self]
    ) -> KitsuListEntry | None:
        """Update a list entry with new information.

        Args:
            key (str): Media key (anime ID).
            entry (ListEntry): Entry with updated data.

        Returns:
            KitsuListEntry | None: Updated entry or None if failed.
        """
        kitsu_entry = cast(KitsuListEntry, entry)
        changed = kitsu_entry._changed_fields.copy()

        # If no fields changed and entry already has an ID, return as is
        if not changed and kitsu_entry._entry.id:
            self.log.debug("No fields modified for Kitsu entry %s", key)
            return kitsu_entry

        attrs: dict[str, Any] = {}
        if "status" in changed:
            attrs["status"] = kitsu_entry._entry.attributes.status
            attrs["reconsuming"] = kitsu_entry._entry.attributes.reconsuming
        if "progress" in changed:
            attrs["progress"] = kitsu_entry._entry.attributes.progress
        if "repeats" in changed:
            attrs["reconsumeCount"] = kitsu_entry._entry.attributes.reconsumeCount
        if "review" in changed:
            attrs["notes"] = kitsu_entry._entry.attributes.notes
        if "user_rating" in changed:
            attrs["ratingTwenty"] = kitsu_entry._entry.attributes.ratingTwenty
        if "started_at" in changed:
            attrs["startedAt"] = kitsu_entry._entry.attributes.startedAt
        if "finished_at" in changed:
            attrs["finishedAt"] = kitsu_entry._entry.attributes.finishedAt

        if not kitsu_entry._entry.id:
            if not self._user:
                raise RuntimeError(
                    "Cannot create library entry without authenticated user"
                )
            if "status" not in attrs and kitsu_entry._entry.attributes.status:
                attrs["status"] = kitsu_entry._entry.attributes.status
            elif "status" not in attrs:
                attrs["status"] = "planned"
            created = await self._client.create_library_entry(
                user_id=self._user.key, anime_id=key, attributes=attrs
            )
            kitsu_entry._entry = created
        else:
            updated = await self._client.update_library_entry(
                entry_id=kitsu_entry._entry.id, attributes=attrs
            )
            kitsu_entry._entry = updated

        kitsu_entry._changed_fields.clear()
        self.log.debug("Updated Kitsu library entry for anime %s", key)
        return kitsu_entry

    async def update_entries_batch(
        self, entries: Sequence[ListEntry[Self]]
    ) -> Sequence[KitsuListEntry | None]:
        """Update multiple entries in sequence.

        Args:
            entries (Sequence[ListEntry]): Entries to update.

        Returns:
            Sequence[KitsuListEntry | None]: Updated entries.
        """
        results: list[KitsuListEntry | None] = []
        for entry in entries:
            try:
                res = await self.update_entry(entry.media().key, entry)
            except Exception:
                self.log.exception(
                    "Error updating Kitsu entry for key '%s'", entry.media().key
                )
                res = None
            results.append(res)
        return results

    def user(self) -> ListUser | None:
        """Return the associated user object if authenticated."""
        return self._user

    async def clear_cache(self) -> None:
        """Clear cached data held by the provider."""
        self._client.clear_cache()
        self.log.debug("Cleared Kitsu provider cache")

    async def close(self) -> None:
        """Close provider resources."""
        await self._client.close()
        self.log.debug("Closed Kitsu provider client")
