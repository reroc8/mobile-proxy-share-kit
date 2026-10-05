#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 PC 版 Clash Verge 的 Merge.yaml 生成 Shadowrocket 的三份 .conf。

为什么需要这个脚本
------------------
Shadowrocket 的规则原来是手工维护的，停在了 v0.1.2 的快照上，PC 端后来新增的
93 条域名（国内 AI 全家桶、Claude 边缘域名、Antigravity/Jules/Opal、Telegram 新
域名、地区特例）一条都没跟过来。改成和 Karing 一样从 Merge.yaml 生成，两边不再漂。

转换规则
--------
* 显式规则  DOMAIN-SUFFIX / DOMAIN / DOMAIN-KEYWORD 原样搬运（Shadowrocket 本来
            就是 Clash 风格的规则语法，不需要改格式）。
* 策略名    用 TARGET_MAP 把 PC 的策略名映射为 Shadowrocket 的策略名。
* RULE-SET  Shadowrocket 没有 mihomo 规则集的概念，PC 靠 RULE-SET 表达的宽泛覆盖
            在 RULE_SET_EXPANSION 里展开成显式域名。这份展开表就是 PC 规则集的等价物。
* 无关类型  PROCESS-NAME / IP-CIDR / MATCH 等跳过，和 Karing 脚本保持同一套判断。

产物
----
    shadowrocket/Shadowrocket.rules.conf   纯规则片段（含 [General]）
    shadowrocket/Shadowrocket.conf         同上，旧链接兼容文件
    shadowrocket/Shadowrocket.full.conf    完整骨架模板（多一段 [Proxy Group]）

用法
----
    python3 scripts/build-shadowrocket-rules.py [Merge.yaml 路径]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHADOWROCKET_DIR = REPO_ROOT / "shadowrocket"

DEFAULT_SOURCE = (
    Path.home() / "Desktop" / "Clash配置" / "clash-verge-share-kit" / "config" / "Merge.yaml"
)

# PC 策略名 -> Shadowrocket 策略名。US / SG 在 Shadowrocket 侧新建同名策略组。
TARGET_MAP = {
    "DIRECT": "DIRECT",
    "Claude": "Claude",
    "AI": "AI",
    "Google": "Google",
    "YouTube": "YouTube",
    "Telegram": "Telegram",
    "Proxies": "Proxy",
    "US": "US",
    "SG": "SG",
}

# 输出顺序即 Rule 段的书写顺序，Shadowrocket 自上而下匹配，先命中先生效。
#
# YouTube 必须排在 Google 前面：YouTube 的 .youtubei.googleapis.com 会被 Google 的
# .googleapis.com 抢走。PC 版也是先写 YouTube 再套 RULE-SET,google，这里对齐它。
OUTPUT_ORDER = (
    "DIRECT",
    "Claude",
    "AI",
    "YouTube",
    "Google",
    "Exchange",
    "Telegram",
    "US",
    "SG",
    "Proxy",
)

# LAN / 本地地址直连。Shadowrocket 独有的写法，PC 靠 private-domain / private-ip 规则集。
LOCAL_RULES = (
    ("DOMAIN-SUFFIX", "local"),
    ("IP-CIDR", "10.0.0.0/8"),
    ("IP-CIDR", "100.64.0.0/10"),
    ("IP-CIDR", "127.0.0.0/8"),
    ("IP-CIDR", "169.254.0.0/16"),
    ("IP-CIDR", "172.16.0.0/12"),
    ("IP-CIDR", "192.168.0.0/16"),
)

# Telegram 官方 IP 段，对应 PC 的 RULE-SET,telegramcidr。
TELEGRAM_CIDR = (
    "91.108.4.0/22",
    "91.108.8.0/21",
    "91.108.16.0/22",
    "91.108.56.0/22",
    "149.154.160.0/20",
)

