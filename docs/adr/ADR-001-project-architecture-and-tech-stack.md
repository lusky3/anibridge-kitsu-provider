---
description: Project architecture and technology stack for anibridge-kitsu-provider.
applies_to: ["**"]
lifecycle:
  owner: team
  review_cadence: on-event
  review_trigger: architecture changes
  supersedes: none
  superseded_by: none
---

# ADR-001: Project Architecture & Tech Stack

## Status

Accepted

## Date

2026-09-21

## Context

`anibridge-kitsu-provider` provides a Kitsu list provider for the AniBridge ecosystem. It connects AniBridge to Kitsu's API (kitsu.app) to synchronize anime watch history, list statuses, episode progress, ratings, and reviews.

## Decision

### Project Type

Python Provider Library (ListProvider plugin for AniBridge).

### Tech Stack

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Language | Python | >=3.14 | Required by AniBridge core ecosystem |
| Package Manager | uv | >=0.11 | Build backend: `uv_build` |
| Core Framework | anibridge-list-base | >=0.2.0 | Base contracts for ListProvider |
| Shared Utilities | anibridge-utils | >=0.2.0 | Provider logging and registry utilities |
| Network / HTTP | aiohttp | >=3.13.3 | Async client for Kitsu JSON:API & OAuth2 |
| Serialization | msgspec | >=0.21.1 | High performance JSON & Struct models |
| Linter & Formatter | ruff | >=0.15.5 | Formatting (88 chars) and linting |
| Testing Framework | pytest, pytest-asyncio, pytest-cov | >=9.0.2 | Async test suite with coverage |

### Directory Structure

```
src/
└── anibridge/
    └── providers/
        └── list/
            └── kitsu/
                ├── __init__.py
                ├── client.py
                ├── config.py
                ├── list.py
                └── models.py
tests/
├── conftest.py
├── test_client.py
├── test_config.py
├── test_list.py
└── test_models.py
```

### Naming Conventions

- Package namespace: `anibridge.providers.list.kitsu` (PEP 420 namespace package)
- Class naming: `KitsuListProvider`, `KitsuListEntry`, `KitsuListMedia`, `KitsuClient`, `KitsuListProviderConfig`
- Files: snake_case (`list.py`, `client.py`, `models.py`, `config.py`)

### API Design

- External API: Kitsu JSON:API v3 (`https://kitsu.app/api/edge`) and OAuth 2 (`https://kitsu.app/api/oauth/token`)
- Auth: OAuth 2 Password Grant and Bearer token headers (`Authorization: Bearer <token>`)
- Headers: `Accept: application/vnd.api+json`, `Content-Type: application/vnd.api+json`

### Testing

- Framework: `pytest` with `pytest-asyncio` and `pytest-cov`
- Command: `uv run pytest`
- Lint command: `uv run ruff check src tests`
- Format check: `uv run ruff format --check src tests`

## Consequences

- Provider strictly adheres to `anibridge-list-base` contracts.
- Follows reference provider patterns from `anibridge-mal-provider` and `anibridge-anilist-provider`.
