#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PATTERN='(ss://[A-Za-z0-9+/=_-]{8,}|ssr://[A-Za-z0-9+/=_-]{8,}|vmess://[A-Za-z0-9+/=_-]{8,}|vless://[^[:space:]]{12,}|trojan://[^[:space:]]{12,}|hysteria2://[^[:space:]]{12,}|hy2://[^[:space:]]{12,}|tuic://[^[:space:]]{12,}|reality-opts|private-key|client-fingerprint|uuid:[[:space:]]*[0-9a-fA-F-]{20,}|password:[[:space:]]*[^[:space:]#]{8,})'

cd "$ROOT_DIR"

if command -v rg >/dev/null 2>&1; then
    if rg -n -i "$PATTERN" --glob '!dist/**' --glob '!.git/**' --glob '!scripts/check-sensitive.sh' .; then
        echo "错误: 发现疑似订阅或节点敏感信息"
        exit 1
    fi
else
    if grep -RInEi "$PATTERN" . --exclude=scripts/check-sensitive.sh --exclude-dir=.git --exclude-dir=dist; then
        echo "错误: 发现疑似订阅或节点敏感信息"
        exit 1
    fi
fi

echo "敏感信息扫描通过"
