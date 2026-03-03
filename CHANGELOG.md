# Changelog

All notable changes to this project will be documented in this file.

## [1.0.2] - 2026-03-03

### Added

- Added comprehensive `guides/` documentation for both the library and CLI surfaces.
- Added canonical JSON hydration helpers (`json_to_product`, `json_to_products`) and `import_json(...)`.

### Changed

- Migrated the package to a `src/` layout and aligned tooling/lint configuration around it.
- Curated public facade exports to a smaller, convenience-first API surface.
- Removed the hard 5 MB CSV import size cap from core CSV import flows.
- Simplified packaging and README around library + CLI workflows.

### Removed

- Removed the deprecated server/web stack (`shelfshift.server`, web assets, and `shelfshift-server` entrypoint).
- Removed Amazon and AliExpress URL import backends and RapidAPI-driven CLI/core flow (URL import remains for Shopify, WooCommerce, and Squarespace).
- Removed deprecated `include_raw` behavior and canonical `raw` payload fields.

## [1.0.1] - 2026-03-01

### Changed

- Lowered the declared minimum supported Python version to `>=3.10`.

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
