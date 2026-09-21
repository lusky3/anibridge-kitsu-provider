# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-21

### Added
- Initial release of `anibridge-kitsu-provider` for Kitsu.app.
- Full implementation of AniBridge `ListProvider` protocol adhering to `anibridge-list-base>=0.2.0`.
- Asynchronous HTTP/JSON:API client (`KitsuClient`) supporting OAuth2 password grant and Bearer token authentication.
- Complete CRUD operations for anime library entries (`get_entry`, `update_entry`, `delete_entry`, `get_entries_batch`, `update_entries_batch`).
- Full mapping descriptor resolution (`resolve_mapping_descriptors`) to Kitsu `ListTarget`.
- Bidirectional status mapping (`current`, `completed`, `on_hold`, `dropped`, `planned`, `reconsuming` ↔ AniBridge `ListStatus`).
- Bidirectional 0..100 integer rating conversion with Kitsu's `ratingTwenty` (2..20) scale.
- Anime search support (`search`).
- Comprehensive unit test suite with 94% code coverage and strict ruff lint/format enforcement.
