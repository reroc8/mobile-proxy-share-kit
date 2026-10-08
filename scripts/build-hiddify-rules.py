#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 PC 版规则源生成 Hiddify 的路由规则，以及一条一键导入链接。

Hiddify 的规则长什么样
----------------------
格式在 `hiddify-app` 的 `android/app/src/main/protos/v2/config/route_rule.proto` 里定义：

    message RouteRule { repeated Rule rules = 1; }
    message Rule {
      uint32 list_order; bool enabled; string name; Outbound outbound;
      repeated string rule_set; repeated string domain;
      repeated string domain_suffix; repeated string domain_keyword;
      repeated string ip_cidr; ...
    }

导入的写法抄自它自己的导出函数（`rules_notifier.dart` 的 `exportJsonToClipboard`）：

    hiddify:///settings/routing-options?routeRule=<base64(JSON)>

两条导入路径：点这个链接（深链接），或者复制它、在 Hiddify 里选「从剪贴板导入」。

⚠️ 一条硬限制：outbound 只有 proxy / direct / direct_with_fragment / block 四个值，
**没有"节点组"的概念**。所以这份产物只能表达「这个域名走不走代理」，
做不到「Claude 走美国、AI 走别的」—— 那是 Shadowrocket / Clash 才有能力做的事。
想清楚这点再决定要不要用它。

用法
----
    python3 scripts/build-hiddify-rules.py [规则源] [--out-dir 目录]
