# Changelog

All notable changes to openstan will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.3] - 2026-10-07

**Summary:** Phase 3 logging infrastructure completion, anonymisation as first-class feature, and multiple documentation improvements including SEO fixes and blog migration to Zensical native blogging.

### Added

- Phase 3 logging infrastructure (complete implementation) (#244)
- Anonymisation as first-class citizen (#217)

### Fixed

- Linting issues in test files
- Version check logic and UI text inconsistency (#216)
- SEO issues identified in review
- Zensical build and internal cross-links

### Documentation

- Screenshots updated
- Zensical redirects plugin for blog post URL migration
- SEO descriptions and sitemap enhancements
- Guides index creation
- Enhanced internal linking across 24 pages for SEO and navigation
- Blog setup documentation
- Migration from Material blog plugin to Zensical native blog

### Changed

- Blog platform modernization to Zensical native support

[0.2.3]: https://github.com/boscorat/openstan/compare/v0.2.2...v0.2.3

---

## [0.2.2] - 2026-09-15

**Summary:** Halifax current account opening balance anomaly fix. Halifax statements have an unusual opening balance behavior (reported at end of first date rather than beginning), causing balance reconciliation failures. This release recalculates the opening balance by adjusting the closing balance with transaction movements.

### Added

- Feedback collection page via OpnForm (#188) (#192)

### Fixed

- Debug worker logging of pending-status update failures with regression tests
- Debug worker to skip already-complete rows when re-running
- Debug worker retry on session restore with failure logging
- Upgrade detection and fpm metadata review feedback
- Linux package upgrade launcher breakage prevention
- Dark mode race condition in feedback form (#193)
- Feedback form dark mode sync with docs site theme (#196)
- Multiple Chrome white iframe background issues:
  - Color scheme auto CSS property
  - darkMode=auto URL parameter
  - Transparent iframe background

### Documentation

- Bank request flow diagram fixes
- Announcements link in community page
- Community page addition and YouTube links for Phase 1 social media plan
- WDSI submission instructions for sole developers (#190)

### Other Changes

- StatCounter tracking integration (gated behind STATCOUNTER_PROJECT_ID env var)
- Removed logging implementation markdown files

[0.2.2]: https://github.com/boscorat/openstan/compare/v0.2.1...v0.2.2

---

## [0.2.1] - 2026-09-10

**Summary:** Major feature release with folder anonymisation support, anonymiser retain-descriptions option, use cases hub, comprehensive SEO improvements (meta tags, schema markup, sitemap, robots.txt), and extensive UI cleanup.

### Added

- Close button to title bar
- Anonymiser retain-descriptions option with security warning (#146)
- Folder anonymisation support (#135)
- Key screens table to homepage for better internal linking (#132)
- Organization JSON-LD schema to homepage (#131)
- Use cases hub page with five dedicated use case pages:
  - Conveyancing
  - Small business
  - Multi-account tracking
  - Probate
  - Self assessment
- Use cases nav section and homepage cross-link
- Supported banks table generation from parser TOML configs (#128)
- Open Graph and Twitter Card meta tags
- BreadcrumbList JSON-LD schema to inner pages
- Sitemap plugin with lastmod and changefreq
- robots.txt with sitemap directive
- WebSite and SearchAction schema on homepage
- Video tutorial quickstart guides (#186)
- Promotion gif to README and docs site (#184)
- Organization JSON-LD schema to homepage

### Fixed

- Upgrade BSP to v0.4.4 and surface migration warnings in UI (#185)
- Project info clearing when opening wizard to prevent stale flash
- BSP harness tests to skip when PDFs unavailable on Dependabot PRs
- QThreadPool consolidation to eliminate macOS 'Task policy set failed' errors (#175)
- Combo signals blocking during project creation to prevent old project flash (#167)
- Nav button highlight sync with stacked widget (#168)
- Results view closing before switching projects (#160)
- App and window naming so macOS Dock shows 'openstan' (#156)
- Statement queue tree view PDF count (#159)
- Admin reset to delete gui.db and restart the app (#148)
- Admin dialog from resetting project selection
- Precise type annotation for PROFILES to satisfy pyrefly
- All 54 ruff check errors
- Missing slash in OG image URL
- Zensical build failure in OG/Twitter meta tags
- Deduplicate homepage title tag
- JSON-LD SoftwareApplication to be conditional on homepage

### Documentation

- Anonymisation docs for folder batch support (#141)
- All pages updated with unique meta descriptions for SEO
- Documentation review for release (#173)

### Other Changes

- GitHub profile improvements before launch (#183)
- UI cleanup tweaks (#149)
- Anonymise folder opening to use Popen instead of run to avoid thread blocking
- Format monetary values with thousand-separator commas in project info table
- Declaration statement for output directory
- Hardening of block signals logic
- Updated supported bank list in README
- Dependency upgrades: BSP and BSA
- ci: Multiple GitHub Actions dependency updates

[0.2.1]: https://github.com/boscorat/openstan/compare/v0.2.0.0...v0.2.1

---

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
