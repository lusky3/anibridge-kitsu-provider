"""Client for interacting with Kitsu's JSON:API and OAuth endpoints."""

from typing import Any

import aiohttp
import msgspec
from anibridge.utils.limiter import Limiter
from anibridge.utils.types import ProviderLogger

from anibridge.providers.list.kitsu.config import KitsuListProviderConfig
from anibridge.providers.list.kitsu.models import (
    KitsuAnimeListResponse,
    KitsuAnimeResource,
    KitsuAnimeResponse,
    KitsuErrorResponse,
    KitsuLibraryEntriesResponse,
    KitsuLibraryEntryResource,
    KitsuLibraryEntryResponse,
    KitsuOAuthTokenResponse,
    KitsuUserResource,
    KitsuUsersResponse,
)

__all__ = ["KitsuClient"]


class KitsuClient:
    """HTTP client for Kitsu JSON:API and OAuth token authentication."""

    def __init__(
        self,
        *,
        logger: ProviderLogger,
        config: KitsuListProviderConfig,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the Kitsu HTTP client.

        Args:
            logger (ProviderLogger): Injected AniBridge logger.
            config (KitsuListProviderConfig): Provider configuration.
            session (aiohttp.ClientSession | None): Optional existing session.
        """
        self.log = logger
        self.config = config
        self.access_token: str | None = config.token
        self.refresh_token: str | None = None
        self.user: KitsuUserResource | None = None
        self._session = session
        self._owns_session = session is None
        self.limiter = Limiter(rate=max(0.1, config.rate_limit), capacity=5)

        self._anime_cache: dict[str, KitsuAnimeResource] = {}
        self._entry_cache: dict[str, KitsuLibraryEntryResource] = {}

    @property
    def session(self) -> aiohttp.ClientSession:
        """Return the active ClientSession, creating one if not present."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def initialize(self) -> None:
        """Initialize client session and authenticate if required."""
        self.log.debug("Initializing KitsuClient")
        if not self.access_token and self.config.username and self.config.password:
            await self.login(self.config.username, self.config.password)

        if self.access_token:
            self.user = await self.get_current_user()
            self.log.debug(
                "KitsuClient authenticated as user '%s' (id=%s)",
                self.user.attributes.name if self.user.attributes else "",
                self.user.id,
            )

    async def login(self, username: str, password: str) -> KitsuOAuthTokenResponse:
        """Authenticate with Kitsu via OAuth2 password grant.

        Args:
            username (str): Kitsu username or email.
            password (str): Kitsu password.

        Returns:
            KitsuOAuthTokenResponse: The token response.
        """
        self.log.debug(
            "Authenticating with Kitsu OAuth endpoint: %s", self.config.oauth_url
        )
        payload = {
            "grant_type": "password",
            "username": username,
            "password": password,
        }
        await self.limiter.acquire(asynchronous=True)
        async with self.session.post(
            self.config.oauth_url,
            json=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as resp:
            body = await resp.read()
            if resp.status >= 400:
                self.log.error(
                    "Kitsu OAuth login failed with status %s: %s",
                    resp.status,
                    body.decode("utf-8", errors="replace"),
                )
                resp.raise_for_status()

            token_resp = msgspec.json.decode(body, type=KitsuOAuthTokenResponse)
            self.access_token = token_resp.access_token
            self.refresh_token = token_resp.refresh_token
            return token_resp

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> bytes:
        """Send a rate-limited JSON:API request to Kitsu.

        Args:
            method (str): HTTP method.
            url (str): Target URL.
            params (dict[str, Any] | None): Query parameters.
            json_data (dict[str, Any] | None): JSON body.

        Returns:
            bytes: Response body bytes.
        """
        await self.limiter.acquire(asynchronous=True)
        headers = {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        async with self.session.request(
            method,
            url,
            params=params,
            json=json_data,
            headers=headers,
        ) as resp:
            if resp.status == 204:
                return b""

            body = await resp.read()
            if resp.status >= 400:
                err_detail = body.decode("utf-8", errors="replace")
                try:
                    err_doc = msgspec.json.decode(body, type=KitsuErrorResponse)
                    if err_doc.errors:
                        err_detail = "; ".join(
                            e.detail or e.title or f"Error {e.status}"
                            for e in err_doc.errors
                        )
                except Exception:
                    pass
                self.log.error(
                    "Kitsu API %s %s failed [%s]: %s",
                    method,
                    url,
                    resp.status,
                    err_detail,
                )
                resp.raise_for_status()

            return body

    async def get_current_user(self) -> KitsuUserResource:
        """Fetch the authenticated Kitsu user resource.

        Returns:
            KitsuUserResource: The current user.
        """
        url = f"{self.config.base_url}/users"
        data = await self._request("GET", url, params={"filter[self]": "true"})
        resp = msgspec.json.decode(data, type=KitsuUsersResponse)
        if not resp.data:
            raise RuntimeError("Kitsu self user filter returned no user")
        self.user = resp.data[0]
        return self.user

    async def get_anime(self, anime_id: str) -> KitsuAnimeResource | None:
        """Fetch a Kitsu anime resource by ID.

        Args:
            anime_id (str): Kitsu anime ID.

        Returns:
            KitsuAnimeResource | None: Anime resource or None if not found.
        """
        if anime_id in self._anime_cache:
            return self._anime_cache[anime_id]

        url = f"{self.config.base_url}/anime/{anime_id}"
        try:
            data = await self._request("GET", url)
        except aiohttp.ClientResponseError as exc:
            if exc.status == 404:
                return None
            raise

        resp = msgspec.json.decode(data, type=KitsuAnimeResponse)
        self._anime_cache[anime_id] = resp.data
        return resp.data

    async def search_anime(
        self, query: str, limit: int = 10
    ) -> list[KitsuAnimeResource]:
        """Search Kitsu anime resources by text query.

        Args:
            query (str): Search string.
            limit (int): Maximum results to return.

        Returns:
            list[KitsuAnimeResource]: Matching anime resources.
        """
        url = f"{self.config.base_url}/anime"
        params = {"filter[text]": query, "page[limit]": str(limit)}
        data = await self._request("GET", url, params=params)
        resp = msgspec.json.decode(data, type=KitsuAnimeListResponse)
        for anime in resp.data:
            self._anime_cache[anime.id] = anime
        return resp.data

    async def get_library_entry(
        self, user_id: str, anime_id: str
    ) -> tuple[KitsuLibraryEntryResource | None, KitsuAnimeResource | None]:
        """Fetch a user's library entry for a specific anime.

        Args:
            user_id (str): Kitsu user ID.
            anime_id (str): Kitsu anime ID.

        Returns:
            tuple[KitsuLibraryEntryResource | None, KitsuAnimeResource | None]:
                The entry and associated anime if found.
        """
        if anime_id in self._entry_cache:
            return self._entry_cache[anime_id], self._anime_cache.get(anime_id)

        url = f"{self.config.base_url}/library-entries"
        params = {
            "filter[userId]": user_id,
            "filter[animeId]": anime_id,
            "include": "anime",
        }
        data = await self._request("GET", url, params=params)
        resp = msgspec.json.decode(data, type=KitsuLibraryEntriesResponse)

        anime_res: KitsuAnimeResource | None = None
        if resp.included:
            for inc in resp.included:
                if isinstance(inc, dict) and inc.get("type") == "anime":
                    try:
                        raw = msgspec.json.encode(inc)
                        anime_res = msgspec.json.decode(raw, type=KitsuAnimeResource)
                        self._anime_cache[anime_res.id] = anime_res
                    except Exception:
                        pass

        if resp.data:
            entry = resp.data[0]
            self._entry_cache[anime_id] = entry
            return entry, anime_res

        return None, anime_res

    async def create_library_entry(
        self, user_id: str, anime_id: str, attributes: dict[str, Any]
    ) -> KitsuLibraryEntryResource:
        """Create a new library entry on Kitsu.

        Args:
            user_id (str): Kitsu user ID.
            anime_id (str): Kitsu anime ID.
            attributes (dict[str, Any]): Entry attributes to save.

        Returns:
            KitsuLibraryEntryResource: The created entry.
        """
        url = f"{self.config.base_url}/library-entries"
        payload = {
            "data": {
                "type": "libraryEntries",
                "attributes": attributes,
                "relationships": {
                    "user": {"data": {"type": "users", "id": user_id}},
                    "media": {"data": {"type": "anime", "id": anime_id}},
                },
            }
        }
        data = await self._request("POST", url, json_data=payload)
        resp = msgspec.json.decode(data, type=KitsuLibraryEntryResponse)
        self._entry_cache[anime_id] = resp.data
        return resp.data

    async def update_library_entry(
        self, entry_id: str, attributes: dict[str, Any]
    ) -> KitsuLibraryEntryResource:
        """Update an existing library entry on Kitsu.

        Args:
            entry_id (str): Kitsu library entry ID.
            attributes (dict[str, Any]): Modified attributes.

        Returns:
            KitsuLibraryEntryResource: The updated entry.
        """
        url = f"{self.config.base_url}/library-entries/{entry_id}"
        payload = {
            "data": {
                "id": entry_id,
                "type": "libraryEntries",
                "attributes": attributes,
            }
        }
        data = await self._request("PATCH", url, json_data=payload)
        resp = msgspec.json.decode(data, type=KitsuLibraryEntryResponse)
        return resp.data

    async def delete_library_entry(self, entry_id: str) -> None:
        """Delete a library entry from Kitsu.

        Args:
            entry_id (str): Kitsu library entry ID.
        """
        url = f"{self.config.base_url}/library-entries/{entry_id}"
        await self._request("DELETE", url)

    async def get_user_library_entries(
        self, user_id: str, limit: int = 500, offset: int = 0
    ) -> tuple[list[KitsuLibraryEntryResource], list[KitsuAnimeResource], bool]:
        """Fetch a paginated page of library entries for a user.

        Args:
            user_id (str): Kitsu user ID.
            limit (int): Number of entries per page.
            offset (int): Offset for pagination.

        Returns:
            tuple[list[KitsuLibraryEntryResource], list[KitsuAnimeResource], bool]:
                (entries, included_anime, has_more).
        """
        url = f"{self.config.base_url}/library-entries"
        params = {
            "filter[userId]": user_id,
            "page[limit]": str(limit),
            "page[offset]": str(offset),
            "include": "anime",
        }
        data = await self._request("GET", url, params=params)
        resp = msgspec.json.decode(data, type=KitsuLibraryEntriesResponse)

        anime_list: list[KitsuAnimeResource] = []
        if resp.included:
            for inc in resp.included:
                if isinstance(inc, dict) and inc.get("type") == "anime":
                    try:
                        raw = msgspec.json.encode(inc)
                        anime_res = msgspec.json.decode(raw, type=KitsuAnimeResource)
                        self._anime_cache[anime_res.id] = anime_res
                        anime_list.append(anime_res)
                    except Exception:
                        pass

        for entry in resp.data:
            # If relationships has media/anime, cache keyed by anime_id
            if entry.relationships:
                anime_rel = entry.relationships.get("anime") or entry.relationships.get(
                    "media"
                )
                if anime_rel and isinstance(anime_rel, dict):
                    data_rel = anime_rel.get("data")
                    if isinstance(data_rel, dict) and data_rel.get("id"):
                        self._entry_cache[str(data_rel["id"])] = entry

        has_more = len(resp.data) >= limit
        return resp.data, anime_list, has_more

    def clear_cache(self) -> None:
        """Clear local anime and entry caches."""
        self._anime_cache.clear()
        self._entry_cache.clear()

    async def close(self) -> None:
        """Close the underlying ClientSession if owned."""
        if (
            self._owns_session
            and self._session is not None
            and not self._session.closed
        ):
            await self._session.close()
            self._session = None
