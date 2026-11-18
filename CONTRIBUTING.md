# Contributing

Thanks for your interest in this academic study project.

## Scope

This repository publishes the current FastAPI-based application. The older
`client/`, `server/`, and `ml-service/` experiments are intentionally excluded
from the public repository.

## Development setup

1. Create a Python 3.12 virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and adjust local settings.
4. Run `python run.py check` before starting the server.
5. Run the smoke tests before opening a pull request:

   ```bash
   python -m unittest discover -s tests -v
   ```

## Guidelines

- Keep user-facing language simple, academic, and free of product-style jargon.
- Do not commit `.env`, API keys, passwords, the SQLite database, or uploads.
- Keep backend changes backward-compatible with the existing API responses.
- Add or update docstrings when introducing new modules or complex functions.
- Update the relevant file in `docs/` when behavior changes.

## Reporting issues

Please open a GitHub issue with:

- your OS and Python version;
- exact reproduction steps;
- expected and observed behavior;
- relevant logs with secrets removed.
