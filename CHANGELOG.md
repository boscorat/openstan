# Changelog

All notable changes to openstan will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0.0] - 2026-07-27

### Added

- VirusTotal malware scanning gate for all release binaries
- Automatic release asset cleanup (keeps only the 5 most recent releases)
- macOS code signing and notarisation
- Windows MSI code signing via jsign + SimplySign
- ARM64 Linux builds (`.deb` and `.rpm`)
- Descriptive release asset filenames

### Fixed

- Apple notarisation submission reliability (JSON validation, retries)
- DMG creation robustness (stale mount cleanup, retry loop)
- VirusTotal polling loop timeout logic
- Large file handling in VirusTotal scan (upload\_url endpoint)
- CI workflow validation errors

### Changed

- Code signing policy updated from SignPath to Certum + jsign
- Release pipeline documentation aligned with actual implementation

### Contributors

Thanks to all contributors who helped with this release.

[0.2.0.0]: https://github.com/boscorat/openstan/compare/v0.1.5.0...v0.2.0.0
