# Contributing

Thank you for your interest in contributing to `search-knowledge-mcp`.

## Development setup
```bash
uv sync --all-extras
cp .env.example .env
# Set OPENAI_API_KEY in .env if you want to run real web searches
```

## Useful commands
### Run tests
```bash
uv run pytest
```

### Run lint
```bash
uv run ruff check .
```

### Run the MCP server
```bash
uv run python -m search_knowledge_mcp.server
```

## Pull request guidelines
- Keep changes as small and reviewable as possible.
- Add or update tests when behavior changes.
- Do not commit secrets such as API keys.
- Update README / docs when user-facing behavior changes.

## Issue reports
Please include:
- OS and Python version
- `uv` version
- Reproduction steps
- Expected behavior
- Actual behavior
- Relevant logs (with secrets redacted)