# PC 用 RULE-SET 表达、Shadowrocket 只能写显式域名的部分。
# 每条都标注了对应的 PC 规则集，别当成随手加的。
RULE_SET_EXPANSION = {
    # 对应 RULE-SET,cn-domain 与 RULE-SET,applications：国内常见服务直连
    "DIRECT": (
        ("DOMAIN-SUFFIX", "alipay.com"),
        ("DOMAIN-SUFFIX", "taobao.com"),
        ("DOMAIN-SUFFIX", "tmall.com"),
        ("DOMAIN-SUFFIX", "jd.com"),
        ("DOMAIN-SUFFIX", "baidu.com"),
        ("DOMAIN-SUFFIX", "bdstatic.com"),
        ("DOMAIN-SUFFIX", "bilibili.com"),
        ("DOMAIN-SUFFIX", "bilivideo.com"),
        ("DOMAIN-SUFFIX", "douyin.com"),
        ("DOMAIN-SUFFIX", "douyincdn.com"),
        ("DOMAIN-SUFFIX", "byteimg.com"),
        ("DOMAIN-SUFFIX", "qq.com"),
        ("DOMAIN-SUFFIX", "tencent.com"),
        ("DOMAIN-SUFFIX", "weixin.qq.com"),
        ("DOMAIN-SUFFIX", "wechat.com"),
        ("DOMAIN-SUFFIX", "cn"),
        ("DOMAIN-KEYWORD", "-cn"),
    ),
    # 对应 RULE-SET,google：Google 全站
    "Google": (
        ("DOMAIN-SUFFIX", "gmail.com"),
        ("DOMAIN-SUFFIX", "googlemail.com"),
        ("DOMAIN-SUFFIX", "google.com"),
        ("DOMAIN-SUFFIX", "gstatic.com"),
        ("DOMAIN-SUFFIX", "googleapis.com"),
        ("DOMAIN-SUFFIX", "googleusercontent.com"),
    ),
    # 对应 RULE-SET,global-domain 与 RULE-SET,tld-proxy：通用海外站点
    "Proxies": (
        ("DOMAIN-SUFFIX", "github.com"),
        ("DOMAIN-SUFFIX", "githubusercontent.com"),
        ("DOMAIN-SUFFIX", "githubassets.com"),
        ("DOMAIN-SUFFIX", "ghcr.io"),
        ("DOMAIN-SUFFIX", "discord.com"),
        ("DOMAIN-SUFFIX", "discord.gg"),
        ("DOMAIN-SUFFIX", "netflix.com"),
        ("DOMAIN-SUFFIX", "nflxvideo.net"),
        ("DOMAIN-SUFFIX", "spotify.com"),
        ("DOMAIN-SUFFIX", "scdn.co"),
        ("DOMAIN-SUFFIX", "reddit.com"),
        ("DOMAIN-SUFFIX", "redd.it"),
        ("DOMAIN-SUFFIX", "redditstatic.com"),
        ("DOMAIN-SUFFIX", "x.com"),
        ("DOMAIN-SUFFIX", "twitter.com"),
        ("DOMAIN-SUFFIX", "twimg.com"),
        ("DOMAIN-SUFFIX", "instagram.com"),
        ("DOMAIN-SUFFIX", "facebook.com"),
        ("DOMAIN-SUFFIX", "fbcdn.net"),
        ("DOMAIN-SUFFIX", "cloudflare.com"),
        ("DOMAIN-SUFFIX", "cloudfront.net"),
        ("DOMAIN-SUFFIX", "amazonaws.com"),
        ("DOMAIN-SUFFIX", "azureedge.net"),
        ("DOMAIN-SUFFIX", "akamaized.net"),
    ),
}

# Shadowrocket 独有的业务，PC 版完全没有对应分组，保留是为了不砍功能。
# 对齐 PC 不等于砍掉 PC 没有的东西 —— 只砍 PC 明确判定为误绑的。
SHADOWROCKET_ONLY = {
    "Exchange": (
        ("DOMAIN-SUFFIX", "okx.com"),
        ("DOMAIN-SUFFIX", "okx-dns.com"),
        ("DOMAIN-SUFFIX", "bybit.com"),
        ("DOMAIN-SUFFIX", "bycsi.com"),
        ("DOMAIN-SUFFIX", "binance.com"),
        ("DOMAIN-SUFFIX", "binance.me"),
        ("DOMAIN-SUFFIX", "binance.info"),
        ("DOMAIN-SUFFIX", "binancecnt.com"),
        ("DOMAIN-SUFFIX", "bntrace.com"),
        ("DOMAIN-SUFFIX", "bitget.com"),
        ("DOMAIN-SUFFIX", "gate.io"),
        ("DOMAIN-SUFFIX", "gateio.live"),
        ("DOMAIN-SUFFIX", "kucoin.com"),
        ("DOMAIN-SUFFIX", "kucnck.com"),
        ("DOMAIN-SUFFIX", "mexc.com"),
        ("DOMAIN-SUFFIX", "mexc.co"),
        ("DOMAIN-SUFFIX", "crypto.com"),
        ("DOMAIN-SUFFIX", "coinbase.com"),
        ("DOMAIN-SUFFIX", "kraken.com"),
        ("DOMAIN-SUFFIX", "htx.com"),
        ("DOMAIN-SUFFIX", "huobi.com"),
        ("DOMAIN-SUFFIX", "bingx.com"),
        ("DOMAIN-SUFFIX", "bitmart.com"),
        ("DOMAIN-SUFFIX", "bitfinex.com"),
        ("DOMAIN-SUFFIX", "bitstamp.net"),
        ("DOMAIN-SUFFIX", "upbit.com"),
    ),
}

