# Tech Stack

- **Language**: Python >= 3.14
- **Package Manager & Build**: `uv` with `uv_build` backend, namespace package `anibridge`
- **Core Dependencies**:
  - `anibridge-list-base>=0.2.0` (List provider abstract classes: `ListProvider`, `ListEntry`, `ListMedia`, `ListStatus`, `ListUser`)
  - `anibridge-utils>=0.2.0` (Provider utilities, types, and registries)
  - `aiohttp>=3.13.3` (async HTTP communication with Kitsu JSON:API & OAuth)
  - `msgspec>=0.21.1` (fast struct-based schema parsing and serialization)
- **Dev Dependencies**:
  - `pytest>=9.0.2`, `pytest-asyncio>=1.3.0`, `pytest-cov>=7.0.0`
  - `ruff>=0.15.5`
- **Language Server**: Serena LSP with Python backend (`python` language server)
