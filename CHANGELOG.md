# Changelog

All notable changes to this project will be documented in this file.

## [4.2.0] - 2026-05-15

### Fixed
- **Purifier**: Corrected platform key mismatch (`gemini` -> `gemini_cli`) in `scripts/purifier.py` that caused legacy environment detection failure.
- **Generator**: Updated Gemini CLI command projection to use `.toml` format for compatibility with Gemini CLI v0.42.0.
- **Mapper**: Improved symbolic link handling for `GEMINI.md` in the bridge directory.

### Added
- **Purifier**: Implemented automatic backup and sanitization of legacy AI environments during installation.
- **Setup**: Added granular platform selection for Harness application.
- **Documentation**: Added `CHANGELOG.md` to track project evolution.

## [4.1.0] - 2026-05-15

### Added
- Distinguished 'Pi Coding Agent' from 'Gemini CLI'.
- Updated 'manifest.json' with independent tool mappings.
- Enhanced 'generator.py' and 'mapper.py' for individual platform projections.

## [4.0.0] - 2026-05-15

### Added
- Complete universal harness implementation.
- Integrated detector, generator, and mapper into setup.
- Implemented Adapter Pattern for cross-platform compatibility.
