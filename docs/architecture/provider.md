---
domain: provider
status: living
description: Architecture overview and domain boundaries for AniBridge providers.
lifecycle:
  owner: team
  review_cadence: on-event
  review_trigger: architecture changes
  supersedes: none
  superseded_by: none
---

# Domain Architecture: Provider

## Overview

AniBridge providers bridge media servers and list tracking services using standardized base interfaces (`anibridge-list-base` and `anibridge-library-base`).

## Boundaries & Invariants

- List providers implement `anibridge.list.ListProvider`.
- All network and API communication is async (`async def`).
- Provider namespace packages follow `anibridge.providers.list.<name>`.
- Rating scale is normalized to 0..100 across AniBridge; provider-specific scales (e.g. Kitsu ratingTwenty 2..20) are mapped bidirectionally with clamping.
- Status values map to `anibridge.list.ListStatus` (`CURRENT`, `COMPLETED`, `PAUSED`, `DROPPED`, `PLANNING`, `REPEATING`).
