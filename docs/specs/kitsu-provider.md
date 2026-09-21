---
description: Specification for Kitsu List Provider for AniBridge
status: shipped
primary_domain: provider
---

# Feature Specification: Kitsu List Provider

## 1. Goal

Implement the `KitsuListProvider` plugin for AniBridge, enabling users to synchronize their anime watch list, progress, ratings, and statuses with Kitsu (`https://kitsu.app`).

## 2. Acceptance Criteria (AC)

- **AC-1**: `KitsuListProvider` implements the `anibridge.list.ListProvider` interface with `NAMESPACE = "kitsu"` and `MAPPING_PROVIDERS = frozenset({"kitsu"})`.
- **AC-2**: `KitsuListProviderConfig` parses provider configuration options including credentials (`username`, `password`), token (`token`), `rate_limit`, and base URL.
- **AC-3**: `KitsuClient` supports authentication via OAuth2 Password Grant and Bearer token headers, and fetches current user details via `/api/edge/users?filter[self]=true`.
- **AC-4**: `get_entry(key)` retrieves an anime's user library status from `/api/edge/library-entries?filter[userId]=...&filter[animeId]=...&include=anime` and maps it to `KitsuListEntry`.
- **AC-5**: `update_entry(key, entry)` creates (`POST /api/edge/library-entries`) or updates (`PATCH /api/edge/library-entries/{id}`) library entries on Kitsu with delta tracking.
- **AC-6**: `delete_entry(key)` deletes the library entry on Kitsu (`DELETE /api/edge/library-entries/{id}`).
- **AC-7**: `search(query)` queries Kitsu anime search (`/api/edge/anime?filter[text]=...`) and returns matching `KitsuListEntry` objects.
- **AC-8**: Status and rating mapping functions accurately map Kitsu statuses (`current`, `completed`, `on_hold`, `dropped`, `planned`, `reconsuming`) and `ratingTwenty` (2..20) to/from AniBridge `ListStatus` and 0..100 integer ratings.
- **AC-9**: `resolve_mapping_descriptors` converts AniBridge mapping descriptors into `ListTarget` media keys.
- **AC-10**: Full test suite passes with unit tests covering client, config, models, and provider behavior with >=90% test coverage.

## 3. Non-goals

- Manga and drama library synchronization (Kitsu supports manga and drama, but AniBridge focuses on anime).
- Social features (comments, posts, community feeds, followers).
- Direct library exports (`backup_list` can return full list JSON or raise `NotImplementedError` if bulk export is unsupported).

## 4. Constraints

- Must target Python `>=3.14` per AniBridge ecosystem standard.
- Must use `kitsu.app` endpoints rather than deprecated `kitsu.io`.
- Must respect Kitsu rate limits and JSON:API content headers (`application/vnd.api+json`).
- Must pass `ruff check src tests` and `ruff format --check src tests`.

## Domain Decisions

- [DECISION] Inherit from `anibridge.list.ListProvider` (`anibridge-list-base`) rather than deprecated `anibridge-provider-base`.
- [DECISION] Map `ratingTwenty` (2..20) to AniBridge 0..100 via `ratingTwenty * 5`, clamping user ratings to [2, 20] on write.
- [DECISION] Use `msgspec.Struct` for JSON:API payload parsing and serialization for maximum performance.
- [TRADEOFF] Kitsu does not provide an atomic batch endpoint for library entries, so batch methods (`get_entries_batch`, `update_entries_batch`) operate sequentially with error isolation.
- [CONSTRAINT] Kitsu JSON:API requests require `Content-Type: application/vnd.api+json` and `Accept: application/vnd.api+json`.
