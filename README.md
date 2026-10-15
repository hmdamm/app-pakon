# AppHarbor ⚓ — Universal Linux Application Manager

AppHarbor is a modern, trustworthy, desktop-native application for Linux that gives you a single, unified place to discover, inspect, and safely remove applications across different installation sources — regardless of distribution.

[![CI & Packaging Validation](https://github.com/appharbor/appharbor/actions/workflows/ci.yml/badge.svg)](https://github.com/appharbor/appharbor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-amber.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![GTK4 & Libadwaita](https://img.shields.io/badge/GUI-GTK4%20%2B%20Libadwaita-brightgreen.svg)](https://gitlab.gnome.org/GNOME/libadwaita)

---

## 💡 The Problem

On modern Linux systems, applications come from multiple package ecosystems:
- Flatpaks from Flathub or Fedora remotes.
- Native RPM, DEB, Pacman, or Zypper packages from the distribution repos.
- Snaps from the Snap Store.
- Standalone portable AppImages dropped into `~/.local/bin` or `~/Applications`.
- Standalone tarballs, scripts, and manually installed `.desktop` launchers.

Most graphical app stores only show what is available to install from their specific backend, while system package managers list thousands of internal shared libraries, drivers, and background daemons that confuse users who just want to manage their apps.

**AppHarbor answers:**
- What desktop applications are currently installed on this computer?
- What version is each app, where did it come from, and is it a system-wide or per-user installation?
- Which package format was used: Flatpak, Snap, AppImage, RPM/DNF, DEB/APT, Pacman, or an unknown source?
- What will happen if I uninstall an entry, and will my personal data and settings be preserved?

---

## ✨ Features

- **Unified Multi-Source Inventory:** Scans Flatpak, RPM/DNF, Snap, AppImage, DEB/APT, Pacman, Zypper, and manual `.desktop` launchers into a single view.
- **Accurate Scope Attribution:** Clearly distinguishes packaging mechanism (`Source`) from installation boundary (`System` vs `User`).
- **Safe, Explicit Uninstallation:**
  - Default policy **preserves personal settings and user data** (`~/.config`, `~/.var/app`).
  - Optional explicit checkbox displays confirmed directories before deletion.
  - No blind `rm -rf`, wildcards, or dynamically constructed shell scripts.
- **Critical System Guard:** Core operating system components (kernels, systemd, glibc, desktop environments, package managers) are protected from accidental removal.
- **Fault-Tolerant Scanning:** If a tool is absent or fails (e.g. `snapd` is not installed on Fedora), it gracefully reports status without blocking results from other providers.
- **Distinctive Visual Direction:** Built with a warm graphite & ivory palette with restrained amber, terracotta, and lime accents (avoiding the generic blue/purple SaaS style).
- **Desktop Native & Accessible:** Full Wayland/X11 support, high-contrast text compliance (WCAG AA), and complete keyboard navigation.

---

## 🗂 Filter Categories

AppHarbor provides prominent category filters that reflect reality:

| Filter | Description | Example Match |
|---|---|---|
| **All** | Every discovered desktop application. | All detected records |
| **Flatpak** | Applications managed via Flatpak. | `org.mozilla.firefox` |
| **Snap** | Applications installed via Snap. | `code` (snap) |
| **AppImage** | Standalone portable AppImage executables. | `Krita.AppImage` |
| **System** | System-wide installations requiring root/admin privileges. | `/var/lib/flatpak` or `/usr/bin` |
| **User** | Per-user installations residing in user's home directory. | `~/.local/share/flatpak` or `~/.local/bin` |
| **Unknown** | Unmanaged or manual launchers without a registered manager. | Manually created `.desktop` file |

---

## 🚀 Installation & Running

### Requirements
- Linux (Fedora 38+, Ubuntu 22.04+, Debian 12+, Arch Linux, openSUSE Tumbleweed/Leap)
- Python 3.10 or newer
- GTK 4 and Libadwaita 1.0+ (`python3-gobject`, `gtk4`, `libadwaita`)

### Fedora
```bash
# Install dependencies
sudo dnf install python3-gobject gtk4 libadwaita

# Run directly from source
git clone https://github.com/appharbor/appharbor.git
cd appharbor
python3 main.py
```

### Ubuntu / Debian
```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1

git clone https://github.com/appharbor/appharbor.git
cd appharbor
python3 main.py
```

### Arch Linux
```bash
sudo pacman -S python-gobject gtk4 libadwaita

git clone https://github.com/appharbor/appharbor.git
cd appharbor
python3 main.py
```

---

## 🧪 Testing & Verification

AppHarbor comes with a unit and integration test suite:

```bash
# Run pytest
pytest -v

# Validate desktop file and AppStream metadata
desktop-file-validate data/io.github.appharbor.AppHarbor.desktop
appstreamcli validate --no-net data/io.github.appharbor.AppHarbor.metainfo.xml
```

---

## 🛡 Security Architecture & Safety Rules

1. **Unprivileged Discovery:** All inventory scans run strictly under the standard user session without elevated permissions.
2. **No Arbitrary Shell Execution:** All subprocess calls use structured argument vectors (`["flatpak", "uninstall", ...]` or `["dnf", "remove", ...]`), strictly preventing shell injection.
3. **OS-Managed Privilege Elevation:** System package removal delegates elevation to system-managed Polkit (`pkexec`) or native package manager prompts. AppHarbor never prompts for or stores passwords.
4. **Data Preservation Guarantee:** User data is preserved by default. Opt-in deletion explicitly lists targeted paths.

See [docs/architecture.md](docs/architecture.md) for the complete architecture decision record.

---

## 🤝 Contributing

Contributions are warmly welcomed! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding new package providers, improving localization, and running tests.

---

## 📄 License

AppHarbor is released under the [MIT License](LICENSE).
