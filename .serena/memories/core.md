# Core Architecture & Map

## Overview
- `anibridge-kitsu-provider` is the Kitsu.app anime list provider for the AniBridge ecosystem.
- Implements `ListProvider` from `anibridge-list-base` to synchronize anime watch history, list status, ratings, and episode progress via Kitsu's JSON:API (`https://kitsu.app/api/edge`).
- Adheres to the standard list provider architecture established in `anibridge-mal-provider` and `anibridge-anilist-provider`.

## Subsystem References
- For language version, package manager, and dependencies, see `mem:tech_stack`.
- For development commands, test runners, and tooling execution, see `mem:suggested_commands`.
- For code style, type annotations, and structural conventions, see `mem:conventions`.
- For the verification gate required before finishing any task, see `mem:task_completion`.

## Source Map
- `src/anibridge/providers/list/kitsu/`: Primary package directory (PEP 420 namespace package `anibridge.providers.list.kitsu`).
  - `list.py`: Implements `KitsuListProvider`, `KitsuListEntry`, `KitsuListMedia`.
  - `client.py`: Async HTTP / JSON:API client for Kitsu OAuth & API endpoints (`https://kitsu.app/api/edge`).
  - `models.py`: Data models and mapping structures using `msgspec.Struct`.
  - `config.py`: Provider configuration parsing (`KitsuListProviderConfig`).
- `tests/`: Unit and integration test suite mirror.
