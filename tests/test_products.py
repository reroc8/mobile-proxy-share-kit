#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对仓库里两份产物做约束检查。

和 scripts/check-drift.sh 的分工：
  check-drift  —— 产物是否等于「用 PC 源码重新生成的结果」（内容新鲜度）
  本文件       —— 产物本身是否符合我们定的规则（结构正确性）

所以这里全程离线、只读仓库里的文件，不联网、不调生成脚本。

跑法：
  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

KARING_FILE = REPO_ROOT / "karing" / "karing-diversion-rules.json"
SHADOWROCKET_FILES = (
    REPO_ROOT / "shadowrocket" / "Shadowrocket.rules.conf",
    REPO_ROOT / "shadowrocket" / "Shadowrocket.conf",
    REPO_ROOT / "shadowrocket" / "Shadowrocket.full.conf",
)

# 两个产物必须一致的组顺序。这是「契约」本身：
# 精确规则在前、宽泛规则在后（PC 里 tgalileo.com 同时在 cn 域名库中，
# 靠精确前置才能改走代理），YouTube 又在 Google 之前
# （否则 youtubei.googleapis.com 被 googleapis.com 抢走）。
EXPECTED_ORDER = (
    ("🤖 Claude", "Claude"),
    ("🧠 国际 AI", "AI"),
    ("🎬 YouTube", "YouTube"),
    ("🌐 Google", "Google"),
    ("💱 交易所", "Exchange"),
    ("✈️ Telegram", "Telegram"),
    ("🇺🇸 美国", "US"),
    ("🇸🇬 新加坡", "SG"),
    ("🏠 国内直连", "DIRECT"),
    ("🚀 代理", "Proxy"),
)

# 「宽泛」策略：必须排在所有精确策略之后
BROAD_POLICIES = ("DIRECT", "Proxy")

# Karing 内置规则集白名单。名字写错不会报错、只会静默不匹配，所以在这里钉死。
# 来源：KaringX/karing 仓库 assets/datas/preset/{default,cn}.json 的实测值。
KNOWN_BUILD_IN_PREFIXES = ("geosite:", "geoip:", "acl:")
KNOWN_BUILD_IN = {
    "acl:Claude",
    "acl:Gemini",
    "geosite:openai",
    "geoip:openai",
    "geosite:google",
    "geosite:telegram",
    "geoip:telegram",
    "acl:ChinaDomain",
    "acl:ChinaIp",
    "geosite:geolocation-!cn",
}

# 必须走代理、不能进国内直连的域名（PC 里明确改道的那几个）
MUST_PROXY = ("tgalileo.com",)
# 必须走对应地区组的域名
MUST_REGION = {
    "mail.com": "🇺🇸 美国",
    "lexmount.com": "🇺🇸 美国",
    "muse.meta.com": "🇺🇸 美国",
    "dola.com": "🇸🇬 新加坡",
}


def load_karing() -> dict:
    return json.loads(KARING_FILE.read_text(encoding="utf-8"))


def parse_shadowrocket(path: Path) -> dict[str, list[tuple[str, str, str]]]:
    """把 .conf 按 `# 策略名` 注释切段，返回 {策略名: [(类型, 值, 目标)]}。"""
    sections: dict[str, list[tuple[str, str, str]]] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            marker = line.lstrip("#").strip()
            current = marker if marker in {name for _, name in EXPECTED_ORDER} else None
            if current:
                sections[current] = []
            continue
        if not line or current is None:
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 3 and parts[0].startswith(("DOMAIN", "IP-CIDR")):
            sections[current].append((parts[0], parts[1], parts[2]))
    return sections


def karing_domains(document: dict) -> dict[str, set[str]]:
    """{组名: {域名（不带前导点）}}"""
    result = {}
    for group in document["rules"]:
        values = set()
        for key in ("domain_suffix", "domain", "domain_keyword"):
            for value in group.get(key, []):
                values.add(value.lstrip("."))
        result[group["name"]] = values
    return result


def shadowrocket_domains(sections: dict[str, list[tuple[str, str, str]]]) -> set[str]:
    return {
        value.lstrip(".")
        for rules in sections.values()
        for rule_type, value, _ in rules
        if rule_type.startswith("DOMAIN")
    }


