# Task Completion Verification

Run the following checks sequentially before concluding any coding task:

1. **Format Code**:
   ```bash
   uv run ruff format src tests
   ```
2. **Lint & Autofix**:
   ```bash
   uv run ruff check --fix src tests
   ```
3. **Validate Formatting**:
   ```bash
   uv run ruff format --check src tests
   ```
4. **Run Test Suite & Coverage**:
   ```bash
   uv run pytest
   ```
5. **Serena Memory Integrity**:
   ```bash
   serena memories check
   ```
