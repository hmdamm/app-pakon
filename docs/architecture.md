# Architecture Decision Record & System Architecture

**Project:** AppHarbor (Universal Linux Application Manager)  
**Status:** Approved & In-Progress  
**Date:** 2026-10-15  
**Target Environment:** Linux (Fedora 44 Workstation primary, Ubuntu/Debian, Arch Linux, openSUSE portable)

---

## 1. Executive Summary & Goals

AppHarbor is an open-source, desktop-native utility designed to give Linux users a single, transparent, and trustworthy inventory of all installed applications across disparate packaging formats (Flatpak, Snap, AppImage, RPM/DNF, Dpkg/APT, Pacman, Zypper, and manual/unknown desktop installations).

Key objectives:
1. **Accurate Provenance & Scope:** Accurately attribute every application to its packaging mechanism (`Source`) and whether it is installed system-wide or per-user (`Scope`).
2. **Honesty over Illusion:** Show `Unknown` when source or scope cannot be proven; never guess. Keep desktop applications separated from system libraries/kernels.
3. **Safe, Explicit Uninstallation:** Zero silent actions, zero unvetted shell interpolation, strict critical component guards, and data preservation by default.
4. **Desktop Native & Accessible:** Built with GTK4 and Libadwaita with custom warm graphite/ivory and amber accents (no generic blue/purple theme).

---

## 2. Technology Stack & Rationale

### 2.1 Language: Python 3 (3.14+)
- **Portability:** Pre-installed on almost all modern Linux distributions (Fedora, Debian, Ubuntu, Arch, openSUSE).
- **Process & OS Management:** Rich standard library (`subprocess`, `os`, `pathlib`, `json`, `concurrent.futures`, `shutil`) allowing secure argument-vector process execution without shell interpolation.
- **Maintainability & Contribution:** Low barrier to entry for open-source contributors across Linux communities.

