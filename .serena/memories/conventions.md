# Code & Design Conventions

## Architecture
- **Namespace Packaging**: Package resides under `anibridge.providers.list.kitsu`. Use standard PEP 420 namespace structure.
- **Provider Class**: `KitsuListProvider` inheriting `anibridge.list.ListProvider` (`NAMESPACE = "kitsu"`, `MAPPING_PROVIDERS = frozenset({"kitsu"})`).
- **Entity Classes**: `KitsuListEntry(ListEntry[KitsuListProvider])` and `KitsuListMedia(ListMedia[KitsuListProvider])`.
- **Async Execution**: Network operations and provider methods must be non-blocking async functions (`async def`).
- **Kitsu API Domain**:
  - API Base URL: `https://kitsu.app/api/edge`
  - OAuth Base URL: `https://kitsu.app/api/oauth/token`
  - Headers: `Accept: application/vnd.api+json`, `Content-Type: application/vnd.api+json`
- **Status & Rating Mappings**:
  - Status: `current` (`reconsuming: false` -> `CURRENT`, `true` -> `REPEATING`), `completed` -> `COMPLETED`, `on_hold` -> `PAUSED`, `dropped` -> `DROPPED`, `planned` -> `PLANNING`.
  - Rating: Kitsu uses `ratingTwenty` (2..20 scale, 1 point = 5%). Mapped to AniBridge 0..100 scale: `user_rating = ratingTwenty * 5`, `ratingTwenty = round(user_rating / 5)`.
- **Change Tracking**: Use `_changed_fields: set[str]` in `KitsuListEntry` to minimize network payloads and avoid sending unmodified fields on `update_entry`.

## Code Style & Formatting
- **Line Length**: 88 characters.
- **Indentation**: 4 spaces, spaces only.
- **Quotes**: Double quotes (`"`).
- **Docstrings**: Google convention (`pydocstyle.convention = "google"`). Tests do not require docstrings.
- **Type Annotations**: Strict typing on all signatures, models, and public interfaces.
