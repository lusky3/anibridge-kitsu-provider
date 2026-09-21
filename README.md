# anibridge-kitsu-provider

Kitsu provider for the [AniBridge](https://github.com/anibridge) project. Implements the `anibridge-list-base` interface to sync watch history, list status, and anime metadata with Kitsu (`https://kitsu.app`).

## Installation

```bash
pip install anibridge-kitsu-provider
```

## Configuration

Add a `kitsu` block to your AniBridge configuration:

```yaml
providers:
  kitsu:
    username: your_username # Kitsu account email or slug
    password: your_password # Kitsu account password
    # OR
    token: your_oauth_token # Kitsu OAuth Bearer token
    rate_limit: 1.0         # Max requests per second (default 1.0)
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Lint & formatting
uv run ruff check src tests
uv run ruff format --check src tests
```
