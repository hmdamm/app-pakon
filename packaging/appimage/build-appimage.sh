#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="/tmp/appharbor-appimage"
APP_DIR="${BUILD_DIR}/AppDir"
OUT_DIR="${ROOT_DIR}/dist"
ARCH="$(uname -m)"

echo "==> Building AppHarbor AppImage for ${ARCH}..."
rm -rf "${BUILD_DIR}"
mkdir -p "${APP_DIR}/usr/bin" "${APP_DIR}/usr/lib/appharbor" "${APP_DIR}/usr/share" "${OUT_DIR}"

# 1. Install pure python package into AppDir
echo "==> Staging application files into AppDir..."
cp -r "${ROOT_DIR}/appharbor" "${APP_DIR}/usr/lib/appharbor/"

# 2. Executable launcher in usr/bin
cat << 'EOF' > "${APP_DIR}/usr/bin/appharbor"
#!/bin/bash
export PYTHONPATH="${HERE}/usr/lib/appharbor:${PYTHONPATH:-}"
exec python3 -m appharbor "$@"
EOF
chmod +x "${APP_DIR}/usr/bin/appharbor"

# 3. Copy desktop integration files
echo "==> Copying desktop integration assets..."
install -Dm644 "${ROOT_DIR}/data/io.github.appharbor.AppHarbor.desktop" \
  "${APP_DIR}/usr/share/applications/io.github.appharbor.AppHarbor.desktop"
install -Dm644 "${ROOT_DIR}/data/io.github.appharbor.AppHarbor.metainfo.xml" \
  "${APP_DIR}/usr/share/metainfo/io.github.appharbor.AppHarbor.metainfo.xml"
install -Dm644 "${ROOT_DIR}/data/icons/io.github.appharbor.AppHarbor.svg" \
  "${APP_DIR}/usr/share/icons/hicolor/scalable/apps/io.github.appharbor.AppHarbor.svg"

# Root links required by AppImage specification
cp "${ROOT_DIR}/data/io.github.appharbor.AppHarbor.desktop" "${APP_DIR}/io.github.appharbor.AppHarbor.desktop"
cp "${ROOT_DIR}/data/icons/io.github.appharbor.AppHarbor.svg" "${APP_DIR}/io.github.appharbor.AppHarbor.svg"
ln -sf io.github.appharbor.AppHarbor.svg "${APP_DIR}/.DirIcon"

# 4. Create AppRun entrypoint
echo "==> Generating AppRun entrypoint..."
cat << 'EOF' > "${APP_DIR}/AppRun"
#!/bin/bash
set -e

HERE="$(dirname "$(readlink -f "$0")")"
export PATH="${HERE}/usr/bin:${PATH}"
export PYTHONPATH="${HERE}/usr/lib/appharbor:${PYTHONPATH:-}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"

exec python3 -m appharbor "$@"
EOF
chmod +x "${APP_DIR}/AppRun"

# 5. Package with appimagetool
echo "==> Packaging AppDir with appimagetool..."
APPIMAGETOOL="${BUILD_DIR}/appimagetool"
export ARCH

if command -v appimagetool &>/dev/null; then
  appimagetool --appimage-extract-and-run "${APP_DIR}" "${OUT_DIR}/AppHarbor-${ARCH}.AppImage" 2>/dev/null || \
  appimagetool "${APP_DIR}" "${OUT_DIR}/AppHarbor-${ARCH}.AppImage"
else
  echo "Downloading standalone appimagetool..."
  curl -fsSL -o "${APPIMAGETOOL}" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
  chmod +x "${APPIMAGETOOL}"
  "${APPIMAGETOOL}" --appimage-extract-and-run "${APP_DIR}" "${OUT_DIR}/AppHarbor-${ARCH}.AppImage" || \
  "${APPIMAGETOOL}" "${APP_DIR}" "${OUT_DIR}/AppHarbor-${ARCH}.AppImage"
fi

echo "==> AppImage created successfully at ${OUT_DIR}/AppHarbor-${ARCH}.AppImage"
