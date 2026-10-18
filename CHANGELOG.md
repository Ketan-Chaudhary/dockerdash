# Changelog

All notable changes to **DockDash** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Color templates and themes system with 9 curated visual themes:
  - Cyber Slate (Default) — Electric Cyan & Deep Obsidian Void
  - Tokyo Night — Cyberpunk Neon Violet & Deep Indigo
  - Dracula — Classic Vampire Purple & Fluorescent Pink
  - Nord — Arctic Frost Cyan & Polar Night
  - Catppuccin Mocha — Soothing Pastel Mauve & Dark Charcoal
  - Monokai Pro — Vivid Purple, Neon Yellow & Dark Olive
  - Gruvbox Dark — Retro Warm Aqua, Gold & Deep Bark
  - Synthwave '84 — Retro Synth Neon Cyan, Magenta & Purple
  - Solarized Dark — Precision Blue & Deep Marine Navy
- Interactive Theme Selection modal dialog (`ThemeDialog`) with real-time live previewing while scrolling through options.
- Persistent configuration saving selected themes to `~/.config/dockdash/config.json`.
- Exit confirmation flow (`ExitDialog` on `q`) presenting vertical action buttons: Quit DockDash [Q], Theme Settings [S], and `Esc` to close/resume.
- Command palette (`Ctrl+P` / `^p`) Quit action directly exits the application immediately without showing the confirmation dialog.
- Global `t` keyboard shortcut and Help Dialog entry to open Theme Settings directly.
- Added numbered shortcut notations to all tab titles for enhanced usability and instant keyboard navigation: `Containers (1)`, `Images (2)`, `Volumes (3)`, `Networks (4)`, `Compose (5)`, `System (6)`.
- Visual Image Layers Inspector (`ImageLayersDialog` on `l` / `h`):
  - Dedicated interactive modal showing breakdown of all layers in an image.
  - Proportional visual ASCII gauge bars and percentage contribution for every layer.
  - Weight-based color coding highlighting bloated layers (cyan, green, yellow, bold red).
  - Cleaned Dockerfile instruction parser extracting commands (`RUN`, `COPY`, `ADD`, `ENV`, `CMD`, `ENTRYPOINT`, etc.).
  - Live command detail inspector pane with keyword syntax coloring and timestamp.
  - Quick keyboard actions: copy command to clipboard (`c`), toggle order between Base-first and Top-first (`o`), and navigate (`↑/↓`).
- Container Shell Picker (`ShellPickerDialog` on `t`):
  - Interactive horizontal 2-column modal dialog replacing default `/bin/sh` attach with shell detection and selection.
  - Presets for Auto-detect (`bash` → `zsh` → `ash` → `sh`), `/bin/bash`, `/bin/sh`, `/bin/zsh`, `/bin/ash`, and custom command execution.
  - Optional custom user/UID field (`-u user`) to attach as `root` or non-root users.
  - Number shortcuts `1` through `6` for instant shell selection, with Enter/Esc submission.
  - Robust terminal input validation and error handling:
    - Inline dialog error banner preventing empty commands or invalid user/UID syntax.
    - Pre-flight daemon verification probing if the requested user exists in the container before suspending the UI.
    - Error catch on non-zero exit codes (e.g., 126, 127) prompting the user before redrawing, preventing screen wipe.
- Image Dangling & Unused Quick Filter (`u` toggle and `P` prune on Images tab):
  - Cycle through filter views: `All` → `Dangling (<none>)` → `Unused (no container)` → `All`.
  - Visual styling tags for `<none>` and `<dangling>` images in the image table.
  - Dynamic actions bar filter badge showing matching image count.
  - Dedicated `P` shortcut to prune dangling images with a confirmation dialog.

### Fixed
- Fixed active tab title text clipping where `border-top` on single-line `Tab` widgets consumed the available cell height, leaving only a blue stripe without visible text.
- Fixed keyboard shortcut footer buttons and tab action bars disappearing off-screen caused by `border-top` displacing single-line footer widgets.

### Changed
- Converted all application stylesheet rules (`styles.tcss`) and widget `DEFAULT_CSS` to dynamic theme variables (`$background`, `$surface`, `$panel`, `$primary`, `$secondary`, `$accent`, `$success`, `$warning`, `$error`, `$foreground`, `$text-muted`, `$border`).
- Overhauled application default aesthetics to a high-contrast Cyber-Slate palette with obsidian void (`#0a0e17`), clean slate panels (`#121824`), and vibrant Electric Sky Blue accents (`#38bdf8`).
- Redesigned all modal and panel buttons (primary, success, warning, error, default) with bold text, luminous borders, and high-visibility focus highlights.
- Upgraded table row cursor highlights to Azure Blue with pure white text to ensure selected containers and images are instantly identifiable.

---

## [v0.1.5] - 2026-10-15

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