### 2.2 GUI Framework: GTK4 + Libadwaita (via PyGObject)
- **True Desktop Integration:** First-class Linux desktop support (Wayland & X11), responsive layout breakpoints (`Adw.Breakpoint`), and master-detail splits (`Adw.NavigationSplitView`).
- **Dynamic Theming & Accessibility:** Automatic synchronization with the desktop dark/light mode preference (`Adw.StyleManager`), standard accessibility support (ATK/ATSPI, screen readers, keyboard focus navigation).
- **Lightweight Footprint:** Instant startup, minimal memory consumption (~40MB vs Electron's 350MB+), without bundling external browser engines.
- **Styling Flexibility:** Full CSS token support (`Gtk.CssProvider`) enabling the custom warm graphite/ivory and amber/terracotta palette while respecting platform conventions.

### 2.3 Packaging Strategy
- **RPM Package:** Native for Fedora, RHEL, CentOS Stream.
- **DEB Package:** Native for Debian, Ubuntu, Linux Mint, Pop!_OS.
- **Flatpak (Portal-aware) / Portable Directory:** Standalone execution directory with standard `.desktop` integration.

---

## 3. Threat Model & Security Architecture

### 3.1 Trust Boundaries
- **Untrusted Input:**
  - Package manager outputs (stdout/stderr).
  - `.desktop` files from user (`~/.local/share/applications`) or third-party repos.
  - AppImage filenames, paths, and internal desktop integration metadata.
  - Application IDs, names, versions, and icon paths.
- **Mitigation:**
  - All command invocations use **strict argument vectors** (`["command", "arg1", "arg2"]`), never string concatenation with `shell=True`.
  - Path normalization with boundary validation (e.g. ensuring an AppImage file is an existing regular file and not a symlink to `/bin` or `/etc`).
  - Desktop file parsing performs lexical extraction without running subshells or executing `Exec` values during scans.

### 3.2 Privilege Elevation & Polkit
- **Rule:** The AppHarbor GUI **must never** run as root (`sudo appharbor`).
- **Discovery:** 100% unprivileged. All scans (RPM, DNF, Flatpak, Snap, AppImage, Desktop entries) run under standard user permissions.
- **Uninstall Actions:**
  - **User-scoped:** Run directly under the current user permissions (e.g., `flatpak uninstall --user <id>`, removing a user AppImage file).
  - **System-scoped:** Delegate elevation to the native package manager's authentication flow or `pkexec` / Polkit helper. Never prompt for or cache passwords inside the application.

### 3.3 Data Deletion & Preservation Policy
- **Default Policy:** Personal data (in `~/.config`, `~/.var/app`, `~/snap`, `~/.local/share`) is **always preserved by default**.
- **Explicit Opt-in:** If an uninstaller supports cleaning app data (e.g., `flatpak uninstall --delete-data`), the user must check an explicit, un-preselected checkbox. The dialog displays the exact paths targeted for deletion before execution.
- **No Wildcard/Recursive Destruction:** Never run `rm -rf` with wildcards or constructed patterns. AppImage removal operates strictly on the single verified target file.

---

## 4. Provider Architecture & Capability Detection

### 4.1 Interface Specification
Each package manager / discovery source implements the `IApplicationProvider` interface:
```python
class IApplicationProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @abstractmethod
    def detect_capabilities(self) -> ProviderCapabilities: ...

    @abstractmethod
    def scan_applications(self, progress_callback=None) -> list[InstallationRecord]: ...

    @abstractmethod
    def plan_uninstall(self, record: InstallationRecord, keep_data: bool) -> UninstallPlan: ...

    @abstractmethod
    def execute_uninstall(self, plan: UninstallPlan, progress_callback=None) -> OperationResult: ...
```

### 4.2 Initial Provider Implementations
1. **FlatpakProvider:**
   - Detects `flatpak` binary.
   - Queries `flatpak list --app --columns=application,name,version,branch,arch,origin,installation,options`.
   - Distinguishes system installations (`/var/lib/flatpak`) from user installations (`~/.local/share/flatpak`).
   - Filters out runtimes/extensions so users see actual desktop applications.
   - Provides safe uninstall via `flatpak uninstall [--user|--system] <app_id> [--delete-data]`.
2. **RpmDnfProvider:**
   - Detects `rpm` and `dnf` / `dnf5`.
   - Correlates desktop files in `/usr/share/applications` with RPM database ownership (`rpm -qf <desktop_file>`). This cleanly isolates interactive desktop applications from the ~3,000 background libraries and OS components.
   - Extracts version, architecture, vendor, summary, and installed size.
   - Plans uninstall via `dnf remove <package_name>` with Polkit elevation.
3. **SnapProvider:**
   - Detects `snap` binary and active snapd socket.
   - Queries `snap list`.
   - Preserves revision, channel, publisher, and confinement.
   - Plans uninstall via `snap remove <snap_name>` (respecting snapshot/data semantics).
4. **AppImageProvider:**
   - Safe scanner of common locations: `~/Applications`, `~/.local/bin`, `~/Downloads`, `/opt`, and `.desktop` files with `AppImage` in their `Exec` path.
   - Validates ELF magic bytes and AppImage type 1/2 signatures without executing the binary.
   - Plans removal by safely moving to Trash or unlinking the single file, plus associated desktop integration file if explicitly requested.
5. **DpkgAptProvider (Debian/Ubuntu):**
   - Correlates desktop files with `dpkg -S`. Queries `dpkg-query -s`.
   - Plans uninstallation via `apt-get remove <pkg>`.
6. **PacmanProvider (Arch Linux):**
   - Queries `pacman -Qo <desktop_file>` and `pacman -Qi <pkg>`.
   - Plans uninstallation via `pacman -R <pkg>`.
7. **ZypperProvider (openSUSE):**
   - Queries RPM desktop files and plans removal via `zypper remove <pkg>`.
8. **ManualDesktopProvider (Unknown/User):**
   - Scans `~/.local/share/applications/` and `/usr/local/share/applications/` for desktop entries not claimed by any package manager.
   - Classifies them as `Source: Unknown` or `Source: Manual`, identifying the launch target and documentation path. Disables casual one-click removal when no reliable package uninstaller is known.

---

## 5. Information Model

Each detected item is an `InstallationRecord`:
- `id`: Deterministic unique identifier (e.g., `flatpak:system:org.mozilla.firefox`).
- `name`: Display name (e.g. "Firefox").
- `package_id`: Canonical package or app identifier (e.g. `org.mozilla.firefox`).
- `version`: Version string or None.
- `architecture`: CPU architecture or `all` / `None`.
- `source`: `Flatpak`, `Snap`, `AppImage`, `RPM`, `DEB/APT`, `Pacman`, `Zypper`, `Manual`, `Unknown`.
- `scope`: `System`, `User`, or `Unknown`.
- `origin`: Remote repo / repository / PPA / local path.
- `install_path`: Physical install root or binary path.
- `desktop_entry_path`: Path to `.desktop` launcher.
- `icon_name_or_path`: Icon name or absolute path.
- `installed_size_bytes`: Confirmed size in bytes (distinguished from package size; `None` if unknown).
- `install_date`: Epoch timestamp or `None`.
- `requires_elevation`: Boolean.
- `is_critical_system_package`: Boolean (flagged by system guards).
- `confidence_score`: High, Medium, Low (provenance certainty).
- `warnings`: List of diagnostic warnings or limitations.

---

## 6. Critical System Component Guard

To prevent catastrophic system bricking, a safety guard protects core OS components:
- Kernel packages (`kernel*`, `linux*`, `vmlinuz*`).
- Core system libraries & init (`systemd*`, `glibc*`, `basesystem*`, `coreutils*`).
- Desktop environment shells (`gnome-shell*`, `mutter*`, `plasma-desktop*`, `sway*`).
- Package managers (`dnf*`, `rpm*`, `apt*`, `dpkg*`, `pacman*`).
- Essential graphics & network stacks (`xorg*`, `wayland*`, `NetworkManager*`).

If an application is mapped to a critical package, casual uninstallation is disabled with an explanatory banner.

---

## 7. Error Handling & Partial Failure Isolation

- Scan operations run concurrently across providers.
- If one provider fails (e.g., `snapd` is not running or `pacman` is missing on Fedora), its failure is recorded as an informational diagnostic banner; it **never halts or corrupts** the scan results of other providers.
- Output errors are captured cleanly in non-intrusive UI banners with a "View Diagnostic Log" option that strips personal paths.
