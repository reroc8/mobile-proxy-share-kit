#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 PC 版 Clash Verge 的 Merge.yaml 生成 Karing「自定义分流组」JSON。

为什么需要这个脚本
------------------
Karing 导入 Clash 配置时只取节点，不读 proxy-groups / rules，分流必须用它自己的
「自定义分流组」系统（导出的格式就是本脚本产出的 JSON）。手工维护那份 JSON 会和
PC 版规则逐渐漂移，所以以 PC 版仓库的 Merge.yaml 为唯一规则源，脚本负责转换。

转换规则
--------
* 显式规则  DOMAIN-SUFFIX,example.com,TARGET  ->  domain_suffix: ".example.com"
            DOMAIN,example.com,TARGET         ->  domain: "example.com"
            DOMAIN-KEYWORD,foo,TARGET         ->  domain_keyword: "foo"
  （domain_suffix 的值带前导点，这是 Karing 导出格式的实测写法。）
* RULE-SET  由 RULE_SET_MAP 表映射为 Karing 内置规则集 rule_set_build_in。
* 其余类型  进程名、IP-CIDR、MATCH 等无法迁移，按 SKIP_PREFIXES 显式跳过。

用法
----
    python3 scripts/build-karing-rules.py [规则源] [--out-dir 目录]

不传规则源时拉取 PC 版仓库的 GitHub 源码（见 mobile_rules.SOURCE_URL）；
离线或想用本地副本时传路径即可。产出两份内容完全一致的 JSON：
    karing/karing-diversion-rules.json        发布包内的正式产物
    docs/karing/karing-diversion-rules.json   GitHub Pages 同源副本（供手机一键下载）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobile_rules import (  # noqa: E402  （必须先加 sys.path）
    DOMAIN_TYPES,
    REPO_ROOT,
    BuildError,
    describe_source,
    load_extra_rules,
    parse_args,
    parse_merge_rules,
)

# 银行 / 券商的域名。Karing 的内置规则集（acl: / geosite: / geoip:）里没有金融分类，
# 只能写显式域名；这些是从 LingJingMaster 的规则集**生成时**转过来的。
# 注意：这是快照 —— 对方更新了要重新跑生成脚本，不像 Shadowrocket 那份是运行时拉取。
LINGJING = "https://raw.githubusercontent.com/LingJingMaster/Shadowrocket-Rules/refs/heads/main"
REMOTE_DOMAIN_GROUPS = {
    "Banks": (f"{LINGJING}/HK_Banks_Direct.list", f"{LINGJING}/HSBC_HK.list"),
    "Brokers": (f"{LINGJING}/HK_Broker.list",),
}


def fetch_remote_domain_rules(names: tuple[str, ...]) -> dict[str, list[str]]:
    """把 Surge 风格的 .list 转成 Karing 的 domain / domain_suffix / domain_keyword 列表。"""
    import urllib.request

    out: dict[str, list[str]] = {"domain": [], "domain_suffix": [], "domain_keyword": []}
    seen: set[tuple[str, str]] = set()
    for url in names:
        with urllib.request.urlopen(url, timeout=30) as response:
            body = response.read().decode("utf-8", "replace")
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split(",")]
            kind, value = parts[0], parts[1] if len(parts) > 1 else ""
            if not value:
                continue
            key = {"DOMAIN": "domain", "DOMAIN-SUFFIX": "domain_suffix",
                   "DOMAIN-KEYWORD": "domain_keyword"}.get(kind)
            if not key or (key, value) in seen:
                continue
            seen.add((key, value))
            out[key].append(value)
    return {k: v for k, v in out.items() if v}


# 产物路径相对于「输出根目录」。默认是仓库根，可用 --out-dir 指向别处，
# 供 scripts/check-drift.sh 生成到临时目录做比对。
OUTPUT_SUFFIXES = (
    Path("karing") / "karing-diversion-rules.json",
    Path("docs") / "karing" / "karing-diversion-rules.json",
)

