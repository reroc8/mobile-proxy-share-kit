#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把仓库里所有位置的项目版本号统一改到指定版本。

**版本号的语义：它表示「用户拿到的产物」的版本。**

产物内容 = 域名、分组、顺序，以及**覆盖的客户端范围**。改了这些才发新版本。
测试、CI、脚本、文档这类工程改动走普通提交，不占版本号 —— 之前没这条规矩，
连续发了 v0.3.2 / v0.3.3 / v0.3.4 / v0.3.5 四个产物内容零变化的版本，
版本号看着在涨，其实什么都没变。

脚本会拿当前版本的产物和上一版比；规则内容完全相同就直接拒绝，
避免再出现「版本号涨了但规则没动」。

用法：
    python3 scripts/bump-version.py v0.3.6
    python3 scripts/bump-version.py v0.3.6 --force   # 明知规则没变也要发

CHANGELOG.md 不自动生成 —— 变更说明得人写。脚本只检查该版本标题是否已存在，
没有就报错，避免出现「版本号改了但 CHANGELOG 没写」。
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")

# 需要跟着版本号走的文件，以及各自「版本号该长什么样」的正则
TARGETS = (
    (Path("README.md"), re.compile(r"(当前 )`v\d+\.\d+\.\d+`"), r"\g<1>`{new}`"),
    (Path("karing/README.md"), re.compile(r"(当前版本：)`v\d+\.\d+\.\d+`"), r"\g<1>`{new}`"),
    (Path("shadowrocket/README.md"), re.compile(r"(当前版本：)`v\d+\.\d+\.\d+`"), r"\g<1>`{new}`"),
    (Path("clash/README.md"), re.compile(r"(当前版本：)`v\d+\.\d+\.\d+`"), r"\g<1>`{new}`"),
)

# 参与「规则内容」指纹的产物。归一化时去掉注释和空行 ——
# .conf 头部的 `# Source:` 行会随 PC 发版变化，但那不是规则内容变了。
# 用 full.conf 而不是 rules.conf —— 后者**不含 [Proxy Group] 段**，
# 于是"只改了策略组（比如地区正则）"这种变化会被指纹漏掉，护栏就会放过一个真改动。
# 这个盲区实际踩到过：修 SG 组误收节点的版本被误判成"与上一版完全相同"。
ARTIFACTS = (
    ("shadowrocket/星君分流.conf", "conf"),
    ("karing/karing-diversion-rules.json", "json"),
    ("clash/clash-override.yaml", "conf"),
    ("hiddify/hiddify-route-rules.json", "json"),
)


def normalize(text: str, kind: str) -> str:
    if kind == "conf":
        return "\n".join(
            line for line in text.splitlines() if line.strip() and not line.startswith("#")
        )
    document = json.loads(text)
    return json.dumps(document, ensure_ascii=False, sort_keys=True)


def fingerprint(read: "callable") -> str:
    """read(relative_path) -> 文本或 None。

    「取不到」也要编进哈希：某个版本还没有这份产物，本身就是与有它的版本之间的差别。
    早先的做法是取不到就返回 None 跳过检查，那会让「新增产物」这种变化被漏掉。
    """
    parts = []
    for relative, kind in ARTIFACTS:
        text = read(relative)
        marker = "MISSING" if text is None else normalize(text, kind)
        parts.append(f"{relative}:{marker}")
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def read_worktree(relative: str) -> str | None:
    path = REPO_ROOT / relative
    return path.read_text(encoding="utf-8") if path.is_file() else None


def read_git(ref: str, relative: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{relative}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else None


def tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main(argv: list[str]) -> int:
    force = "--force" in argv[1:]
    args = [arg for arg in argv[1:] if arg != "--force"]

    if len(args) != 1 or not VERSION_PATTERN.match(args[0]):
        print(
            "用法: python3 scripts/bump-version.py vX.Y.Z [--force]",
            file=sys.stderr,
        )
        return 1

    new_version = args[0]
    version_file = REPO_ROOT / "VERSION.txt"
    old_version = version_file.read_text(encoding="utf-8").strip()

    if new_version == old_version:
        print(f"当前已经是 {new_version}，无需改动。")
        return 0

    # CHANGELOG 必须先有人写好条目，否则不允许改版本号
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    if f"## {new_version}" not in changelog_path.read_text(encoding="utf-8"):
        print(
            f"错误: CHANGELOG.md 里还没有 `## {new_version}` 条目。\n"
            "先写好该版本的变更说明，再跑这个脚本。",
            file=sys.stderr,
        )
        return 1

    # 规则内容没变就不该发新版
    if not force:
        if not tag_exists(old_version):
            print(f"提示: {old_version} 还没有 tag，跳过规则内容比对。")
        else:
            before = fingerprint(lambda rel: read_git(old_version, rel))
            after = fingerprint(read_worktree)
            if before == after:
                print(
                    f"错误: 产物内容与 {old_version} 完全相同，不该发新版本。\n"
                    "版本号只表示产物（域名/分组/顺序/覆盖的客户端）的版本，\n"
                    "测试、CI、脚本、文档之类的工程改动走普通提交即可。确实需要发就用 --force。",
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
