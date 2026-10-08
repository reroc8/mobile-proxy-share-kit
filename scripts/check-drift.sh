#!/usr/bin/env bash
# 漂移检测：仓库里的产物是否仍然等于「用 PC 版仓库当前源码生成的结果」。
#
# 规则源是 GitHub 上 PC 版仓库的 Merge.yaml（见 scripts/mobile_rules.py 的 SOURCE_URL），
# 不是本机某份副本 —— 所以在任何机器上都能跑，也能挂 CI。
#
# 不一致就说明 PC 那边改了规则、而手机端这两份产物没重新生成 —— 也就是漂移。
# v0.1.x 到 v0.3.0 之间 Shadowrocket 落后了 93 条，就是因为当时没有这道检查。
#
# 用法：
#   bash scripts/check-drift.sh          只检测，报差异，退出码 1 表示有漂移
#   bash scripts/check-drift.sh --fix    检测并直接重新生成产物
#
# 环境变量：
#   PYTHON_BIN   指定 python（默认 python3）
#   RULES_SOURCE 指定规则源，默认走 GitHub；离线时指向本机 Merge.yaml 即可

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RULES_SOURCE="${RULES_SOURCE:-}"

for script in mobile_rules.py build-karing-rules.py build-shadowrocket-rules.py build-clash-rules.py build-hiddify-rules.py; do
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

# 没显式指定就用脚本内置的默认源（GitHub）。
# 不用数组拼接：macOS 自带 bash 3.2 在 set -u 下展开空数组会直接报错，
# 那会让整个检测静默失败还返回 0 —— 安全网等于没有。
run_builder() {
    local script="$1"
    shift
    if [ -n "$RULES_SOURCE" ]; then
        "$PYTHON_BIN" "$ROOT_DIR/scripts/$script" "$RULES_SOURCE" "$@"
    else
        "$PYTHON_BIN" "$ROOT_DIR/scripts/$script" "$@"
    fi
}

if [ "$FIX" -eq 1 ]; then
    echo "== 用 PC 版规则源重新生成产物 =="
    run_builder build-karing-rules.py
    run_builder build-shadowrocket-rules.py
    run_builder build-clash-rules.py
    run_builder build-hiddify-rules.py
    echo
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

ARTIFACTS=(
    "karing/karing-diversion-rules.json"
    "docs/karing/karing-diversion-rules.json"
    "shadowrocket/Shadowrocket.rules.conf"
    "shadowrocket/Shadowrocket.conf"
    "shadowrocket/星君分流.conf"
    "clash/clash-override.yaml"
    "hiddify/hiddify-route-rules.json"
    "hiddify/import-link.txt"
)

if ! run_builder build-karing-rules.py --out-dir "$TMP_DIR" >/dev/null; then
    echo "错误: Karing 产物生成失败，先解决上面的报错"
    exit 1
fi
if ! run_builder build-shadowrocket-rules.py --out-dir "$TMP_DIR" >/dev/null; then
    echo "错误: Shadowrocket 产物生成失败，先解决上面的报错"
    exit 1
fi
if ! run_builder build-clash-rules.py --out-dir "$TMP_DIR" >/dev/null; then
    echo "错误: Clash 产物生成失败，先解决上面的报错"
    exit 1
fi
if ! run_builder build-hiddify-rules.py --out-dir "$TMP_DIR" >/dev/null; then
    echo "错误: Hiddify 产物生成失败，先解决上面的报错"
    exit 1
fi

# 生成脚本必须真的产出全部文件。少了就直接判失败 —— 否则下面的比对可能
# 因为「临时目录里啥都没有」而得出一个看似正常、其实没在检查的结果。
for rel in "${ARTIFACTS[@]}"; do
    if [ ! -f "$TMP_DIR/$rel" ]; then
        echo "错误: 生成脚本没有产出 $rel，漂移检测不可信"
        exit 1
    fi
done

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
    echo "产物与 PC 版源码一致。"
    exit 0
fi

if [ "$FIX" -eq 1 ]; then
    echo "重新生成后仍有差异，说明生成脚本不是确定性的，需要排查。"
    exit 1
fi

echo "发现漂移：PC 版配置已变，但仓库产物还是旧的。"
echo "在手机上真正生效前，先跑一次：bash scripts/check-drift.sh --fix"
exit 1
