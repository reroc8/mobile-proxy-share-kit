#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
VERSION_FILE="$ROOT_DIR/VERSION.txt"
VERSION="${1:-}"
VERSION_RE='^v[0-9]+\.[0-9]+\.[0-9]+$'
# 默认 python3；测试依赖（pyyaml）装在别处时用 PYTHON_BIN 指过来，
# 否则 Clash 产物的校验会被跳过，卡口就弱了。
PYTHON_BIN="${PYTHON_BIN:-python3}"

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

# 产物约束：组顺序、映射、内置规则集名字等。离线跑，不依赖 PC 源码。
if ! (cd "$ROOT_DIR" && "$PYTHON_BIN" -m unittest discover -s tests); then
    echo "错误: 产物约束检查未通过，先修好再发版"
    exit 1
fi

# karing/ 是产物，docs/karing/ 是 Pages 同源下载副本，两者必须逐字节一致。
if ! diff -q "$ROOT_DIR/karing/karing-diversion-rules.json" \
             "$ROOT_DIR/docs/karing/karing-diversion-rules.json" >/dev/null; then
    echo "错误: docs/karing/ 副本与 karing/ 产物不一致，请先运行 scripts/build-karing-rules.py"
    exit 1
fi

# Shadowrocket.conf 是旧链接兼容文件，必须和 rules.conf 完全一致。
if ! diff -q "$ROOT_DIR/shadowrocket/Shadowrocket.conf" \
             "$ROOT_DIR/shadowrocket/Shadowrocket.rules.conf" >/dev/null; then
    echo "错误: Shadowrocket.conf 与 Shadowrocket.rules.conf 不一致，请先运行 scripts/build-shadowrocket-rules.py"
    exit 1
fi

# 最关键的一步：确认两份产物就是「用当前 PC 版 Merge.yaml 生成的结果」。
# 缺了这一步，PC 改了规则而产物没重新生成，发出去的还是旧规则。
if ! "$ROOT_DIR/scripts/check-drift.sh" >/dev/null; then
    echo "错误: 产物与 PC 版配置不一致，先跑 scripts/check-drift.sh --fix"
    "$ROOT_DIR/scripts/check-drift.sh" || true
    exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$DIST_DIR" "$TMP_DIR/shadowrocket" "$TMP_DIR/karing" "$TMP_DIR/clash" "$TMP_DIR/docs/assets" "$TMP_DIR/docs/karing" "$TMP_DIR/scripts" "$TMP_DIR/tests"
cp "$ROOT_DIR/README.md" "$TMP_DIR/README.md"
cp "$ROOT_DIR/VERSION.txt" "$TMP_DIR/VERSION.txt"
cp "$ROOT_DIR/CHANGELOG.md" "$TMP_DIR/CHANGELOG.md"
cp "$ROOT_DIR/shadowrocket/README.md" "$TMP_DIR/shadowrocket/README.md"
cp "$ROOT_DIR/shadowrocket/"*.conf "$TMP_DIR/shadowrocket/"
cp "$ROOT_DIR/karing/README.md" "$TMP_DIR/karing/README.md"
cp "$ROOT_DIR/karing/"*.json "$TMP_DIR/karing/"
cp "$ROOT_DIR/clash/"* "$TMP_DIR/clash/"
# 整目录复制，别再逐个列文件名 —— 之前就漏过新增的脚本
cp "$ROOT_DIR/scripts/"* "$TMP_DIR/scripts/"
mkdir -p "$TMP_DIR/tests"
cp "$ROOT_DIR/tests/"*.py "$TMP_DIR/tests/"
cp "$ROOT_DIR/docs/index.html" "$TMP_DIR/docs/index.html"
cp "$ROOT_DIR/docs/import.html" "$TMP_DIR/docs/import.html"
cp "$ROOT_DIR/docs/assets/"*.png "$TMP_DIR/docs/assets/"
cp "$ROOT_DIR/docs/karing/"*.json "$TMP_DIR/docs/karing/"

ZIP_NAME="mobile-proxy-share-kit-${VERSION}.zip"
rm -f "$DIST_DIR/$ZIP_NAME"

cd "$TMP_DIR"
# 用 Python 打包，不用 `zip -qr`：产物主入口是中文文件名（星君分流.conf），
# 而 Info-ZIP 的 zip 不写 UTF-8 标志位，解压方会按本地编码猜 ——
# macOS 的 unzip 猜成 cp437，文件名直接乱码。Python 的 zipfile 始终带 UTF-8 标志位。
"$PYTHON_BIN" -c '
import os, sys, zipfile
src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(root, name)
            zf.write(full, os.path.relpath(full, src))
' "$TMP_DIR" "$DIST_DIR/$ZIP_NAME"

echo "完成: $DIST_DIR/$ZIP_NAME"
