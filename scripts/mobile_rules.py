#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两个手机端生成脚本共用的部分。

规则源、rules 段解析、补充分组、参数解析都放在这里，Karing 和 Shadowrocket
两个脚本只保留各自「怎么把规则写成目标格式」的差异。

抽出来的理由很实际：两份产物必须同构，逻辑各写一遍早晚会改一边忘一边 ——
v0.3.0 之前 Shadowrocket 落后 PC 93 条，就是这么来的。
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 规则源 = PC 版仓库的 GitHub 源码，不是本机某份副本。
# 这样产物可以在任何机器上复现，不再依赖 ~/Desktop 下的本地路径，
# 也不会因为本地文件没提交就和真源不一致。
SOURCE_URL = (
    "https://raw.githubusercontent.com/reroc8/clash-verge-share-kit/main/config/Merge.yaml"
)

EXTRA_RULES_PATH = REPO_ROOT / "scripts" / "extra-rules.json"

DOMAIN_TYPES = ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD")


class BuildError(Exception):
    """规则源有问题、或者映射表没登记的情况，一律报错而不是猜。"""


def read_source(source: str) -> str:
    """读取规则源。支持 http(s) URL 和本地文件路径（离线或调试时用）。"""
    if source.startswith(("http://", "https://")):
        try:
            with urllib.request.urlopen(source, timeout=30) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise BuildError(f"拉取规则源失败 {source}\n  {error}") from error

    path = Path(source).expanduser()
    if not path.is_file():
        raise BuildError(f"找不到规则源 {path}")
    return path.read_text(encoding="utf-8")


def parse_merge_rules(source: str) -> list[tuple[str, str, str]]:
    """解析 PC 版 Merge.yaml 的顶层 rules: 段，返回 (类型, 值, 目标) 列表。

    刻意不引 PyYAML：这份文件里我们只用得到 rules 段的扁平结构，手写解析
    少一个依赖，也不会因为文件别处改动而失败。
    """
    lines = read_source(source).splitlines()

    start = None
    for index, line in enumerate(lines):
        if line.rstrip() == "rules:":
            start = index
            break
    if start is None:
        raise BuildError(f"规则源里找不到顶层 rules: 段（{source}）")

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

    if not entries:
        raise BuildError(f"规则源里 rules: 段是空的（{source}）")
    return entries


def load_extra_rules() -> dict:
    """读取 PC 没有、手机端自己补充的分组定义。两个生成脚本共用这一份。"""
    if not EXTRA_RULES_PATH.is_file():
        raise BuildError(f"缺少 {EXTRA_RULES_PATH.relative_to(REPO_ROOT)}")
    data = json.loads(EXTRA_RULES_PATH.read_text(encoding="utf-8"))
    groups = data.get("groups")
    if not isinstance(groups, dict):
        raise BuildError(f"{EXTRA_RULES_PATH.name} 里缺少 groups 段")
    return groups


def parse_args(argv: list[str]) -> tuple[str, Path]:
    """返回 (规则源, 输出根目录)。

    规则源默认走 GitHub 源码；传路径或 URL 可覆盖，离线时指本机副本即可。
    --out-dir 供 scripts/check-drift.sh 生成到临时目录做比对。
    """
    source = SOURCE_URL
    out_dir = REPO_ROOT
    rest = list(argv[1:])
    while rest:
        arg = rest.pop(0)
        if arg == "--out-dir":
            if not rest:
                raise BuildError("--out-dir 后面要跟目录")
            out_dir = Path(rest.pop(0)).expanduser()
        elif arg.startswith("--out-dir="):
            out_dir = Path(arg.split("=", 1)[1]).expanduser()
        else:
            source = arg
    return source, out_dir


def describe_source(source: str) -> str:
    """打印用：URL 原样显示，本地路径转成 ~ 开头更短。"""
    if source.startswith(("http://", "https://")):
        return source
    return str(Path(source).expanduser())