# ── 分组成员 ────────────────────────────────────────────────────────────────
# 顺序即 Karing「分流规则」页里的匹配顺序，元素越靠前优先级越高。
# 两个产物的组顺序必须一致：Shadowrocket 脚本里是同一个列表。
#
# 精确规则（Claude / AI / YouTube / Google / Exchange / Telegram / US / SG）全部排在
# 宽泛规则（国内直连 / 代理）之前，这是硬要求：PC 版里 tgalileo.com 同时出现在
# cn-domain 规则集里，靠「精确规则前置」才能改走代理。国内直连一旦提前就会把它
# 判成直连，和 PC 的意图相反。
#
# YouTube 又必须排在 Google 之前：youtubei.googleapis.com 会被 googleapis.com 抢走。
#
# clash_targets 是 Merge.yaml 里该组的策略名。extra 是从
# scripts/extra-rules.json 读的、PC 没有的分组。
#
# outbound 只写「开箱可用」的值：currentSelected（当前选择）/ direct（直连）。
# 地区隔离（例如 Claude 只走美国）需要用户自己的地区自动选择组，在
# 「分流规则」页逐组改出站，不写进 JSON —— 因为组名由用户自己起。
#
# build_in 是 Karing 内置规则集，用来补上 Merge.yaml 里靠 RULE-SET 表达的
# 宽泛覆盖。名字取自 Karing 自带预设 assets/datas/preset/{default,cn}.json。
GROUPS = (
    {
        "name": "🤖 Claude",
        "outbound": "currentSelected",
        "clash_targets": ("Claude",),
        "build_in": ("acl:Claude",),
    },
    {
        "name": "🧠 国际 AI",
        "outbound": "currentSelected",
        "clash_targets": ("AI",),
        "build_in": ("geosite:openai", "geoip:openai", "acl:Gemini"),
    },
    {
        "name": "🎬 YouTube",
        "outbound": "currentSelected",
        "clash_targets": ("YouTube",),
        "build_in": (),
    },
    {
        "name": "🌐 Google",
        "outbound": "currentSelected",
        "clash_targets": ("Google",),
        "build_in": ("geosite:google",),
    },
    {
        "name": "💱 交易所",
        "outbound": "currentSelected",
        "clash_targets": (),
        "extra": "Exchange",
        "build_in": (),
    },
    {
        "name": "✈️ Telegram",
        "outbound": "currentSelected",
        "clash_targets": ("Telegram",),
        "build_in": ("geoip:telegram",),
    },
    {
        "name": "🏦 银行",
        "outbound": "currentSelected",
        "clash_targets": ("Banks",),
        "remote": "Banks",
        "build_in": (),
    },
    {
        "name": "📈 券商",
        "outbound": "currentSelected",
        "clash_targets": ("Brokers",),
        "remote": "Brokers",
        "build_in": (),
    },
    {
        "name": "🇺🇸 美国",
        "outbound": "currentSelected",
        "clash_targets": ("US",),
        "build_in": (),
    },
    {
        "name": "🇸🇬 新加坡",
        "outbound": "currentSelected",
        "clash_targets": ("SG",),
        "build_in": (),
    },
    {
        "name": "🏠 国内直连",
        "outbound": "direct",
        "clash_targets": ("DIRECT",),
        "build_in": ("acl:ChinaDomain", "acl:ChinaIp"),
    },
    {
        "name": "🚀 代理",
        "outbound": "currentSelected",
        "clash_targets": ("Proxies",),
        "build_in": ("geosite:geolocation-!cn",),
    },
)