class TestOrderContract(unittest.TestCase):
    """两个产物的组顺序必须完全一致，且满足两条硬性顺序要求。"""

    def test_karing_group_order(self) -> None:
        names = [group["name"] for group in load_karing()["rules"]]
        self.assertEqual(names, [name for name, _ in EXPECTED_ORDER])

    def test_shadowrocket_group_order(self) -> None:
        for path in SHADOWROCKET_FILES[1:]:  # rules.conf 与 .conf 内容相同，查一份即可
            sections = parse_shadowrocket(path)
            self.assertEqual(
                list(sections),
                [name for _, name in EXPECTED_ORDER],
                f"{path.name} 的策略段落顺序不符合契约",
            )

    def test_youtube_before_google(self) -> None:
        """否则 youtubei.googleapis.com 会被 googleapis.com 抢走。"""
        names = [group["name"] for group in load_karing()["rules"]]
        self.assertLess(names.index("🎬 YouTube"), names.index("🌐 Google"))

        for path in SHADOWROCKET_FILES[1:]:
            names = list(parse_shadowrocket(path))
            self.assertLess(
                names.index("YouTube"), names.index("Google"), f"{path.name} 里 YouTube 不在 Google 前"
            )

    def test_exact_policies_before_broad_ones(self) -> None:
        """PC 里 tgalileo.com 同时在 cn 域名库中，靠精确规则前置才能改走代理。"""
        to_policy = {name: policy for name, policy in EXPECTED_ORDER}
        orderings = {
            "Karing": [to_policy[group["name"]] for group in load_karing()["rules"]],
            "Shadowrocket": list(parse_shadowrocket(SHADOWROCKET_FILES[1])),
        }
        exact = [policy for _, policy in EXPECTED_ORDER if policy not in BROAD_POLICIES]
        for product, ordering in orderings.items():
            broad_start = min(ordering.index(policy) for policy in BROAD_POLICIES)
            for policy in exact:
                self.assertLess(
                    ordering.index(policy),
                    broad_start,
                    f"{product}: {policy} 没有被排在宽泛策略之前",
                )


