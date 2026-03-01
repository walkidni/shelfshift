# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-03-01

### Changed

- Finalized stable runtime configuration precedence across library, CLI, and server:
  - explicit runtime input > environment (`.env`) > defaults.
- Added app-scoped server settings via `create_app(settings=...)` and request-time settings resolution.
- Removed server settings cache coupling so new app instances pick up current environment values.
- Centralized RAPIDAPI key resolution for core URL imports and CLI.
- Updated README quick-start and runtime configuration guidance to match the stable behavior.

## [0.1.0] - 2026-02-18

### Added

- Initial public release of `shelfshift`.
- Core library for URL/CSV import to canonical product models.
- CSV export support for Shopify, BigCommerce, Wix, Squarespace, and WooCommerce.
- CLI commands via `shelfshift`.
- FastAPI server entrypoint via `shelfshift-server`.
