# Security Policy

AppHarbor prioritizes system integrity and safety above all else. Because AppHarbor interacts with packaging systems and uninstallation routines, we enforce strict security boundaries.

---

## 🔒 Security Principles

1. **Unprivileged Operation:** The AppHarbor application process **never** runs as root.
2. **Elevation Delegation:** Privileged package modifications (such as system RPM or DEB removals) are delegated strictly to OS-managed authorization systems (Polkit / `pkexec`) or native package manager credential prompts.
3. **No Shell Interpolation:** All subprocesses are executed with isolated argument vectors. We never pass unvetted strings to `/bin/sh` or use `shell=True`.
4. **Critical Component Guards:** Hardcoded safeguards prevent removal of fundamental OS components (kernel, systemd, glibc, display manager, package manager).

---

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability or safety issue in AppHarbor:
- **Do not** open a public GitHub issue.
- Please email the security maintainers at `security@appharbor.org` (or contact maintainers privately via GitHub Security Advisories).
- Provide a detailed description of the vulnerability, reproduction steps, and potential impact.
- We will acknowledge receipt within 48 hours and work with you on a coordinated disclosure schedule.