# PC 规则集 -> Shadowrocket 侧的处理方式。值同时说明「在哪被覆盖」，不能是 None，
# 否则等于静默丢弃，所以这里逐条写清楚。出现表里没有的规则集就直接报错。
RULE_SET_COVERAGE = {
    # 私有地址由 LOCAL_RULES 常量覆盖
    "private-domain": "LOCAL_RULES",
    "private-ip": "LOCAL_RULES",
    # Telegram 官方 IP 段由 TELEGRAM_CIDR 常量覆盖
    "telegramcidr": "TELEGRAM_CIDR",
    # 以下三项展开成显式域名，见 RULE_SET_EXPANSION
    "google": "RULE_SET_EXPANSION[Google]",
    "cn-domain": "RULE_SET_EXPANSION[DIRECT]",
    "applications": "RULE_SET_EXPANSION[DIRECT]",
    "global-domain": "RULE_SET_EXPANSION[Proxies]",
    "tld-proxy": "RULE_SET_EXPANSION[Proxies]",
    # 国内 IP 段由 Rule 段末尾的 GEOIP,CN,DIRECT 覆盖
    "cn-ip": "GEOIP,CN,DIRECT",
    # Apple / iCloud 直连：本包兜底就是直连，不需要在 Rule 段单列
    "apple": "兜底直连（FINAL,DIRECT）",
    "icloud": "兜底直连（FINAL,DIRECT）",
}

# Shadowrocket 没有匹配到的规则类型，显式跳过而不是静默丢弃。
SKIP_PREFIXES = ("PROCESS-NAME", "PROCESS-PATH", "MATCH", "GEOIP", "SRC-IP-CIDR")

HEADER = (
    "# Mobile Proxy Share Kit for Shadowrocket",
    "# 由 scripts/build-shadowrocket-rules.py 从 PC 版 Merge.yaml 生成，勿手改。",
)

GENERAL = (
    "[General]",
    "dns-server = https://doh.pub/dns-query, https://dns.alidns.com/dns-query",
    "bypass-system = true",
    "ipv6 = false",
    "skip-proxy = localhost, *.local, captive.apple.com, 0.0.0.0/8, 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4, 255.255.255.255/32",
)

# 先声明 Proxy，后面各策略都引用它
PROXY_GROUP = (
    "[Proxy Group]",
    "Proxy = select, DIRECT",
    "Claude = select, Proxy",
    "AI = select, Proxy",
    "Google = select, Proxy",
    "YouTube = select, Proxy",
    "Exchange = select, Proxy",
    "Telegram = select, Proxy",
    "US = select, Proxy",
    "SG = select, Proxy",
)


class BuildError(Exception):
    pass


def parse_merge_rules(path: Path) -> list[tuple[str, str, str]]:
    """只解析 Merge.yaml 顶层 rules: 段。和 Karing 脚本同一套逻辑。"""
    lines = path.read_text(encoding="utf-8").splitlines()

    start = None
    for index, line in enumerate(lines):
        if line.rstrip() == "rules:":
            start = index
            break
    if start is None:
        raise BuildError(f"{path} 里找不到顶层 rules: 段")

    entries: list[tuple[str, str, str]] = []
    for raw in lines[start + 1 :]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith("  - "):
            break

        item = re.split(r"\s+#", raw[4:].strip())[0].strip()
        parts = [part.strip() for part in item.split(",")]
        if len(parts) < 2:
            raise BuildError(f"无法解析的规则行: {raw!r}")
        entries.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return entries


