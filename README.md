# anibridge-kitsu-provider

[![CI](https://github.com/lusky3/anibridge-kitsu-provider/actions/workflows/ci.yml/badge.svg)](https://github.com/lusky3/anibridge-kitsu-provider/actions/workflows/ci.yml)
[![Security](https://github.com/lusky3/anibridge-kitsu-provider/actions/workflows/security.yml/badge.svg)](https://github.com/lusky3/anibridge-kitsu-provider/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)

Kitsu anime list provider for the [AniBridge](https://github.com/anibridge) ecosystem. Implements `anibridge-list-base` to synchronize anime watch history, list statuses, episode progress, and user ratings with [Kitsu](https://kitsu.app).

## Features

- **Standard Interface**: Implements AniBridge's `ListProvider` specification (`NAMESPACE = "kitsu"`).
- **Modern Kitsu API**: Connects to Kitsu v3 JSON:API (`https://kitsu.app/api/edge`).
- **Flexible Authentication**: Supports OAuth 2 Password Grant (username + password) or pre-generated Bearer tokens.
- **Bi-directional Status & Rating Mapping**: Converts Kitsu statuses (`current`, `completed`, `on_hold`, `dropped`, `planned`, `reconsuming`) and `ratingTwenty` (2..20) to/from AniBridge `ListStatus` and 0..100 ratings.
- **Delta Change Tracking**: Tracks modified fields in `KitsuListEntry` to minimize network payload on updates.
- **Mapping Resolution**: Resolves Kitsu IDs to AniBridge `ListTarget` descriptors.

## Installation

```bash
pip install anibridge-kitsu-provider
```

Or using `uv`:

```bash
uv add anibridge-kitsu-provider
```

## Configuration

Add a `kitsu` block to your AniBridge configuration file:

```yaml
providers:
  kitsu:
    # Option A: Username + Password (uses OAuth2 Password Grant)
    username: your_username # Kitsu username, email, or user slug
    password: your_password # Kitsu account password

    # Option B: Bearer token (preferred if you have a pre-existing token)
    # token: your_oauth_token

    rate_limit: 1.0         # Max requests per second (default 1.0)
    base_url: https://kitsu.app/api/edge
```

### Configuration Options

| Option | Type | Default | Description |
|---|---|---|---|
| `username` | `str \| null` | `null` | Kitsu email, slug, or username for password grant. |
| `password` | `str \| null` | `null` | Kitsu account password for password grant. |
| `token` | `str \| null` | `null` | Kitsu OAuth2 Bearer token (alternative to password grant). |
| `rate_limit` | `float` | `1.0` | Maximum API requests per second. |
| `base_url` | `str` | `https://kitsu.app/api/edge` | Kitsu JSON:API root endpoint. |
| `oauth_url` | `str` | `https://kitsu.app/api/oauth/token` | Kitsu OAuth2 token endpoint. |

### How to Authenticate with Kitsu

Kitsu does not offer static "API Keys" generated through a web dashboard. Instead, it uses **OAuth 2.0**. You have two options for setting up authentication:

#### Option 1: Username & Password (Recommended & Fully Automated)
Set your Kitsu login email (or username) and password in the AniBridge configuration:
```yaml
providers:
  kitsu:
    username: your_email@example.com
    password: your_kitsu_password
```
When AniBridge starts, `anibridge-kitsu-provider` automatically contacts `https://kitsu.app/api/oauth/token`, exchanges your credentials for a Bearer access token, and manages authentication headers behind the scenes.

#### Option 2: Pre-generated Bearer Token
If you prefer not to store your Kitsu password in configuration files, you can manually generate a Bearer token via `curl`:

```bash
curl -X POST https://kitsu.app/api/oauth/token \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "grant_type": "password",
    "username": "your_email@example.com",
    "password": "your_password"
  }'
```

Kitsu will respond with a JSON object:
```json
{
  "access_token": "2f8b...",
  "token_type": "bearer",
  "expires_in": 7200,
  "refresh_token": "4a1c...",
  "scope": "public",
  "created_at": 1726880000
}
```
Copy the `"access_token"` string and supply it to your AniBridge configuration:
```yaml
providers:
  kitsu:
    token: "2f8b..."
```
*(Note: Bearer tokens generated this way expire based on Kitsu's token lifecycle, so Option 1 is recommended for unattended, long-running sync setups.)*

## Status Mapping

AniBridge normalizes list statuses across different anime tracking services. The mapping for Kitsu is:

### Reading from Kitsu

| Kitsu Status | `reconsuming` | AniBridge `ListStatus` |
|---|---|---|
| `current` | `false` | `CURRENT` |
| `current` | `true` | `REPEATING` |
| `completed` | *any* | `COMPLETED` |
| `on_hold` | *any* | `PAUSED` |
| `dropped` | *any* | `DROPPED` |
| `planned` | *any* | `PLANNING` |

### Writing to Kitsu

| AniBridge `ListStatus` | Kitsu Status | `reconsuming` |
|---|---|---|
| `CURRENT` | `current` | `false` |
| `COMPLETED` | `completed` | `false` |
| `PAUSED` | `on_hold` | `false` |
| `DROPPED` | `dropped` | `false` |
| `PLANNING` | `planned` | `false` |
| `REPEATING` | `current` | `true` |

## Rating Conversion

- **Kitsu scale**: Kitsu represents ratings using `ratingTwenty`, an integer scale from `2` to `20` (in steps of 1 or 2).
- **AniBridge scale**: Normalized integer scale from `0` to `100`.
- **Reading**: `user_rating = ratingTwenty * 5` (e.g., `2` becomes `10`, `20` becomes `100`).
- **Writing**: `ratingTwenty = max(2, min(20, round(user_rating / 5)))` (values outside `[2, 20]` are clamped).

## Limitations

- **Anime Only**: AniBridge focuses on anime libraries; manga and drama synchronization are out of scope.
- **Rate Limiting**: Kitsu enforces API rate boundaries. The provider defaults to 1.0 request/second token bucket throttling.
- **Sequential Batch Operations**: Kitsu JSON:API does not provide an atomic multi-entry bulk update endpoint. Batch operations execute sequentially with isolated error handling.

## Development

```bash
# Install dependencies
uv sync

# Run tests with coverage
uv run pytest

# Run linter
uv run ruff check src tests

# Check code formatting
uv run ruff format --check src tests
```

## Releasing

Publishing to PyPI is automated via [`.github/workflows/publish.yml`](.github/workflows/publish.yml) using PyPI Trusted Publishing (OIDC).

A built-in verification gate prevents accidental or malformed releases:
1. The release tag (e.g. `v0.1.0`) must match the `version` field in `pyproject.toml`.
2. `CHANGELOG.md` must be updated with an entry for the target version.
3. If either check fails, the workflow aborts before building or uploading to PyPI.

To release a new version:
```bash
# 1. Update version in pyproject.toml and add release notes to CHANGELOG.md
# 2. Commit the changes
git commit -am "chore(release): v0.1.0"

# 3. Tag and push
git tag v0.1.0
git push origin v0.1.0
```

## Security

Please report any security issues privately via GitHub Private Vulnerability Reporting. See [SECURITY.md](SECURITY.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
