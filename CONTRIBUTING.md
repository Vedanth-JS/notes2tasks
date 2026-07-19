# Contributing

Thank you for your interest in contributing! Even though this is a solo or portfolio project, contributions are welcome.

## Local Setup

1. Fork and clone the repository.
2. Install dependencies using `uv` or `pip`:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up pre-commit hooks to ensure formatting and linting:
   ```bash
   pre-commit install
   ```

## Development

- We use `black` for formatting and `ruff` for linting.
- Tests are located in the `tests/` directory. Run them with:
  ```bash
  pytest
  ```

## Submitting Pull Requests

1. Create a new branch.
2. Make your changes and add tests if applicable.
3. Submit a PR against the `main` branch.
