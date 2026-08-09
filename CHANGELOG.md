# Changelog

All notable changes to **DockDash** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]
\n## [v0.1.3] - 2026-08-09

### Merged Feature
- fix(ci): trigger release workflow on tag push as well as merged relea… (#8 by @Ketan-Chaudhary)

\n## [v0.1.2] - 2026-08-09

### Merged Feature
- Feat/ci cd automation (#6 by @Ketan-Chaudhary)

\n## [v0.1.1] - 2026-08-09

### Merged Pull Request
- ci: add PR CI matrix, automated SemVer release workflow, unit tests, … (#1 by @Ketan-Chaudhary)


### Added
- Automated PR integration checks workflow (`.github/workflows/ci.yml`).
- Automated semver bumping and release workflow on PR merge (`.github/workflows/release-on-merge.yml`).
- PR issue template (`.github/PULL_REQUEST_TEMPLATE.md`).
- Bug report and feature request templates (`.github/ISSUE_TEMPLATE/`).
- Dependabot configuration (`.github/dependabot.yml`).

---

## [0.1.0] - 2026-08-09

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
