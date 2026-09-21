# Suggested Commands

## Dependency Management & Setup
- `uv sync`: Install dependencies and development packages.
- `uv add <package>`: Add runtime dependency.
- `uv add --dev <package>`: Add development dependency.

## Testing & Quality Gates
- `uv run pytest`: Run test suite with coverage report.
- `uv run pytest -k <filter>`: Run tests matching expression.
- `uv run ruff check src tests`: Check lint rules.
- `uv run ruff check --fix src tests`: Apply safe automated lint fixes.
- `uv run ruff format --check src tests`: Validate formatting without modifying files.
- `uv run ruff format src tests`: Reformat source and test files.

## Serena Maintenance
- `serena memories check`: Verify referential integrity of Serena memory graph.
- `serena project health-check`: Inspect language server and tool availability.