class TestKaringContent(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load_karing()
        self.domains = karing_domains(self.document)

    def test_every_group_has_rules(self) -> None:
        for group in self.document["rules"]:
            has_domain = any(
                group.get(key) for key in ("domain_suffix", "domain", "domain_keyword")
            )
            self.assertTrue(
                has_domain or group.get("rule_set_build_in"),
                f"{group['name']} 组没有任何规则",
            )

    def test_domain_suffix_values_have_leading_dot(self) -> None:
        """Karing 导出的 domain_suffix 带前导点，实测格式。"""
        offenders = [
            value
            for group in self.document["rules"]
            for value in group.get("domain_suffix", [])
            if not value.startswith(".")
        ]
        self.assertEqual(offenders, [])

    def test_no_domain_in_two_groups(self) -> None:
        seen: dict[str, str] = {}
        for name, values in self.domains.items():
            for value in values:
                self.assertNotIn(value, seen, f"{value} 同时出现在 {seen.get(value)} 和 {name}")
                seen[value] = name

    def test_build_in_names_are_known(self) -> None:
        for group in self.document["rules"]:
            for name in group.get("rule_set_build_in", []):
                self.assertTrue(
                    name.startswith(KNOWN_BUILD_IN_PREFIXES),
                    f"{name} 前缀不对",
                )
                self.assertIn(
                    name,
                    KNOWN_BUILD_IN,
                    f"{name} 不在已验证的内置规则集白名单里；名字写错会静默不匹配",
                )

    def test_group_outbound_is_valid(self) -> None:
        for group in self.document["rules"]:
            self.assertIn(group["outbound"], ("currentSelected", "direct", "block"))
            self.assertTrue(group["switch"])

    def test_must_proxy_domains_go_to_proxy(self) -> None:
        for domain in MUST_PROXY:
            self.assertIn(domain, self.domains["🚀 代理"], f"{domain} 应该走代理")
            self.assertNotIn(domain, self.domains["🏠 国内直连"], f"{domain} 不该被判成国内直连")

    def test_region_locked_domains_in_region_groups(self) -> None:
        for domain, group_name in MUST_REGION.items():
            self.assertIn(domain, self.domains[group_name], f"{domain} 应该在 {group_name}")
            self.assertNotIn(domain, self.domains["🚀 代理"], f"{domain} 不该被并进 🚀 代理")


class TestCrossProductAlignment(unittest.TestCase):
    """Karing 不该有 Shadowrocket 没有的域名 —— 两份产物必须同构。"""

    def test_karing_domains_subset_of_shadowrocket(self) -> None:
        karing = {value for values in karing_domains(load_karing()).values() for value in values}
        shadowrocket = shadowrocket_domains(parse_shadowrocket(SHADOWROCKET_FILES[1]))
        self.assertEqual(
            sorted(karing - shadowrocket),
            [],
            "Karing 里有 Shadowrocket 没有的域名，两份产物已经不同构",
        )

    def test_domain_rules_present_in_every_shadowrocket_section(self) -> None:
        sections = parse_shadowrocket(SHADOWROCKET_FILES[1])
        for name, rules in sections.items():
            domains = [rule for rule in rules if rule[0].startswith("DOMAIN")]
            self.assertTrue(domains, f"{name} 段里没有域名规则")

    def test_legacy_conf_matches_rules_conf(self) -> None:
        """Shadowrocket.conf 是旧链接兼容文件，必须与 rules.conf 逐字节相同。"""
        self.assertEqual(
            SHADOWROCKET_FILES[0].read_bytes(),
            SHADOWROCKET_FILES[1].read_bytes(),
        )


class TestSourceStamp(unittest.TestCase):
    """.conf 头部要标明对应的 PC 源版本，否则查不到产物对应 PC 的哪一版。"""

    PATTERN = re.compile(r"^# Source: reroc8/clash-verge-share-kit v\d+\.\d+\.\d+$", re.M)

    def test_every_shadowrocket_file_is_stamped(self) -> None:
        for path in SHADOWROCKET_FILES:
            self.assertRegex(path.read_text(encoding="utf-8"), self.PATTERN, path.name)

    def test_stamps_agree(self) -> None:
        stamps = {
            self.PATTERN.search(path.read_text(encoding="utf-8")).group(0)
            for path in SHADOWROCKET_FILES
        }
        self.assertEqual(len(stamps), 1, f"三份 .conf 的来源标注不一致: {stamps}")


class TestVersionConsistency(unittest.TestCase):
    """版本号散在 4 个文件里，手改漏一个就会出现「README 说 v0.3.3、VERSION.txt 说 v0.3.4」
    这种不一致 —— 已经漏过一次。改用 scripts/bump-version.py 统一改，这里钉住一致性。"""

    README_PATTERNS = {
        "README.md": r"当前 `(v\d+\.\d+\.\d+)`",
        "karing/README.md": r"当前版本：`(v\d+\.\d+\.\d+)`",
        "shadowrocket/README.md": r"当前版本：`(v\d+\.\d+\.\d+)`",
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.version = (REPO_ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()

    def test_version_format(self) -> None:
        self.assertRegex(self.version, r"^v\d+\.\d+\.\d+$")

    def test_readmes_match_version_file(self) -> None:
        for relative, pattern in self.README_PATTERNS.items():
            text = (REPO_ROOT / relative).read_text(encoding="utf-8")
            found = re.findall(pattern, text)
            self.assertTrue(found, f"{relative} 里找不到版本号写法")
            for value in found:
                self.assertEqual(value, self.version, f"{relative} 的版本号与 VERSION.txt 不一致")

    def test_changelog_top_entry_is_current(self) -> None:
        changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        headings = re.findall(r"^## (v\d+\.\d+\.\d+)$", changelog, re.M)
        self.assertTrue(headings, "CHANGELOG.md 里没有任何版本条目")
        self.assertEqual(headings[0], self.version, "CHANGELOG 最新条目不是当前版本")

    def test_changelog_entry_has_content(self) -> None:
        changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        section = changelog.split(f"## {self.version}", 1)[1].split("\n## ", 1)[0]
        self.assertTrue(
            any(line.startswith("- ") for line in section.splitlines()),
            f"CHANGELOG 的 {self.version} 条目下没有任何变更说明",
        )

    def test_release_scripts_present(self) -> None:
        for relative in ("scripts/bump-version.py", "scripts/publish-release.sh"):
            self.assertTrue((REPO_ROOT / relative).is_file(), f"缺少 {relative}")


if __name__ == "__main__":
    unittest.main()