def collect(entries: list[tuple[str, str, str]]) -> dict[str, list[tuple[str, str]]]:
    rules: dict[str, list[tuple[str, str]]] = {}
    for name in OUTPUT_ORDER:
        rules[name] = []

    seen: dict[str, set[tuple[str, str]]] = {name: set() for name in OUTPUT_ORDER}

    def add(policy: str, rule: tuple[str, str]) -> None:
        if rule not in seen[policy]:
            seen[policy].add(rule)
            rules[policy].append(rule)

    for rule_type, value, target in entries:
        if rule_type == "RULE-SET":
            if value not in RULE_SET_COVERAGE:
                raise BuildError(
                    f"Merge.yaml 出现未登记的规则集 {value!r}；"
                    "请在 RULE_SET_COVERAGE 里说明它在 Shadowrocket 侧怎么覆盖"
                )
            continue
        if rule_type.startswith(SKIP_PREFIXES):
            continue
        if rule_type not in ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"):
            raise BuildError(f"未处理的规则类型 {rule_type!r}（值 {value!r}）")
        if target not in TARGET_MAP:
            raise BuildError(f"未知策略名 {target!r}（来自 {rule_type},{value}）")
        add(TARGET_MAP[target], (rule_type, value))

    # PC 靠 RULE-SET 表达的宽泛覆盖
    for pc_target, extra in RULE_SET_EXPANSION.items():
        for rule in extra:
            add(TARGET_MAP[pc_target], rule)

    # Shadowrocket 独有
    for policy, extra in SHADOWROCKET_ONLY.items():
        for rule in extra:
            add(policy, rule)

    return rules


def render_rules(rules: dict[str, list[tuple[str, str]]]) -> list[str]:
    lines = ["[Rule]", "# LAN / local"]
    for rule_type, value in LOCAL_RULES:
        suffix = ",no-resolve" if rule_type == "IP-CIDR" else ""
        lines.append(f"{rule_type},{value},DIRECT{suffix}")

    for policy in OUTPUT_ORDER:
        body = rules[policy]
        if not body:
            raise BuildError(f"{policy} 策略没有任何规则，检查 Merge.yaml 是否还包含对应策略")
        lines.append(f"# {policy}")
        for rule_type, value in body:
            lines.append(f"{rule_type},{value},{policy}")
        if policy == "Telegram":
            for cidr in TELEGRAM_CIDR:
                lines.append(f"IP-CIDR,{cidr},Telegram,no-resolve")

    lines.append("# 国内 IP 直连，然后保守兜底")
    lines.append("GEOIP,CN,DIRECT")
    lines.append("FINAL,DIRECT")
    return lines


def render(rules: dict[str, list[tuple[str, str]]], include_proxy_group: bool) -> str:
    body = list(HEADER)
    body += ["", *GENERAL]
    if include_proxy_group:
        body += ["", *PROXY_GROUP]
    body += [""]
    body += render_rules(rules)
    return "\n".join(body) + "\n"


def summarize(rules: dict[str, list[tuple[str, str]]]) -> str:
    return "\n".join(
        f"  {policy:<10} {len(rules[policy])} 条域名规则" for policy in OUTPUT_ORDER
    )


def main(argv: list[str]) -> int:
    source = Path(argv[1]).expanduser() if len(argv) > 1 else DEFAULT_SOURCE
    if not source.is_file():
        print(f"错误: 找不到规则源 {source}", file=sys.stderr)
        return 1

    try:
        rules = collect(parse_merge_rules(source))
        slim = render(rules, include_proxy_group=False)
        full = render(rules, include_proxy_group=True)
    except BuildError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1

    outputs = (
        (SHADOWROCKET_DIR / "Shadowrocket.rules.conf", slim),
        (SHADOWROCKET_DIR / "Shadowrocket.conf", slim),
        (SHADOWROCKET_DIR / "Shadowrocket.full.conf", full),
    )
    for path, content in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    print(f"规则源: {source}")
    print(summarize(rules))
    for path, _ in outputs:
        print(f"已写入: {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
