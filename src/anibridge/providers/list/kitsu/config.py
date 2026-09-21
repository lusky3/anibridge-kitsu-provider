"""Configuration models for the Kitsu list provider."""

import msgspec

__all__ = ["KitsuListProviderConfig"]


class KitsuListProviderConfig(msgspec.Struct, kw_only=True):
    """Configuration options for Kitsu list provider.

    Attributes:
        token (str | None): Existing OAuth Bearer token.
        username (str | None): Kitsu username, email, or slug for OAuth password grant.
        password (str | None): Kitsu password for OAuth password grant.
        rate_limit (float): Max requests per second. Defaults to 1.0.
        base_url (str): Base URL for Kitsu JSON:API. Defaults to 'https://kitsu.app/api/edge'.
        oauth_url (str): URL for Kitsu OAuth endpoint. Defaults to 'https://kitsu.app/api/oauth/token'.
    """

    token: str | None = None
    username: str | None = None
    password: str | None = None
    rate_limit: float = 1.0
    base_url: str = "https://kitsu.app/api/edge"
    oauth_url: str = "https://kitsu.app/api/oauth/token"
