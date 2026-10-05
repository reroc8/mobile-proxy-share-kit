#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把仓库里所有位置的项目版本号统一改到指定版本。

版本号散在 4 个文件里（VERSION.txt、README.md、karing/README.md、shadowrocket/README.md，
再加上 CHANGELOG.md 的条目标题）。手工改漏一个就会出现「README 说 v0.3.3、
VERSION.txt 说 v0.3.4」这种不一致 —— 已经漏过一次。所以改成一命令改全部，
并用 tests/test_products.py 钉住一致性。

用法：
    python3 scripts/bump-version.py v0.3.5

CHANGELOG.md 不自动生成 —— 变更说明得人写。脚本只检查该版本标题是否已存在，
没有就报错，避免出现「版本号改了但 CHANGELOG 没写」。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")
CURRENT_PATTERN = re.compile(r"v\d+\.\d+\.\d+")

# 需要跟着版本号走的文件，以及各自「版本号该长什么样」的正则
TARGETS = (
    (Path("README.md"), re.compile(r"(当前 )`v\d+\.\d+\.\d+`"), r"\g<1>`{new}`"),
    (Path("karing/README.md"), re.compile(r"(当前版本：)`v\d+\.\d+\.\d+`"), r"\g<1>`{new}`"),
    (Path("shadowrocket/README.md"), re.compile(r"(当前版本：)`v\d+\.\d+\.\d+`"), r"\g<1>`{new}`"),
)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not VERSION_PATTERN.match(argv[1]):
        print("用法: python3 scripts/bump-version.py vX.Y.Z", file=sys.stderr)
        return 1

    new_version = argv[1]
    version_file = REPO_ROOT / "VERSION.txt"
    old_version = version_file.read_text(encoding="utf-8").strip()

    if new_version == old_version:
        print(f"当前已经是 {new_version}，无需改动。")
        return 0

    # CHANGELOG 必须先有人写好条目，否则不允许改版本号
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8")
    if f"## {new_version}" not in changelog:
        print(
            f"错误: CHANGELOG.md 里还没有 `## {new_version}` 条目。\n"
            "先写好该版本的变更说明，再跑这个脚本。",
            file=sys.stderr,
        )
        return 1

    changed = []
    version_file.write_text(new_version + "\n", encoding="utf-8")
    changed.append("VERSION.txt")

    for relative, pattern, replacement in TARGETS:
        path = REPO_ROOT / relative
        original = path.read_text(encoding="utf-8")
        updated, count = pattern.subn(replacement.format(new=new_version), original)
        if count == 0:
            print(f"错误: {relative} 里找不到该改的版本号写法，检查文件是否被改过", file=sys.stderr)
            return 1
        path.write_text(updated, encoding="utf-8")
        changed.append(f"{relative}（{count} 处）")

    print(f"{old_version} -> {new_version}")
    for item in changed:
        print(f"  已更新: {item}")
    print("\n接下来：")
    print("  bash scripts/check-drift.sh --fix              # 产物头部会带上 PC 源版本")
    print("  python3 -m unittest discover -s tests -v       # 确认版本号处处一致")
    print("  bash scripts/build-release.command             # 出包")
    print("  bash scripts/publish-release.sh                # 打 tag + 发 GitHub Release")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
