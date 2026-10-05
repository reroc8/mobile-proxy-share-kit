#!/usr/bin/env bash
# 发版：出包 -> 打 tag -> 建 GitHub Release 并把 zip 传上去。
#
# 为什么需要它：dist/ 在 .gitignore 里，zip 只留在本机，别人从仓库拿不到成品；
# 而且 v0.2.0 之后一直没打 tag，没有任何版本锚点。这个脚本把这两件事补齐。
#
# 用法：
#   bash scripts/publish-release.sh            按 VERSION.txt 发当前版本
#   bash scripts/publish-release.sh --dry-run  只检查，不推 tag、不发 Release
#
# 前提：工作区干净、VERSION.txt 与 CHANGELOG.md 对齐、本地领先或等于远端。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        *) echo "错误: 未知参数 $arg（只支持 --dry-run）"; exit 1 ;;
    esac
done

VERSION="$(tr -d '\r\n' < VERSION.txt)"
if ! [[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "错误: VERSION.txt 里的版本号格式不对: $VERSION"
    exit 1
fi

if ! grep -q "^## ${VERSION}$" CHANGELOG.md; then
    echo "错误: CHANGELOG.md 里没有 ${VERSION} 的条目"
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "错误: 工作区不干净，先提交或撤销改动"
    git status --short
    exit 1
fi

if git rev-parse -q --verify "refs/tags/${VERSION}" >/dev/null; then
    echo "错误: tag ${VERSION} 已存在。发新版本请先跑 scripts/bump-version.py"
    exit 1
fi

echo "== 出包 =="
bash scripts/build-release.command

ZIP="dist/mobile-proxy-share-kit-${VERSION}.zip"
if [ ! -f "$ZIP" ]; then
    echo "错误: 没有产出 $ZIP"
    exit 1
fi

# Release 说明直接从 CHANGELOG 抽该版本段落，不再手写一份
NOTES="$(awk -v version="## ${VERSION}" '
    $0 == version { found = 1; next }
    found && /^## / { exit }
    found { print }
' CHANGELOG.md)"
if [ -z "$NOTES" ]; then
    echo "错误: 从 CHANGELOG.md 抽不出 ${VERSION} 的说明"
    exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
    echo
    echo "== dry-run 通过，本应执行 =="
    echo "  git tag ${VERSION} && git push origin ${VERSION}"
    echo "  gh release create ${VERSION} ${ZIP} --title ${VERSION} --notes <CHANGELOG 段落>"
    exit 0
fi

echo "== 打 tag =="
git tag "$VERSION"
git -c http.version=HTTP/1.1 push origin "$VERSION"

echo "== 建 GitHub Release =="
gh release create "$VERSION" "$ZIP" --title "$VERSION" --notes "$NOTES"

echo
echo "完成: $(gh release view "$VERSION" --json url --jq .url)"
