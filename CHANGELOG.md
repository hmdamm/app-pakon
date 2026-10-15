# Changelog

All notable changes to AppHarbor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-15

### Added
- **Unified Inventory Engine:** Concurrent scanning across Flatpak, RPM/DNF, Snap, AppImage, DEB/APT, Pacman, Zypper, and manual desktop entries.
- **Accurate Scope & Provenance:** Distinct attribution for packaging mechanism (`Source`) and installation boundary (`System` vs `User`).
- **Safe Uninstallation Workflows:**
  - Explicit confirmation modal presenting package identity, elevation requirements, and deletion targets.
  - Personal configuration/data preserved by default (`~/.config`, `~/.var/app`).
  - Opt-in data removal with exact path previews.
- **Critical System Guard:** Protection blocking accidental uninstallation of core OS packages (kernel, systemd, glibc, display manager, package managers).
- **Failure Isolation:** Graceful degradation when package managers are absent or fail; unhandled provider errors never crash or block discovery.
- **Desktop-Native UI/UX:** Built with Python 3, GTK4, and Libadwaita with custom warm graphite and amber styling.
- **Master-Detail Navigation:** Scannable list with category filter pills, instant debounced search, sort dropdown, and detailed inspection panel.
- **Packaging & CI:** Spec file for RPM/Fedora, Debian control/rules, FreeDesktop `.desktop` and AppStream metainfo files, and GitHub Actions CI workflow.
