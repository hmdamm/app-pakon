#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist"
BUILD_DIR="/tmp/appharbor-debbuild"
PKG_DIR="${BUILD_DIR}/pkg"
VERSION="0.1.0"
DEB_VERSION="0.1.0-1"

echo "==> Building AppHarbor Debian package (.deb)..."
rm -rf "${BUILD_DIR}"
mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/lib/appharbor"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/metainfo"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${OUT_DIR}"

# 1. Copy pure python application package
cp -r "${ROOT_DIR}/appharbor" "${PKG_DIR}/usr/lib/appharbor/"

# 2. Launcher executable script
cat << 'EOF' > "${PKG_DIR}/usr/bin/appharbor"
#!/bin/bash
export PYTHONPATH="/usr/lib/appharbor:${PYTHONPATH:-}"
exec python3 -m appharbor "$@"
EOF
chmod 0755 "${PKG_DIR}/usr/bin/appharbor"

# 3. Desktop integration files
install -D -m 0644 "${ROOT_DIR}/data/io.github.appharbor.AppHarbor.desktop" "${PKG_DIR}/usr/share/applications/io.github.appharbor.AppHarbor.desktop"
install -D -m 0644 "${ROOT_DIR}/data/io.github.appharbor.AppHarbor.metainfo.xml" "${PKG_DIR}/usr/share/metainfo/io.github.appharbor.AppHarbor.metainfo.xml"
install -D -m 0644 "${ROOT_DIR}/data/icons/io.github.appharbor.AppHarbor.svg" "${PKG_DIR}/usr/share/icons/hicolor/scalable/apps/io.github.appharbor.AppHarbor.svg"

# 4. Control file
cat << EOF > "${PKG_DIR}/DEBIAN/control"
Package: appharbor
Version: ${DEB_VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: AppHarbor Team <support@appharbor.org>
Depends: python3, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1
Homepage: https://github.com/hmdamm/app-pakon
Description: Universal Linux Application Manager
 AppHarbor is an open-source desktop application that provides a unified,
 transparent inventory of installed applications across Flatpak, Snap,
 AppImage, RPM/DNF, DEB/APT, Pacman, Zypper, and manual desktop entries,
 featuring safe and explicit uninstallation workflows.
EOF

# 5. Build package using dpkg-deb
dpkg-deb --build --root-owner-group "${PKG_DIR}" "${OUT_DIR}/appharbor_${DEB_VERSION}_all.deb"
echo "==> Debian package built successfully at ${OUT_DIR}/appharbor_${DEB_VERSION}_all.deb"
