#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 PC 版 Clash Verge 的 Merge.yaml 生成 Shadowrocket 的三份 .conf。

为什么需要这个脚本
------------------
Shadowrocket 的规则原来是手工维护的，停在了 v0.1.2 的快照上，PC 端后来新增的
93 条域名（国内 AI 全家桶、Claude 边缘域名、Antigravity/Jules/Opal、Telegram 新
域名、地区特例）一条都没跟过来。改成和 Karing 一样从 PC 版规则源生成，两边不再漂。

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
    shadowrocket/星君分流.conf    完整骨架模板（多一段 [Proxy Group]）

用法
----
    python3 scripts/build-shadowrocket-rules.py [规则源] [--out-dir 目录]

不传规则源时拉取 PC 版仓库的 GitHub 源码（见 mobile_rules.SOURCE_URL）；
离线或想用本地副本时传路径即可。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobile_rules import (  # noqa: E402  （必须先加 sys.path）
    DOMAIN_TYPES,
    REPO_ROOT,
    SOURCE_REPO,
    BuildError,
    describe_source,
    fetch_source_version,
    load_extra_rules,
    parse_args,
    parse_merge_rules,
    supplemental_entries,
)

# 产物路径相对于「输出根目录」。默认是仓库根，可用 --out-dir 指向别处，
# 供 scripts/check-drift.sh 生成到临时目录做比对。
OUTPUT_NAMES = (
    "Shadowrocket.rules.conf",
    "Shadowrocket.conf",
    # 主入口用中文名：小火箭的配置列表里显示的就是文件名，叫「Shadowrocket.full」
    # 和机场给的 WestData / default 混在一起分不清。用户要求带个人标识。
    "星君分流.conf",
)


