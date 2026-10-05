#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 PC 版 Clash Verge 的 Merge.yaml 生成 Karing「自定义分流组」JSON。

为什么需要这个脚本
------------------
Karing 导入 Clash 配置时只取节点，不读 proxy-groups / rules，分流必须用它自己的
「自定义分流组」系统（导出的格式就是本脚本产出的 JSON）。手工维护那份 JSON 会和
PC 版 Merge.yaml 逐渐漂移，所以以 Merge.yaml 为唯一规则源，脚本负责转换。

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
    python3 scripts/build-karing-rules.py [Merge.yaml 路径]

不传路径时读取 DEFAULT_SOURCE。产出两份内容完全一致的 JSON：
    karing/karing-diversion-rules.json        发布包内的正式产物
    docs/karing/karing-diversion-rules.json   GitHub Pages 同源副本（供手机一键下载）
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_SOURCE = (
    Path.home() / "Desktop" / "Clash配置" / "clash-verge-share-kit" / "config" / "Merge.yaml"
)

OUTPUT_PATHS = (
    REPO_ROOT / "karing" / "karing-diversion-rules.json",
    REPO_ROOT / "docs" / "karing" / "karing-diversion-rules.json",
)

# ── 分组成员 ────────────────────────────────────────────────────────────────
# 顺序即 Karing「分流规则」页里的匹配顺序，元素越靠前优先级越高。
# outbound 只写「开箱可用」的值：currentSelected（当前选择）/ direct（直连）。
# 地区隔离（例如 Claude 只走美国）需要用户自己的地区自动选择组，在
# 「分流规则」页逐组改出站，不写进 JSON —— 因为组名由用户自己起。
#
# clash_targets 是 Merge.yaml 里该组的策略名；US / SG 这类 PC 专属地区组
# 没有对应的 Karing 组，统一并入 🚀 代理。
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
        "name": "🌐 Google",
        "outbound": "currentSelected",
        "clash_targets": ("Google",),
        "build_in": ("geosite:google",),
    },
    {
        "name": "🎬 YouTube",
        "outbound": "currentSelected",
        "clash_targets": ("YouTube",),
        "build_in": (),
    },
    {
        "name": "✈️ Telegram",
        "outbound": "currentSelected",
        "clash_targets": ("Telegram",),
        "build_in": ("geoip:telegram",),
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
        "clash_targets": ("Proxies", "US", "SG"),
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

DOMAIN_TYPES = ("DOMAIN-SUFFIX", "DOMAIN", "DOMAIN-KEYWORD")


class BuildError(Exception):
    pass


def parse_merge_rules(path: Path) -> list[tuple[str, str, str]]:
    """只解析 Merge.yaml 顶层 rules: 段，返回 (类型, 值, 目标) 列表。

    刻意不引 PyYAML：这份文件里我们只用得到 rules 段的扁平结构，手写解析
    少一个依赖，也不会因为文件别处改动而失败。
    """
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
            break  # 遇到下一个顶层键，rules 段结束

        item = re.split(r"\s+#", raw[4:].strip())[0].strip()
        parts = [part.strip() for part in item.split(",")]
        if len(parts) < 2:
            raise BuildError(f"无法解析的规则行: {raw!r}")
        entries.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return entries


def build_document(entries: list[tuple[str, str, str]]) -> dict:
    by_group: dict[str, dict[str, list[str]]] = {
        group["name"]: {"domain_suffix": [], "domain": [], "domain_keyword": []} for group in GROUPS
    }
    group_of_target = {}
    for group in GROUPS:
        for target in group["clash_targets"]:
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
            raise BuildError(f"{name} 组没有任何规则，检查 Merge.yaml 是否还包含对应策略")
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
        lines.append(f"  {rule['name']:<12} outbound={rule['outbound']:<15} {counts}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    source = Path(argv[1]).expanduser() if len(argv) > 1 else DEFAULT_SOURCE
    if not source.is_file():
        print(f"错误: 找不到规则源 {source}", file=sys.stderr)
        return 1

    try:
        document, substituted, supplementary = build_document(parse_merge_rules(source))
    except BuildError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1

    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    for output in OUTPUT_PATHS:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")

    print(f"规则源: {source}")
    print(summarize(document))
    print(f"内置规则集替代自 RULE-SET: {len(substituted)} 项")
    if supplementary:
        print(f"内置规则集纯补充: {', '.join(supplementary)}")
    for output in OUTPUT_PATHS:
        print(f"已写入: {output.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
