# Security Policy

## Supported use

This project is intended for local research, teaching, and demonstration. It
is not hardened for public production deployment.

## Reporting a vulnerability

Please report security concerns privately through GitHub's private security
advisory form for this repository. Include reproduction steps and the affected
version. Do not open a public issue for sensitive findings.

## Handling secrets

- `.env` is excluded by `.gitignore`. Only `.env.example` is published.
- Keep `GEMINI_API_KEY`, `PLANTNET_API_KEY`, and `ADMIN_SECRET_KEY` server-side.
- Replace the placeholder admin secret and generate a real password hash before
  exposing the app to anyone else:

  ```bash
  python run.py hash-password
  ```

- If a key is ever committed or shared, rotate it immediately with the provider.
- Uploaded images and `data/plant_disease.db` are local runtime data and are not
  part of the repository.

## Scope of reports

Please focus on authentication, file handling, and accidental secret exposure.
Model accuracy discussions belong in a regular issue rather than a security
report.