# PC 策略名 -> Shadowrocket 策略名。US / SG 在两个产物里都是独立策略组。
TARGET_MAP = {
    # 国内流量不再直接写 DIRECT，改成指向 CN 组 —— 组里默认还是 DIRECT，
    # 但万一某条规则判错，用户能一键切走（同类项目 LingJingMaster 也这么做）。
    "DIRECT": "CN",
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
# 这份顺序必须和 scripts/build-karing-rules.py 里的 GROUPS 完全一致。
#
# 精确规则全部排在宽泛规则（DIRECT / Proxy）之前，这是硬要求：PC 版里
# tgalileo.com 同时出现在 cn-domain 规则集里，靠「精确规则前置」才能改走代理。
# DIRECT 一旦提前就会把它判成直连，和 PC 的意图相反。
#
# YouTube 又必须排在 Google 之前：youtubei.googleapis.com 会被 googleapis.com 抢走。
OUTPUT_ORDER = (
    "Claude",
    "AI",
    "YouTube",
    "Google",
    "Exchange",
    "Telegram",
    "Banks",
    "Brokers",
    "US",
    "SG",
    "CN",
    "Proxy",
)

# 地区识别正则，写给策略组的 policy-regex-filter。
# 参考同类项目（LingJingMaster/Shadowrocket-Rules、IvanSolis1989/Smart-Config-Kit）的写法：
# 机场常用城市名或「沪美」这类缩写命名节点，所以要把它们一并写进去。
# 刻意**不用单字**（如「美」「港」）—— 会误匹配到别的词。
# 只认「旗帜 emoji / 中文 / 英文全称 / 城市名」，**刻意不收两字母缩写**。
#
# 原因：缩写不可靠。加词边界也挡不住 —— 节点叫「🇺🇸 美国 SG 中转」时，那个 SG 本身就是
# 一个独立的词，`(^|[^A-Za-z])SG([^A-Za-z]|$)` 照样命中，于是美国节点被收进 SG 组。
# （用户实际报过：SG 组里有 2 个美国节点。）
#
# 收窄的代价：只写「US 01」「SG-02」这种纯缩写的节点不会进地区组 —— 它们仍在 Proxy 组里，
# 手动选得到。比"选错国家"轻得多。
REGION_FILTERS = {
    "US": "🇺🇸|美国|美國|United States|洛杉矶|圣何塞|西雅图|芝加哥|纽约|达拉斯|凤凰城|硅谷",
    "SG": "🇸🇬|新加坡|狮城|Singapore",
    "HK": "🇭🇰|香港|深港|沪港|京港|广港|Hong Kong|Hongkong",
}

# 细分的地区组（只为别的组提供出口，自己不带规则）
REGION_ONLY = ("HK",)

# 地区组一律用 url-test 自动筛节点 —— 用户不用手动往里拖节点。
# policy-select-name 设默认选中项（小火箭手册第 968 行有官方示例）。
def region_group(name: str) -> str:
    return (
        f"{name} = url-test,url=http://www.gstatic.com/generate_204,interval=600,"
        f"tolerance=0,timeout=5,policy-regex-filter={REGION_FILTERS[name]}"
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

# 这四个组改用远程规则集，不再手写域名。
#
# 手写永远追不上：Google 手写 16 条 vs 规则集 708 条、YouTube 10 vs 199、
# Telegram 12 vs 50、交易所 26 vs 209。小火箭原生支持 RULE-SET 引用远程规则集
# （`配置 > 配置文件 > 编辑配置 > 规则集 URL` 可以看到加载状态），官方推荐配置
# （LOWERTOP 的 lazy_group.conf）就是这么写的。
#
# **Claude 和 AI 两个组故意不换**：Claude.list 只有 10 行，我们手写 11 条还多一点；
# OpenAI 45 + Gemini 21 = 66 行，也不如我们 AI 组的 93 条全 —— 这两块是我们自己的价值，
# 保持手写、可审计。
#
# 规则集来自 blackmatrix7/ios_rule_script，和 PC 版用的是同一个源（PC 用它做 google / global-domain）。
RULE_SET_BASE = (
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket"
)
# (规则类型, URL)。带类型的规则集用 RULE-SET；纯域名列表用 DOMAIN-SET ——
# 后者体积大得多（China_Domain 3699 条、Global_Domain **34922 条**），
# 小火箭对纯域名列表有专门处理，用 DOMAIN-SET 比 RULE-SET 省。
RULE_SETS = {
    "Google": (("RULE-SET", f"{RULE_SET_BASE}/Google/Google.list"),),
    "YouTube": (("RULE-SET", f"{RULE_SET_BASE}/YouTube/YouTube.list"),),
    "Telegram": (("RULE-SET", f"{RULE_SET_BASE}/Telegram/Telegram.list"),),
    # Crypto 是 blackmatrix7 的加密货币分类，比我们的交易所清单宽（含行情站、钱包、DeFi）
    "Exchange": (("RULE-SET", f"{RULE_SET_BASE}/Crypto/Crypto.list"),),
    # 银行 / 券商：blackmatrix7 没有金融类规则集，用 LingJingMaster 的。
    # 这类业务最怕出口地区乱跳触发风控，单独建组就是为了把出口钉住。
    "Banks": (
        ("RULE-SET", "https://raw.githubusercontent.com/LingJingMaster/Shadowrocket-Rules/refs/heads/main/HK_Banks_Direct.list"),
        ("RULE-SET", "https://raw.githubusercontent.com/LingJingMaster/Shadowrocket-Rules/refs/heads/main/HSBC_HK.list"),
    ),
    "Brokers": (
        ("RULE-SET", "https://raw.githubusercontent.com/LingJingMaster/Shadowrocket-Rules/refs/heads/main/HK_Broker.list"),
    ),
    # 国内兜底：把国内域名逐条兜住，不再只靠 GEOIP,CN 按 IP 猜。
    # 少这一层的后果：国内域名解析到海外 IP（用了海外 CDN）时会被送进代理，慢且可能触发异地登录风控。
    "CN": (
        ("RULE-SET", f"{RULE_SET_BASE}/China/China.list"),
        ("DOMAIN-SET", f"{RULE_SET_BASE}/China/China_Domain.list"),
    ),
    # 海外兜底：Global_Domain 有 34922 条，是机场那些几千条规则的来源。
    "Proxy": (
        ("RULE-SET", f"{RULE_SET_BASE}/Global/Global.list"),
        ("DOMAIN-SET", f"{RULE_SET_BASE}/Global/Global_Domain.list"),
    ),
}

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

# Shadowrocket 独有的业务，PC 版完全没有对应分组，定义在 scripts/extra-rules.json，
# 和 Karing 脚本共用同一份。对齐 PC 不等于砍掉 PC 没有的东西 —— 只砍 PC 明确判定为误绑的。

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

HEADER_FIRST_LINE = "# Mobile Proxy Share Kit for Shadowrocket"


def build_header(source_version: str | None) -> list[str]:
    """产物头部。带上 PC 源版本 —— 手机端和 PC 端是两套独立编号，
    只写手机端版本没法知道这份规则对应 PC 的哪一版。"""
    return [
        HEADER_FIRST_LINE,
        "# 由 scripts/build-shadowrocket-rules.py 从 PC 版规则源生成，勿手改。",
        f"# Source: {SOURCE_REPO} {source_version or 'unknown'}",
    ]

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
    # 通用出口：内置 PROXY 指「当前选中的节点」，再挂上地区组方便直接选某地
    "Proxy = select,PROXY,DIRECT,US,SG,HK",
    "CN = select,DIRECT,Proxy,policy-select-name=DIRECT",
    region_group("US"),
    region_group("SG"),
    region_group("HK"),
    # 业务组：默认指到合适的地区组，用户可以随时改
    "Claude = select,US,Proxy,CN,policy-select-name=US",
    "AI = select,US,SG,Proxy,CN,policy-select-name=US",
    "YouTube = select,Proxy,US,SG,CN",
    "Google = select,Proxy,US,SG,CN",
    "Exchange = select,SG,HK,Proxy,CN",
    "Telegram = select,Proxy,US,SG,CN",
    "Banks = select,DIRECT,HK,Proxy,policy-select-name=DIRECT",
    "Brokers = select,HK,US,Proxy,policy-select-name=HK",
)



def collect(entries: list[tuple[str, str, str]]) -> dict[str, list[tuple[str, str]]]:
    rules: dict[str, list[tuple[str, str]]] = {}
    for name in OUTPUT_ORDER:
        rules[name] = []

    seen: dict[str, set[tuple[str, str]]] = {name: set() for name in OUTPUT_ORDER}

    def add(policy: str, rule: tuple[str, str]) -> None:
        if rule not in seen[policy]:
            seen[policy].add(rule)
            rules[policy].append(rule)

    effective_extra = load_extra_rules()

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

    # PC 没有的分组，规则来自 scripts/extra-rules.json
    for extra_key, definition in effective_extra.items():
        if extra_key not in rules:
            raise BuildError(f"extra-rules.json 里的 {extra_key!r} 在 OUTPUT_ORDER 里没有对应策略")
        for rule_type, value in definition["rules"]:
            if rule_type not in ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"):
                raise BuildError(f"extra-rules.json 里 {extra_key!r} 出现未处理的类型 {rule_type!r}")
            add(extra_key, (rule_type, value))

    return rules


def render_rules(rules: dict[str, list[tuple[str, str]]]) -> list[str]:
    lines = ["[Rule]"]
    lines.append("# LAN / local")
    for rule_type, value in LOCAL_RULES:
        suffix = ",no-resolve" if rule_type == "IP-CIDR" else ""
        lines.append(f"{rule_type},{value},DIRECT{suffix}")

    for policy in OUTPUT_ORDER:
        lines.append(f"# {policy}")
        remote_sets = RULE_SETS.get(policy, ())
        for kind, url in remote_sets:
            lines.append(f"{kind},{url},{policy}")

        body = rules[policy]
        if not body and not remote_sets:
            raise BuildError(f"{policy} 策略没有任何规则，检查 Merge.yaml 是否还包含对应策略")
        # 用了规则集的组不再写手写域名：规则集已经覆盖得更全，重复写只是噪音
        if not remote_sets:
            for rule_type, value in body:
                lines.append(f"{rule_type},{value},{policy}")

        if policy == "Telegram":
            for cidr in TELEGRAM_CIDR:
                lines.append(f"IP-CIDR,{cidr},Telegram,no-resolve")

    # 国内 IP 直连，其余兜底走代理。
    #
    # 这里**不能**照抄 PC 版的 MATCH,DIRECT：PC 版前面有 global-domain 规则集兜住海外域名，
    # 最后那条 MATCH 只兜极小一部分；手机端没有那个规则集，同样的兜底会变成
    # 「没列出的墙外站全走直连、打不开」——Wikipedia / IMDb / Bloomberg 这些都会中招。
    # 宁可国内小众站稍慢，也不要墙外站打不开。
    # 国内 IP 也走 CN 组（组里默认 DIRECT），和其他国内规则保持一致 —— 判定错了能一键切走
    lines.append("# 国内 IP")
    lines.append("GEOIP,CN,CN")
    lines.append("# 其余走代理兜底（不要改成 DIRECT，理由见生成脚本注释）")
    lines.append("FINAL,Proxy")
    return lines


def render(
    rules: dict[str, list[tuple[str, str]]],
    include_proxy_group: bool,
    source_version: str | None,
) -> str:
    body = build_header(source_version)
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
    try:
        source, out_dir = parse_args(argv)
        rules = collect(parse_merge_rules(source) + supplemental_entries())
        source_version = fetch_source_version(source)
        slim = render(rules, include_proxy_group=False, source_version=source_version)
        full = render(rules, include_proxy_group=True, source_version=source_version)
    except BuildError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1

    contents = {
        "Shadowrocket.conf": slim,
        "星君分流.conf": full,
    }
    outputs = []
    for name in OUTPUT_NAMES:
        # rules.conf 与 .conf 是同一份内容，.conf 只为兼容旧链接存在
        content = contents.get(name, slim)
        outputs.append((out_dir / "shadowrocket" / name, content))

    for path, content in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    print(f"规则源: {describe_source(source)}")
    print(summarize(rules))
    for path, _ in outputs:
        print(f"已写入: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
