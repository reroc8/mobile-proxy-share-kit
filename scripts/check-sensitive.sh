#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PATTERN='(ss://[A-Za-z0-9+/=_-]{8,}|ssr://[A-Za-z0-9+/=_-]{8,}|vmess://[A-Za-z0-9+/=_-]{8,}|vless://[^[:space:]]{12,}|trojan://[^[:space:]]{12,}|hysteria2://[^[:space:]]{12,}|hy2://[^[:space:]]{12,}|tuic://[^[:space:]]{12,}|reality-opts|private-key|client-fingerprint|uuid:[[:space:]]*[0-9a-fA-F-]{20,}|password:[[:space:]]*[^[:space:]#]{8,})'

cd "$ROOT_DIR"

SCAN_PATHS=(
    README.md
    CHANGELOG.md
    VERSION.txt
    shadowrocket
    docs
)

if command -v rg >/dev/null 2>&1; then
    if rg -n -i "$PATTERN" "${SCAN_PATHS[@]}"; then
        echo "错误: 发现疑似订阅或节点敏感信息"
        exit 1
    fi
else
    if find "${SCAN_PATHS[@]}" -type f -print0 | xargs -0 grep -nEi "$PATTERN"; then
        echo "错误: 发现疑似订阅或节点敏感信息"
        exit 1
    fi
fi

echo "敏感信息扫描通过"
