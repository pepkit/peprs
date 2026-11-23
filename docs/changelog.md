# Changes

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [0.2.5] - 2026-11-23
### Added:
- `Project(path)` now falls back to loading `path` as a PEPHub registry (e.g. `"namespace/name:tag"`) when it is not a local YAML/CSV file.
- `Project.add_sample()`: append a single sample to the raw sample table (call `reprocess()` afterward to update processed samples).
- Mutable `Project.config`: edit configuration in place via the `Config` mapping.
- `Project.reprocess()`: re-run sample processing from the in-memory config and raw tables.
- `sample_table` and `subsample_table` properties.
- Amendments are executed automatically after a project is created.

### Changed:
- Updated to Polars 2.0 and added Python 3.10 support.

## [0.2.4] - 2026-07-05
### Fixed:
- Deserialization bug and column type identification in the WASM bindings.

## [0.2.3] - 2026-07-04
### Fixed:
- Config parser of subsample id columns.

## [0.2.2] - 2026-07-02
### Changed:
- Improved error reporting in the eido validation module.

## [0.2.1] - 2026-07-01
### Added:
- New PEPHub authentication/login system.
- `polars` as a Python dependency.

## [0.2.0] - 2026-04-17
### Added:
- `Project.from_sample_yaml()` constructor.
- `sample_name_colname` attribute and sample iteration via `samples`.

### Fixed:
- Validation no longer fails on not-found environment variables.

## [0.1.2] - 2026-04-05
### Added:
- URL schema support for eido and Windows wheels on PyPI.

### Fixed:
- Fetching the raw project in the Python bindings.

## [0.1.1] - 2026-04-04
### Added:
- WebAssembly (WASM) bindings.
- eido validation bindings (`validate_with_pydantic`) and CLI commands (`convert`, `inspect`).
- `Project.from_pandas()` constructor and samples retrieval as `Sample` objects.
- PyPI publishing workflow.

### Changed:
- Removed OpenSSL and reqwest dependencies.

## [0.1.0] - 2025-09-26
### Added:
- Initial release of the `peprs` Python bindings: PEP config/sample/subsample handling, sample modifiers (imply, derive), sample iterators, `from_polars`/`from_dict`/`from_pephub` constructors, and `to_dict`/`to_polars` export.
