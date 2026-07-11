#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
VERSION_FILE="$ROOT_DIR/VERSION.txt"
VERSION="${1:-}"
VERSION_RE='^v[0-9]+\.[0-9]+\.[0-9]+$'

if [ -z "$VERSION" ]; then
    VERSION="$(tr -d '\r\n' < "$VERSION_FILE")"
fi

if ! [[ "$VERSION" =~ $VERSION_RE ]]; then
    echo "错误: 版本号必须使用 vX.Y.Z 格式，例如 v0.1.0"
    exit 1
fi

PACKAGE_VERSION="$(tr -d '\r\n' < "$VERSION_FILE")"
if [ "$VERSION" != "$PACKAGE_VERSION" ]; then
    echo "错误: 参数版本 $VERSION 与 VERSION.txt $PACKAGE_VERSION 不一致"
    exit 1
fi

if ! awk -v version="$VERSION" '
    $0 == "## " version { found = 1; next }
    found && /^## / { exit }
    found && /^- / { item = 1 }
    END { exit !(found && item) }
' "$ROOT_DIR/CHANGELOG.md"; then
    echo "错误: CHANGELOG.md 缺少 $VERSION 标题，或该版本下没有变更条目"
    exit 1
fi

"$ROOT_DIR/scripts/check-sensitive.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$DIST_DIR" "$TMP_DIR/shadowrocket" "$TMP_DIR/docs/assets"
cp "$ROOT_DIR/README.md" "$TMP_DIR/README.md"
cp "$ROOT_DIR/VERSION.txt" "$TMP_DIR/VERSION.txt"
cp "$ROOT_DIR/CHANGELOG.md" "$TMP_DIR/CHANGELOG.md"
cp "$ROOT_DIR/shadowrocket/README.md" "$TMP_DIR/shadowrocket/README.md"
cp "$ROOT_DIR/shadowrocket/"*.conf "$TMP_DIR/shadowrocket/"
cp "$ROOT_DIR/docs/index.html" "$TMP_DIR/docs/index.html"
cp "$ROOT_DIR/docs/assets/shadowrocket-full-qr.png" "$TMP_DIR/docs/assets/shadowrocket-full-qr.png"

ZIP_NAME="mobile-proxy-share-kit-${VERSION}.zip"
rm -f "$DIST_DIR/$ZIP_NAME"

cd "$TMP_DIR"
zip -qr "$DIST_DIR/$ZIP_NAME" .

echo "完成: $DIST_DIR/$ZIP_NAME"
