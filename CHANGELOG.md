# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-18

### Added

- Local-first FastAPI web application with a server-rendered dashboard and admin panel.
- Trained 38-class Keras model inference with 128 × 128 RGB preprocessing and optional test-time augmentation.
- Local disease reference library with symptoms, severity, actions, and prevention guidance.
- SQLite-backed identification history with search, filters, detail view, and deletion.
- Image validation for format, size, dimensions, blur, and basic leaf-likeness.
- Optional backend support services for plants outside the trained reference set.
- Optional Open-Meteo weather context.
- Automated smoke test suite covering health, library, uploads, detection, history, admin access, and fallback behavior.
- Academic documentation: README, architecture, API reference, dataset notes, security policy, contribution guide, and citation metadata.
- GitHub CI workflow, issue templates, pull request template, and code of conduct.

### Changed

- User interface language is deliberately academic and free of product-style terminology.
- Result presentation standardized into seven research-oriented sections.
- Configuration consolidated into a single sanitized `.env.example` and canonical `requirements.txt`.
- Training notebooks moved to `notebooks/`; screenshot moved to `docs/assets/`.

### Removed

- Legacy experimental frontend/backend folders from the published repository.
- Duplicate model, data, and requirement files from the published repository.

### Security

- API keys, admin secrets, local database, and uploaded images are excluded from version control.
- Default example configuration no longer ships a precomputed admin password hash.