# ── RULE-SET 映射表 ────────────────────────────────────────────────────────
# 值是 (clash_target, build_in) 或 None。
# None 表示 PC 端该规则集的语义在 Karing 上有更合适的处理方式，不需要搬运，
# 原因写在 REASON 里，避免以后有人误以为是漏掉了。
RULE_SET_MAP = {
    # 局域网 / 私有地址：Karing 内核自带 bypass 直连，无需搬运
    "private-domain": None,
    "private-ip": None,
    # Apple / iCloud 直连：本包兜底就是直连，单独建组只会增加噪音
    "apple": None,
    "icloud": None,
    # 应用类直连规则集：Karing 用「应用包 id / 进程名」按本机配置，搬过去没有意义
    "applications": None,
    # 国外顶级域名整体代理：Karing 兜底为直连，照搬会把大量国内 .com 误送代理
    "tld-proxy": None,
    # 需要搬运的宽泛覆盖
    "google": ("Google", "geosite:google"),
    "cn-domain": ("DIRECT", "acl:ChinaDomain"),
    "cn-ip": ("DIRECT", "acl:ChinaIp"),
    "global-domain": ("Proxies", "geosite:geolocation-!cn"),
    "telegramcidr": ("Telegram", "geoip:telegram"),
}

# 这些前缀的规则无法迁移到 Karing 分流组，显式跳过而不是静默丢弃。
SKIP_PREFIXES = ("PROCESS-NAME", "PROCESS-PATH", "IP-CIDR", "IP-CIDR6", "MATCH", "GEOIP", "SRC-IP-CIDR")

