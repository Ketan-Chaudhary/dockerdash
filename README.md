# DockDash

> A powerful, keyboard-driven Docker management dashboard built for the terminal.
---

## Overview

**DockDash** provides a modern, high-contrast Terminal User Interface (TUI) for inspecting, managing, and controlling Docker Engine resources. Built using Python, Textual, and the official Docker SDK, DockDash delivers desktop-grade interactivity directly within your terminal window.

---

## Features

- **Container Lifecycle**: Start, stop, restart, pause, rename, and force-remove containers.
- **Full-Screen Logs**: Instant full-screen container log viewer (`l`) with text scrolling, clean markup handling, and clear option (`c`). Press `Esc` or `q` to return.
- **Resource Monitoring**: Live CPU, memory usage, network I/O, disk I/O, and PID metrics displayed via bar indicators.
- **Interactive Terminal Access**: Attach directly to running containers (`t`) via interactive shell execution (TUI automatically suspends and resumes upon exit).
- **Image Management**: Pull, delete, tag/rename, and inspect local images. View layer histories.
- **Dockerfile Editor**: Built-in full-screen editor (`e`) with line numbers, code editing, file saving, and direct image building.
- **Container Creation Wizard**: Multi-field form for configuring images, ports, volume mounts, environment variables, restart policies, and resource limits.
- **Volumes & Networks**: Inspect, create, and remove Docker volumes and networks with built-in network protection.
- **System Overview & Disk Cleanup**: Real-time Engine information, disk usage breakdown, and prune tools for containers, images, volumes, networks, or full system prune (`x`).
- **Keyboard-Driven Traversal**: Seamless focus traversal across interactive controls using Arrow keys (`←` `→` `↑` `↓`), `Tab`, and context keybindings.

---

## Quick Start & Installation

### Requirements
- Python `>= 3.10`
- Docker Engine running locally

### Installation

```bash
# Clone the repository
git clone https://github.com/ketanchaudhary/docker-dashboard.git
cd docker-dashboard

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install package in editable mode
pip install -e .

# Launch DockDash
dockdash
```

---

## Keyboard Shortcuts

### Global Navigation

| Shortcut | Action |
| :--- | :--- |
| `1` – `5` | Switch active tab (Containers, Images, Volumes, Networks, System) |
| `r` / `F5` | Refresh current tab data |
| `/` | Open search / filter bar |
| `?` / `F1` | Open Keyboard Shortcuts help modal |
| `q` / `Ctrl+C` | Quit application |
| `Esc` | Close active dialog, filter bar, or modal |

### Containers Tab (`1`)

| Shortcut | Action |
| :--- | :--- |
| `s` | Start container |
| `S` | Stop container |
| `R` | Restart container |
| `p` | Pause / Unpause container |
| `n` | Rename container |
| `d` | Delete container (requires confirmation) |
| `l` | Open full-screen Log Viewer (`Esc`/`q` to close, `c` to clear) |
| `a` | Toggle real-time container Stats panel |
| `i` | Open full-screen JSON Inspect view |
| `t` | Attach terminal (interactive shell) |
| `Enter` | Toggle Container Detail panel |

### Images Tab (`2`)

| Shortcut | Action |
| :--- | :--- |
| `p` | Pull new image (repository:tag) |
| `t` | Tag / rename image |
| `c` | Launch Container Creation Wizard for selected image |
| `e` | Open full-screen Dockerfile Editor (`Ctrl+S` to save, build button) |
| `h` | View image layer history |
| `i` | Open full-screen JSON Inspect view |
| `d` | Delete image (requires confirmation) |

### Volumes (`3`) & Networks (`4`) Tabs

| Shortcut | Action |
| :--- | :--- |
| `c` | Create volume or network |
| `i` | Inspect volume or network details |
| `d` | Remove volume or network |

### System & Cleanup Tab (`5`)

| Shortcut | Action |
| :--- | :--- |
| `←` `→` `↑` `↓` | Traverse cleanup action buttons |
| `Enter` | Trigger selected prune action |
| `c` | Prune stopped containers |
| `i` | Prune dangling images |
| `v` | Prune unused volumes |
| `n` | Prune unused networks |
| `x` | Trigger Full System Prune |

---

## Architecture Overview

```
docker-dashboard/
├── pyproject.toml               # Build system configuration & dependencies
├── LICENSE                      # MIT License (Ketan Chaudhary)
├── README.md                    # Documentation
└── dockdash/
    ├── __init__.py
    ├── app.py                   # Main Textual App & global event handling
    ├── docker_client.py         # Async Docker SDK wrapper
    ├── styles.tcss              # High-contrast TCSS stylesheet
    ├── screens/
    │   ├── containers.py        # Containers management view
    │   ├── images.py            # Images management view
    │   ├── volumes.py           # Volumes management view
    │   ├── networks.py          # Networks management view
    │   └── system.py            # Engine status & cleanup view
    ├── widgets/
    │   ├── container_detail.py  # Container attributes panel
    │   ├── log_viewer.py        # Full-screen log viewer modal
    │   ├── stats_display.py     # Live container stats widget
    │   ├── pull_progress.py     # Image pull progress bar
    │   └── search_bar.py        # Search / filter bar
    └── modals/
        ├── container_create.py  # Container creation wizard
        ├── dockerfile_editor.py # Full-screen Dockerfile editor
        ├── confirm_dialog.py    # Reusable confirmation dialog
        ├── input_dialog.py      # Input modals
        ├── inspect_dialog.py    # Full-screen JSON inspector
        └── help_dialog.py       # Keybindings reference modal
```

---

## License

Distributed under the MIT License. See [LICENSE](file:///home/ketan/Desktop/docker-dashboard/LICENSE) for full details.

Copyright (c) 2026 **Ketan Chaudhary**
