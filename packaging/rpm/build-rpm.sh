#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="/tmp/appharbor-rpmbuild"
OUT_DIR="${ROOT_DIR}/dist"
VERSION="0.1.0"

echo "==> Building AppHarbor RPM package (v${VERSION})..."
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} "${OUT_DIR}"

# 1. Create clean source tarball in /tmp without spaces in path
tar --exclude-vcs --exclude="./build" --exclude="./dist" \
    --transform "s,^\.,appharbor-${VERSION}," \
    -czf "${BUILD_DIR}/SOURCES/appharbor-${VERSION}.tar.gz" -C "${ROOT_DIR}" .

# 2. Build RPM using spec file
rpmbuild -ba --nodeps "${ROOT_DIR}/packaging/appharbor.spec" \
    --define "_topdir ${BUILD_DIR}" \
    --define "version ${VERSION}"

# 3. Copy RPM to dist/
find "${BUILD_DIR}/RPMS" -name "*.rpm" -exec cp {} "${OUT_DIR}/" \;
echo "==> RPM built successfully in ${OUT_DIR}/"