def build_document(entries: list[tuple[str, str, str]]) -> dict:
    by_group: dict[str, dict[str, list[str]]] = {
        group["name"]: {"domain_suffix": [], "domain": [], "domain_keyword": []} for group in GROUPS
    }
    group_of_target = {}
    for group in GROUPS:
        for target in group["clash_targets"]:
            # 一个 PC 策略只能归一个 Karing 组。漏改这里会让先声明的组静默吞掉规则，
            # 所以宁可报错也不要「后者覆盖前者」。
            if target in group_of_target:
                raise BuildError(
                    f"策略 {target!r} 同时被 {group_of_target[target]} 和 {group['name']} 声明"
                )
            group_of_target[target] = group["name"]

    referenced_build_in: set[tuple[str, str]] = set()

    for rule_type, value, target in entries:
        if rule_type == "RULE-SET":
            if value not in RULE_SET_MAP:
                raise BuildError(
                    f"Merge.yaml 出现未登记的规则集 {value!r}；请在 RULE_SET_MAP 里显式登记"
                )
            mapped = RULE_SET_MAP[value]
            if mapped is None:
                continue
            mapped_target, build_in = mapped
            if mapped_target != target:
                raise BuildError(
                    f"规则集 {value!r} 的目标是 {target}，但 RULE_SET_MAP 记为 {mapped_target}"
                )
            if build_in not in next(
                g["build_in"] for g in GROUPS if g["name"] == group_of_target[target]
            ):
                raise BuildError(
                    f"内置规则集 {build_in!r} 没有声明在 {group_of_target[target]} 组的 build_in 里"
                )
            referenced_build_in.add((group_of_target[target], build_in))
            continue

        if rule_type.startswith(SKIP_PREFIXES):
            continue

        if rule_type not in DOMAIN_TYPES:
            raise BuildError(f"未处理的规则类型 {rule_type!r}（值 {value!r}）")

        if target not in group_of_target:
            raise BuildError(f"未知策略名 {target!r}（来自 {rule_type},{value}）")

        bucket = by_group[group_of_target[target]]
        if rule_type == "DOMAIN-SUFFIX":
            key, normalized = "domain_suffix", value if value.startswith(".") else "." + value
        elif rule_type == "DOMAIN":
            key, normalized = "domain", value
        else:
            key, normalized = "domain_keyword", value
        if normalized not in bucket[key]:
            bucket[key].append(normalized)

    # 银行 / 券商：Karing 内置规则集里没有金融分类，域名从远程清单转过来（生成时快照）
    remote_cache: dict[str, dict[str, list[str]]] = {}
    for group in GROUPS:
        remote_key = group.get("remote")
        if not remote_key:
            continue
        if remote_key not in REMOTE_DOMAIN_GROUPS:
            raise BuildError(f"{group['name']} 组引用了未登记的远程域名组 {remote_key!r}")
        if remote_key not in remote_cache:
            remote_cache[remote_key] = fetch_remote_domain_rules(REMOTE_DOMAIN_GROUPS[remote_key])
        bucket = by_group[group["name"]]
        for key, values in remote_cache[remote_key].items():
            for value in values:
                normalized = value if key != "domain_suffix" else (
                    value if value.startswith(".") else "." + value
                )
                if normalized not in bucket[key]:
                    bucket[key].append(normalized)

    # PC 没有的分组，规则来自 scripts/extra-rules.json
    extra_definitions = load_extra_rules()
    for group in GROUPS:
        extra_key = group.get("extra")
        if not extra_key:
            continue
        if extra_key not in extra_definitions:
            raise BuildError(f"{group['name']} 组引用了 extra-rules.json 里不存在的 {extra_key!r}")
        bucket = by_group[group["name"]]
        for rule_type, value in extra_definitions[extra_key]["rules"]:
            if rule_type == "DOMAIN-SUFFIX":
                key, normalized = "domain_suffix", value if value.startswith(".") else "." + value
            elif rule_type == "DOMAIN":
                key, normalized = "domain", value
            elif rule_type == "DOMAIN-KEYWORD":
                key, normalized = "domain_keyword", value
            else:
                raise BuildError(f"extra-rules.json 里 {extra_key!r} 出现未处理的类型 {rule_type!r}")
            if normalized not in bucket[key]:
                bucket[key].append(normalized)

    rules = []
    for group in GROUPS:
        name = group["name"]
        rule: dict[str, object] = {
            "outbound": group["outbound"],
            "name": name,
            "switch": True,
            "or": True,
        }
        # 字段顺序对齐 Karing 自身导出的格式，保持逐字节可比对
        for key in ("domain_suffix", "domain", "domain_keyword"):
            if by_group[name][key]:
                rule[key] = by_group[name][key]
        if group["build_in"]:
            rule["rule_set_build_in"] = list(group["build_in"])

        if len(rule) <= 4:
            missing = "、".join(group["clash_targets"]) or group.get("extra", "")
            raise BuildError(
                f"{name} 组没有任何规则（来自策略 {missing}）；"
                "检查 Merge.yaml 或 extra-rules.json 是否还包含对应内容"
            )
        rules.append(rule)

    # build_in 里有些是 RULE-SET 的替代品，有些是纯补充（例如 acl:Claude 用来补齐
    # Merge.yaml 手工维护时容易漏掉的 Anthropic 边缘域名）。这里只做统计，
    # 不强制每个内置规则集都必须有对应的 RULE-SET。
    substituted = sorted({item for _, item in referenced_build_in})
    supplementary = sorted(
        {
            item
            for group in GROUPS
            for item in group["build_in"]
            if (group["name"], item) not in referenced_build_in
        }
    )
    return {"rules": rules}, substituted, supplementary


def summarize(document: dict) -> str:
    lines = []
    for rule in document["rules"]:
        counts = " ".join(
            f"{key}={len(rule[key])}"
            for key in ("domain_suffix", "domain", "domain_keyword", "rule_set_build_in")
            if key in rule
        )
        lines.append(f"  {rule['name']:<14} outbound={rule['outbound']:<15} {counts}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    try:
        source, out_dir = parse_args(argv)
        document, substituted, supplementary = build_document(parse_merge_rules(source))
    except BuildError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1

    outputs = [out_dir / suffix for suffix in OUTPUT_SUFFIXES]
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    for output in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")

    print(f"规则源: {describe_source(source)}")
    print(summarize(document))
    print(f"内置规则集替代自 RULE-SET: {len(substituted)} 项")
    if supplementary:
        print(f"内置规则集纯补充: {', '.join(supplementary)}")
    for output in outputs:
        print(f"已写入: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
