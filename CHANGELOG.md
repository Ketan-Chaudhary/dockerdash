# Changelog

All notable changes to **DockDash** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Real-time live log streaming (`tail -f`) for containers and Docker Compose stacks in `LogViewerScreen` via dedicated background threads and async workers.
- Interactive log search and live regex/text filter bar (`/`) with instant match highlighting and match counting (`X/Y lines`).
- Auto-scroll to bottom toggle (`a`) with live stream tracking.
- Timestamp display toggle (`t`) with ISO 8601 prefix detection and dim formatting.
- Text line wrap toggle (`w`) and log display clear (`c`).
- Log export action (`s`) saving buffered output directly to a timestamped local file.
- `stream_container_logs` and `stream_compose_logs` methods in `DockerClient`.

### Fixed
- Fixed search filter bar display and navigation across all tabs (`ImagesTab`, `ContainersTab`, `VolumesTab`, `NetworksTab`, `ComposeTab`): resolved input clipping by enclosing the search bar with accent borders, enabled `Enter` to navigate directly into the filtered results table, and enabled `Escape` to dismiss search and restore the complete item list.
- Fixed critical item selection desync across `DataTable` views (`ContainersTab`, `ImagesTab`, `VolumesTab`, `NetworksTab`, `ComposeTab`) where table actions (start, stop, logs, inspect, etc.) could target the wrong or previous container when Docker reordered lists or diffed rows; selection now securely resolves via the visual cursor's `RowKey`.
- Fixed bottom-bar overflow and clipping across full-screen modals (`ContainerCreateDialog`, `DockerfileEditorDialog`, `InspectDialog`, `LogViewerScreen`) by replacing conflicting `dock` layouts with flex containers.
- Fixed duplicate row key collision error when rendering identical image tags in the `DataTable`.
- Fixed down arrow key navigation on the tab bar to correctly enter the active tab's `DataTable`.
- Fixed tab focus logic to prevent hidden `SearchBar` input fields from capturing cursor focus.
- Fixed Compose tab so the `Escape` key closes the side panel and returns focus to the table.
- Fixed `release.yml` GitHub Actions workflow to explicitly use `shell: bash` for extracting tags on Windows runners.

### Changed
- Removed hardcoded version number from the main application window title.
- Updated `README.md` release instructions to use a generic `<version>` placeholder instead of a hardcoded tag.

### Performance
- Massively improved tab refreshing by implementing Textual `app.batch_update()` and `update_cell` diffing, preventing UI layout locking and screen flickering.
- Prevented UI lag during tab switches by adding a `0.3s` non-blocking delay to allow the tab transition animation to finish smoothly before triggering data fetch.
- Replaced synchronous API calls with Textual `@work(exclusive=True)` background workers across all tabs to prevent overlapping requests and keep the UI responsive.

## [v0.1.4] - 2026-08-09

### Merged Feature
- fix(ci): use gh pr create in create-release-pr workflow to eliminate branch mismatch and node deprecation errors (#11 by @Ketan-Chaudhary)

## [v0.1.3] - 2026-08-09

### Merged Feature
- fix(ci): trigger release workflow on tag push as well as merged release PRs (#8 by @Ketan-Chaudhary)

## [v0.1.2] - 2026-08-09

### Merged Feature
- Feat/ci cd automation (#6 by @Ketan-Chaudhary)

## [v0.1.1] - 2026-08-09

### Merged Pull Request
- ci: add PR CI matrix, automated SemVer release workflow, unit tests, and templates (#1 by @Ketan-Chaudhary)


### Added
- Automated PR integration checks workflow (`.github/workflows/ci.yml`).
- Automated semver bumping and release workflow on PR merge (`.github/workflows/release-on-merge.yml`).
- PR issue template (`.github/PULL_REQUEST_TEMPLATE.md`).
- Bug report and feature request templates (`.github/ISSUE_TEMPLATE/`).
- Dependabot configuration (`.github/dependabot.yml`).

---

## [v0.1.0] - 2026-08-09

### Added
- Initial release of **DockDash** terminal Docker management dashboard.
- Full container management: start, stop, restart, pause, rename, force delete.
- Full-screen log viewer modal (`l`) with text wrapping, auto-scrolling, and clear screen (`c`).
- Container stats monitoring with CPU, Memory, Network I/O, Disk I/O, and PID bars.
- Interactive terminal attach (`t`) via TUI suspension and `docker exec -it`.
- Image management: pull, delete, tag/rename, inspect JSON, and history layers.
- Full-screen Dockerfile editor (`e`) with line numbers, code editing, and image building.
- Container creation wizard with custom ports, volume mounts, environment variables, restart policies, and resource limits.
- Volume management: list, create, delete, and inspect named volumes.
- Network management: list, create, delete, inspect networks with built-in network protection.
- System overview tab with Engine attributes, disk usage breakdown, and prune tools for containers, images, volumes, networks, or full system prune (`x`).
- High-contrast dark TCSS theme with glowing button focus highlights, active tab badges, and arrow key traversal (`←` `→` `↑` `↓`).
- Cross-platform release executables for Linux (x86_64), Windows (`.exe`), macOS, and Universal Python packages (`.whl`).