"""

from __future__ import annotations

import base64
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
)

OUTPUT_SUFFIX = Path("hiddify")
RULES_FILE = "hiddify-route-rules.json"
LINK_FILE = "import-link.txt"

# Hiddify 的 outbound 只有这四个值（见 route_rule.proto）
OUTBOUND_PROXY = "proxy"
OUTBOUND_DIRECT = "direct"

# 组名 -> （Hiddify 的 outbound，PC 规则源里的策略名）。
# 顺序就是 list_order —— Hiddify 按这个顺序匹配，精确的排前面。
#
# ⚠️ 这里的"组"和另外三份产物的"策略组"不是一回事：Hiddify 的 outbound 只有
# proxy / direct 两个可用值，所以分组只决定**规则在界面里怎么归拢、能不能单独开关**，
# 不决定走哪个地区的节点。US / SG 因此合并成一组 —— 反正都是"走代理"。
GROUPS = (
    ("🤖 Claude", OUTBOUND_PROXY, ("Claude",)),
    ("🧠 国际 AI", OUTBOUND_PROXY, ("AI",)),
    ("🎬 YouTube", OUTBOUND_PROXY, ("YouTube",)),
    ("🌐 Google", OUTBOUND_PROXY, ("Google",)),
    ("💱 交易所", OUTBOUND_PROXY, ("Exchange",)),
    ("✈️ Telegram", OUTBOUND_PROXY, ("Telegram",)),
    # 银行 / 券商暂时没有：它们在 PC 规则源里不存在，需要额外数据源（另外三份产物
    # 是引 LingJing 的规则集）。等这一层做扎实再加。
    ("🌍 地区锁定", OUTBOUND_PROXY, ("US", "SG")),
    ("🏠 国内直连", OUTBOUND_DIRECT, ("DIRECT",)),
    ("🚀 代理", OUTBOUND_PROXY, ("Proxy", "Proxies")),
)

# 额外来源：这些组在 Merge.yaml 里没有对应策略，规则写在 extra-rules.json
EXTRA_GROUPS = {"💱 交易所": "Exchange"}

# Merge.yaml 里靠 RULE-SET 表达、Hiddify 这边没法用同款写法的，直接跳过。
SKIP_TYPES = ("RULE-SET", "IP-CIDR", "IP-CIDR6", "IP-ASN", "GEOIP", "PROCESS-NAME",
              "PROCESS-NAME-REGEX", "USER-AGENT", "URL-REGEX", "MATCH", "AND", "OR", "NOT")


def build_rule_groups(entries: list[tuple[str, str, str]], extra: dict) -> list[dict]:
    """把 (类型, 值, 策略) 归拢成 Hiddify 的 rules 数组。"""
    by_name: dict[str, dict] = {}
    for name, outbound, _ in GROUPS:
        by_name[name] = {
            "enabled": True,
            "name": name,
            "outbound": outbound,
            "domain": [],
            "domain_suffix": [],
            "domain_keyword": [],
        }

    target_to_name: dict[str, str] = {}
    for name, _, targets in GROUPS:
        for target in targets:
            if target in target_to_name:
                raise BuildError(f"策略 {target!r} 被 {target_to_name[target]} 和 {name} 同时声明")
            target_to_name[target] = name

    for rule_type, value, target in entries:
        if rule_type.startswith(SKIP_TYPES):
            continue
        if rule_type not in DOMAIN_TYPES:
            raise BuildError(f"未处理的规则类型 {rule_type!r}（值 {value!r}）")
        name = target_to_name.get(target)
        if name is None:
            raise BuildError(f"未知策略名 {target!r}（来自 {rule_type},{value}）")

        bucket = by_name[name]
        if rule_type == "DOMAIN-SUFFIX":
            key, normalized = "domain_suffix", value.lstrip(".")
        elif rule_type == "DOMAIN":
            key, normalized = "domain", value
        else:
            key, normalized = "domain_keyword", value
        if normalized not in bucket[key]:
            bucket[key].append(normalized)

    for name, extra_key in EXTRA_GROUPS.items():
        if extra_key not in extra:
            raise BuildError(f"{name} 组引用了 extra-rules.json 里不存在的 {extra_key!r}")
        bucket = by_name[name]
        for rule_type, value in extra[extra_key]["rules"]:
            if rule_type == "DOMAIN-SUFFIX":
                key, normalized = "domain_suffix", value.lstrip(".")
            elif rule_type == "DOMAIN":
                key, normalized = "domain", value
            else:
                key, normalized = "domain_keyword", value
            if normalized not in bucket[key]:
                bucket[key].append(normalized)

    rules: list[dict] = []
    for index, (name, _, _) in enumerate(GROUPS, start=1):
        bucket = by_name[name]
        if not any(bucket[key] for key in ("domain", "domain_suffix", "domain_keyword")):
            raise BuildError(
                f"{name} 组没有任何规则；检查 Merge.yaml 或 extra-rules.json 是否还包含对应内容"
            )
        # 空数组不写出去，保持产物干净
        rule = {key: val for key, val in bucket.items() if val}
        rule["list_order"] = index
        rules.append(rule)
    return rules


def build_document(rules: list[dict], source_version: str | None) -> dict:
    return {"rules": rules}


def build_link(document: dict) -> str:
    """Hiddify 自己导出的写法：base64(JSON) 挂在 routeRule 参数上。"""
    payload = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return f"hiddify:///settings/routing-options?routeRule={encoded}"


def summarize(rules: list[dict]) -> str:
    lines = []
    for rule in rules:
        counts = " ".join(
            f"{key}={len(rule[key])}"
            for key in ("domain_suffix", "domain", "domain_keyword")
            if key in rule
        )
        lines.append(f"  {rule['name']:<14} {rule['outbound']:<7} {counts}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    try:
        source, out_dir = parse_args(argv)
        entries = parse_merge_rules(source)
        version = fetch_source_version(source)
        rules = build_rule_groups(entries, load_extra_rules())
        document = build_document(rules, version)
        link = build_link(document)
    except BuildError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1

    target = out_dir / OUTPUT_SUFFIX
    target.mkdir(parents=True, exist_ok=True)
    (target / RULES_FILE).write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (target / LINK_FILE).write_text(link + "\n", encoding="utf-8")

    print(f"规则源: {describe_source(source)}")
    print(summarize(rules))
    print(f"已写入: {target / RULES_FILE}")
    print(f"已写入: {target / LINK_FILE}（一键导入链接，{len(link)} 字符）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
