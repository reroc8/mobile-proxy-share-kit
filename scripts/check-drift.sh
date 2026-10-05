#!/usr/bin/env bash
# 漂移检测：仓库里的产物是否仍然等于「用当前 PC 版 Merge.yaml 生成的结果」。
#
# 不一致就说明 PC 那边改了规则、而手机端这两份产物没重新生成 —— 也就是漂移。
# v0.1.x 到 v0.3.0 之间 Shadowrocket 落后了 93 条，就是因为当时没有这道检查。
#
# 用法：
#   bash scripts/check-drift.sh          只检测，报差异，退出码 1 表示有漂移
#   bash scripts/check-drift.sh --fix    检测并直接用 PC 版配置重新生成产物
#
# 注意：规则源在仓库外（~/Desktop/Clash配置/...），所以这个检查只能在有那份配置的
# 本机上跑，GitHub Actions 之类的 CI 跑不了。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

for script in build-karing-rules.py build-shadowrocket-rules.py; do
    if [ ! -f "$ROOT_DIR/scripts/$script" ]; then
        echo "错误: 缺少 scripts/$script"
        exit 1
    fi
done

FIX=0
for arg in "$@"; do
    case "$arg" in
        --fix) FIX=1 ;;
        *) echo "错误: 未知参数 $arg（只支持 --fix）"; exit 1 ;;
    esac
done

if [ "$FIX" -eq 1 ]; then
    echo "== 用 PC 版配置重新生成产物 =="
    "$PYTHON_BIN" "$ROOT_DIR/scripts/build-karing-rules.py"
    "$PYTHON_BIN" "$ROOT_DIR/scripts/build-shadowrocket-rules.py"
    echo
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# --fix 模式下先重新生成了，这里的比对等于复核生成结果是否已落盘
if ! "$PYTHON_BIN" "$ROOT_DIR/scripts/build-karing-rules.py" --out-dir "$TMP_DIR" >/dev/null; then
    echo "错误: Karing 产物生成失败，先解决上面的报错"
    exit 1
fi
if ! "$PYTHON_BIN" "$ROOT_DIR/scripts/build-shadowrocket-rules.py" --out-dir "$TMP_DIR" >/dev/null; then
    echo "错误: Shadowrocket 产物生成失败，先解决上面的报错"
    exit 1
fi

ARTIFACTS=(
    "karing/karing-diversion-rules.json"
    "docs/karing/karing-diversion-rules.json"
    "shadowrocket/Shadowrocket.rules.conf"
    "shadowrocket/Shadowrocket.conf"
    "shadowrocket/Shadowrocket.full.conf"
)

DRIFTED=0
for rel in "${ARTIFACTS[@]}"; do
    committed="$ROOT_DIR/$rel"
    regenerated="$TMP_DIR/$rel"

    if [ ! -f "$committed" ]; then
        echo "缺失:   $rel（仓库里没有这个产物）"
        DRIFTED=1
        continue
    fi
    if cmp -s "$committed" "$regenerated"; then
        echo "一致:   $rel"
    else
        echo "已漂移: $rel"
        diff -u "$committed" "$regenerated" | sed -n '1,40p' | sed 's/^/        /' || true
        DRIFTED=1
    fi
done

echo
if [ "$DRIFTED" -eq 0 ]; then
    echo "产物与 PC 版配置一致。"
    exit 0
fi

if [ "$FIX" -eq 1 ]; then
    echo "重新生成后仍有差异，说明生成脚本不是确定性的，需要排查。"
    exit 1
fi

echo "发现漂移：PC 版配置已变，但仓库产物还是旧的。"
echo "在手机上真正生效前，先跑一次：bash scripts/check-drift.sh --fix"
exit 1
