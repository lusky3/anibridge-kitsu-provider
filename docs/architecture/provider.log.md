### [provider][2026-09-21][main]
source_spec: docs/specs/kitsu-provider.md
source_sha: 5e9a29cc7aa3f5f8b16b52bbe8b4c6cb4fc6c472

- [DECISION] Inherit from `anibridge.list.ListProvider` (`anibridge-list-base`) rather than deprecated `anibridge-provider-base`.
- [DECISION] Map `ratingTwenty` (2..20) to AniBridge 0..100 via `ratingTwenty * 5`, clamping user ratings to [2, 20] on write.
- [DECISION] Use `msgspec.Struct` for JSON:API payload parsing and serialization for maximum performance.
- [TRADEOFF] Kitsu does not provide an atomic batch endpoint for library entries, so batch methods (`get_entries_batch`, `update_entries_batch`) operate sequentially with error isolation.
- [CONSTRAINT] Kitsu JSON:API requests require `Content-Type: application/vnd.api+json` and `Accept: application/vnd.api+json`.
