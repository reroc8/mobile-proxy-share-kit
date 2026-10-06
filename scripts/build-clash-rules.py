#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 PC 版 Clash Verge 的 Merge.yaml 生成手机端 Clash 覆写。

为什么这份产物最省事
--------------------
PC 版那份 `Merge.yaml` **本身就是 Clash 语法**（`rule-providers` + `rules`），
手机端 Clash（ClashMetaForAndroid / FlClash / Stash，都是 mihomo 内核）能吃同一套。
所以这里不做格式转换，只做两件事：

1. 补一段 `proxy-groups`。PC 那边靠 `Script.js` 按订阅里的节点动态建组，
   手机端没有 JS 执行器，改用 mihomo 的 `include-all` + `filter`：
   按节点名里的地区字样自动把节点收进 `US` / `SG` 组，效果等同 PC 的自动分组。
2. 把 `rule-providers` 和 `rules` 原样搬过来，只把策略名 `Proxies` 改成手机端统一用的 `Proxy`。

组名与 `karing/`、`shadowrocket/` 两份产物完全一致（10 组），规则来源同一份。

用法
----
    python3 scripts/build-clash-rules.py [规则源] [--out-dir 目录]

产物
----
    clash/clash-override.yaml   给 CMFA / FlClash 当「覆写」用
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobile_rules import (  # noqa: E402  （必须先加 sys.path）
    REPO_ROOT,
    SOURCE_REPO,
    BuildError,
    describe_source,
    fetch_source_version,
    load_extra_rules,
    parse_args,
    read_source,
)

OUTPUT_SUFFIX = Path("clash") / "clash-override.yaml"

# PC 的策略名 -> 手机端统一的策略名。其余同名。
TARGET_RENAME = {"Proxies": "Proxy"}

# 地区识别正则，直接取自 PC 版 config/Script.js 的 regionPatterns，
# 保证两边认出来的节点是同一批。
REGION_FILTERS = {
    "US": r"(?i)(美国|美國|United States|(^|[^A-Za-z])US([^A-Za-z]|$)|(^|[^A-Za-z])USA([^A-Za-z]|$)|🇺🇸)",
    "SG": r"(?i)(新加坡|Singapore|(^|[^A-Za-z])SG([^A-Za-z]|$)|🇸🇬)",
}

# 策略组。顺序对齐另外两份产物：精确规则组在前，宽泛的 Proxy 在后。
#
# 地区组用 include-all + filter 自动收节点，并放一个 DIRECT 兜底 ——
# mihomo 不允许组里一个候选都没有，用户订阅里没有美国节点时不能整个配置加载失败。
GROUP_ORDER = (
    ("Claude", ["US", "Proxy", "DIRECT"]),
    ("AI", ["US", "SG", "Proxy", "DIRECT"]),
    ("YouTube", ["Proxy", "US", "SG", "DIRECT"]),
    ("Google", ["Proxy", "US", "SG", "DIRECT"]),
    ("Exchange", ["SG", "Proxy", "DIRECT"]),
    ("Telegram", ["Proxy", "US", "SG", "DIRECT"]),
    ("US", None),
    ("SG", None),
    ("Proxy", None),
)

HEADER = (
    "# Mobile Proxy Share Kit — 手机端 Clash 覆写",
    "# 由 scripts/build-clash-rules.py 从 PC 版规则源生成，勿手改。",
    "#",
    "# 用法：ClashMetaForAndroid / FlClash →「覆写 / Override」→ 粘贴这个文件的内容或地址。",
    "# 它不含节点：节点由你自己的订阅提供，地区组会按节点名自动归类。",
)


def extract_block(text: str, start_marker: str, end_marker: str | None) -> str:
    """按顶层键名切出一整段（含其后的缩进行）。"""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.rstrip() == start_marker:
            start = index
            break
    if start is None:
        raise BuildError(f"规则源里找不到 {start_marker} 段")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line and not line[0].isspace() and not line.lstrip().startswith("#"):
            if end_marker is None or line.rstrip() == end_marker:
                end = index
                break
    return "\n".join(lines[start:end]).rstrip("\n")


def rename_targets(block: str) -> str:
    """把 block 里的策略名换成手机端统一叫法。"""
    for old, new in TARGET_RENAME.items():
        # rules 段：行尾的 `,Proxies`
        block = re.sub(rf",{re.escape(old)}$", f",{new}", block, flags=re.MULTILINE)
        # rule-providers 段：`    proxy: Proxies`
        block = re.sub(rf"^(\s*proxy:\s*){re.escape(old)}$", rf"\g<1>{new}", block, flags=re.MULTILINE)
    return block


def render_groups() -> list[str]:
    lines = ["proxy-groups:"]
    for name, proxies in GROUP_ORDER:
        lines.append(f"  - name: {name}")
        lines.append("    type: select")
        if proxies is None:
            # 地区组 / 通用代理组：自动收节点
            lines.append("    include-all: true")
            if name in REGION_FILTERS:
                lines.append(f'    filter: "{REGION_FILTERS[name]}"')
            lines.append("    proxies:")
            lines.append("      - DIRECT")
        else:
            lines.append("    proxies:")
            for proxy in proxies:
                lines.append(f"      - {proxy}")
    return lines


def build_document(merge_text: str, extra_groups: dict) -> str:
    providers = rename_targets(extract_block(merge_text, "rule-providers:", "rules:"))
    rules = rename_targets(extract_block(merge_text, "rules:", None))

    # 交易所是手机端独有的分组（PC 版没有这块业务），规则来自 extra-rules.json
    exchange = extra_groups.get("Exchange")
    if not exchange:
        raise BuildError("extra-rules.json 里没有 Exchange 组")
    exchange_lines = [
        f"  - {rule_type},{value},Exchange" for rule_type, value in exchange["rules"]
    ]

    # 插到兜底之前，别让 MATCH 把它们吃掉
    head, _, tail = rules.rpartition("  # 最终兜底")
    if not head:
        raise BuildError("规则源里找不到兜底注释，插交易所规则的位置不确定")
    rules = (
        head.rstrip("\n")
        + "\n  # 交易所（手机端独有分组）\n"
        + "\n".join(exchange_lines)
        + "\n"
        + "  # 最终兜底"
        + tail
    )

    body = [
        *HEADER,
        f"# Source: {SOURCE_REPO} {{version}}",
        "",
        *render_groups(),
        "",
        providers,
        "",
        rules,
        "",
    ]
    return "\n".join(body)


def summarize(document: str) -> str:
    groups = len(re.findall(r"^  - name: ", document, re.MULTILINE))
    providers = len(re.findall(r"^  [a-z0-9-]+:$", document, re.MULTILINE))
    rules = len(re.findall(r"^  - ", document, re.MULTILINE)) - groups
    return f"  策略组 {groups} 个 / 规则集 {providers} 个 / 规则约 {rules} 条"


def main(argv: list[str]) -> int:
    try:
        source, out_dir = parse_args(argv)
        merge_text = read_source(source)
        version = fetch_source_version(source)
        document = build_document(merge_text, load_extra_rules())
    except BuildError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1

    document = document.replace("{version}", version or "unknown")
    output = out_dir / OUTPUT_SUFFIX
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")

    print(f"规则源: {describe_source(source)}")
    print(summarize(document))
    print(f"已写入: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
