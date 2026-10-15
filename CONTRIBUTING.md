# Contributing to AppHarbor

Thank you for your interest in contributing to AppHarbor! We welcome bug fixes, documentation improvements, UI polish, and new package provider adapters.

---

## 🛠 Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/appharbor/appharbor.git
   cd appharbor
   ```

2. Ensure system dependencies are installed:
   - Fedora: `sudo dnf install python3-gobject gtk4 libadwaita pytest desktop-file-utils appstream`
   - Ubuntu/Debian: `sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-pytest desktop-file-utils appstream`
   - Arch Linux: `sudo pacman -S python-gobject gtk4 libadwaita python-pytest desktop-file-utils appstream`

3. Run the application:
   ```bash
   python3 main.py
   ```

4. Run the test suite:
   ```bash
   pytest -v
   ```

---

## 🔌 How to Add a New Provider

AppHarbor is designed with a pluggable provider architecture:

1. Create a new provider adapter in `appharbor/providers/<name>.py` subclassing `BaseProvider`:
   ```python
   from appharbor.providers.base import BaseProvider
   from appharbor.domain.models import ProviderCapabilities, InstallationRecord, UninstallPlan, OperationResult

   class MyNewProvider(BaseProvider):
       @property
       def provider_id(self) -> str:
           return "mynewprovider"

       @property
       def display_name(self) -> str:
           return "My New Provider"

       def detect_capabilities(self) -> ProviderCapabilities:
           ...

       def scan_applications(self, progress_callback=None) -> list[InstallationRecord]:
           ...

       def plan_uninstall(self, record, keep_data=True) -> UninstallPlan:
           ...

       def execute_uninstall(self, plan, progress_callback=None) -> OperationResult:
           ...
   ```

2. Register the provider in `appharbor/providers/__init__.py` and in `appharbor/inventory/orchestrator.py`.
3. Add unit test fixtures in `tests/test_providers.py`.
4. Run `pytest -v` to ensure all safety checks pass.

---

## 🛡 Safety and Security Rules

- **No `shell=True`:** Always execute commands using argument arrays (`run_command_safely(["tool", "arg1"])`).
- **Never guess deletion targets:** Uninstallation targets must be concrete and verified.
- **Data preservation:** Personal data must always be preserved unless the user explicitly opts in.
- **Critical packages:** Never allow uninstallation of core OS packages (kernel, systemd, glibc, dnf, apt, etc.).

---

## 📝 Pull Request Guidelines

1. Create a feature branch: `git checkout -b feature/my-feature`.
2. Commit with concise, descriptive messages.
3. Verify that `pytest -v` passes.
4. Open a Pull Request describing your changes, motivation, and verification steps.
