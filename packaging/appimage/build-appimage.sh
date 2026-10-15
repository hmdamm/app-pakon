#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/appimage"
APP_DIR="${BUILD_DIR}/AppDir"
OUT_DIR="${ROOT_DIR}/dist"

echo "==> Building AppHarbor AppImage..."
rm -rf "${BUILD_DIR}"
mkdir -p "${APP_DIR}/usr/bin" "${APP_DIR}/usr/lib" "${APP_DIR}/usr/share" "${OUT_DIR}"

# 1. Install appharbor into AppDir
echo "==> Installing Python package into AppDir..."
python3 -m pip install --no-deps --target "${APP_DIR}/usr/lib/python-appharbor" "${ROOT_DIR}"

# 2. Copy desktop integration files
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

# 3. Create AppRun entrypoint
echo "==> Generating AppRun entrypoint..."
cat << 'EOF' > "${APP_DIR}/AppRun"
#!/bin/bash
set -e

HERE="$(dirname "$(readlink -f "$0")")"
export PATH="${HERE}/usr/bin:${PATH}"
export PYTHONPATH="${HERE}/usr/lib/python-appharbor:${PYTHONPATH:-}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"

exec python3 -m appharbor "$@"
EOF
chmod +x "${APP_DIR}/AppRun"

# 4. Check for appimagetool or download
echo "==> Packaging AppDir with appimagetool..."
APPIMAGETOOL="${BUILD_DIR}/appimagetool"
if ! command -v appimagetool &>/dev/null; then
  if [ ! -f "${APPIMAGETOOL}" ]; then
    echo "Downloading appimagetool..."
    if curl -fsSL -o "${APPIMAGETOOL}" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$(uname -m).AppImage"; then
      chmod +x "${APPIMAGETOOL}"
      ARCH=$(uname -m) "${APPIMAGETOOL}" --appimage-extract-and-run "${APP_DIR}" "${OUT_DIR}/AppHarbor-$(uname -m).AppImage" || \
      ARCH=$(uname -m) "${APPIMAGETOOL}" "${APP_DIR}" "${OUT_DIR}/AppHarbor-$(uname -m).AppImage"
    else
      echo "Note: appimagetool download skipped/offline. AppDir successfully staged at ${APP_DIR}."
      exit 0
    fi
  fi
else
  ARCH=$(uname -m) appimagetool "${APP_DIR}" "${OUT_DIR}/AppHarbor-$(uname -m).AppImage"
fi

echo "==> AppImage packaging complete."
