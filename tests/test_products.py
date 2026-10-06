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
import subprocess
import unittest
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_REPO = "reroc8/mobile-proxy-share-kit"

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

# Shadowrocket 自己的组顺序。它比另外两份多出 HK / CN / Banks / Brokers ——
# 小火箭有 policy-regex-filter 这种别家没有的能力，按能力做足，不强行三份同构。
# （HK 只在 [Proxy Group] 里，[Rule] 段不出现，所以不在这张表里。）
SHADOWROCKET_ORDER = (
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

# Shadowrocket 侧的宽泛策略：CN（国内，默认直连，可切）和 Proxy（兜底走代理）
SHADOWROCKET_BROAD = ("CN", "Proxy")

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


# Shadowrocket 用到的全部策略名（HK 只在 [Proxy Group] 里，不在 [Rule] 段）
SHADOWROCKET_POLICIES = set(SHADOWROCKET_ORDER) | {"HK"}


def parse_shadowrocket(path: Path) -> dict[str, list[tuple[str, str, str]]]:
    """把 .conf 按 `# 策略名` 注释切段，返回 {策略名: [(类型, 值, 目标)]}。"""
    sections: dict[str, list[tuple[str, str, str]]] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            marker = line.lstrip("#").strip()
            current = marker if marker in SHADOWROCKET_POLICIES else None
            if current:
                sections[current] = []
            continue
        if not line or current is None:
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 3 and parts[0].startswith(("DOMAIN", "IP-CIDR", "RULE-SET")):
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
                list(SHADOWROCKET_ORDER),
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
        checks = {
            "Karing": (
                [to_policy[group["name"]] for group in load_karing()["rules"]],
                BROAD_POLICIES,
            ),
            "Shadowrocket": (list(parse_shadowrocket(SHADOWROCKET_FILES[1])), SHADOWROCKET_BROAD),
        }
        for product, (ordering, broad) in checks.items():
            broad_start = min(ordering.index(policy) for policy in broad)
            for policy in ordering:
                if policy in broad:
                    continue
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

    def test_hand_written_groups_stay_in_sync(self) -> None:
        """Claude 和 AI 是两个产物都**手写**的组，内容必须逐条一致。

        其余组小火箭侧改用了远程规则集（Google / YouTube / Telegram / Exchange），
        内容在别人仓库里，没法逐条比对，只能比组名 —— 那个由顺序测试覆盖。
        """
        name_of = {policy: name for name, policy in EXPECTED_ORDER}
        karing = karing_domains(load_karing())
        shadowrocket = parse_shadowrocket(SHADOWROCKET_FILES[1])
        for policy in ("Claude", "AI"):
            sr_domains = {
                value.lstrip(".") for kind, value, _ in shadowrocket[policy] if kind.startswith("DOMAIN")
            }
            missing = sorted(karing[name_of[policy]] - sr_domains)
            self.assertEqual(missing, [], f"{policy} 组：Karing 有而小火箭没有的域名 {missing}")

    def test_every_shadowrocket_section_has_rules(self) -> None:
        """有的段手写域名，有的段引用远程规则集 —— 两者必须有其一，不能空着。"""
        sections = parse_shadowrocket(SHADOWROCKET_FILES[1])
        for name, rules in sections.items():
            covered = any(
                rule[0].startswith("DOMAIN") or rule[0] in ("RULE-SET",) or rule[0].startswith("IP-CIDR")
                for rule in rules
            )
            self.assertTrue(covered, f"{name} 段里既没有域名规则也没有规则集")

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
        "clash/README.md": r"当前版本：`(v\d+\.\d+\.\d+)`",
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


def load_script(filename: str):
    """scripts/ 下的文件名带连字符，不能直接 import，用 importlib 载入。"""
    import importlib.util

    path = REPO_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_bump_tool():
    return load_script("bump-version.py")


class TestVersionsTrackRuleChanges(unittest.TestCase):
    """每个版本号都必须对应一次真实的规则内容变化。

    v0.3.2 ~ v0.3.5 曾连发四个规则内容零变化的版本（版本号已撤销），
    从这个边界之后的版本开始强制。所以这条断言现在会通过，但下次谁再发一个
    「只改了脚本和文档」的版本，它就会红。
    """

    GUARD_FROM = "v0.2.0"

    @classmethod
    def setUpClass(cls) -> None:
        cls.tool = load_bump_tool()
        result = subprocess.run(
            ["git", "tag"], cwd=REPO_ROOT, capture_output=True, text=True
        )
        cls.tags = result.stdout.split() if result.returncode == 0 else []

    @staticmethod
    def key(tag: str) -> tuple[int, ...]:
        return tuple(int(part) for part in tag.lstrip("v").split("."))

    def fingerprint_at(self, tag: str) -> str | None:
        return self.tool.fingerprint(lambda rel: self.tool.read_git(tag, rel))

    def test_consecutive_releases_change_rules(self) -> None:
        if not self.tags:
            self.skipTest("拿不到 git tag（浅克隆？），跳过")

        guarded = sorted(
            (tag for tag in self.tags if self.key(tag) >= self.key(self.GUARD_FROM)),
            key=self.key,
        )
        self.assertTrue(guarded, f"没有 {self.GUARD_FROM} 之后的 tag")

        for older, newer in zip(guarded, guarded[1:]):
            before, after = self.fingerprint_at(older), self.fingerprint_at(newer)
            self.assertNotEqual(
                before,
                after,
                f"{newer} 与 {older} 的规则内容完全相同 —— 版本号只该为规则变更而涨，"
                "工程改动走普通提交即可",
            )


class TestDocumentLinks(unittest.TestCase):
    """文档里的仓库内链接必须指向真实存在的文件。

    这类失效最不容易被发现：改目录结构、改文件名、删兼容文件，文档照旧写着旧路径，
    读者点开才发现 404。所以把文档当代码一样测。
    """

    DOCUMENTS = (
        "README.md",
        "karing/README.md",
        "shadowrocket/README.md",
        "docs/index.html",
        "docs/import.html",
        "clash/README.md",
    )

    HTML_PAGES = ("docs/index.html", "docs/import.html")

    def read(self, relative: str) -> str:
        return (REPO_ROOT / relative).read_text(encoding="utf-8")

    def test_raw_githubusercontent_links_resolve(self) -> None:
        prefix = f"raw.githubusercontent.com/{SOURCE_REPO}/main/"
        pattern = re.compile(re.escape(prefix) + r"([^\s)`\"<>]+)")
        checked = 0
        for relative in self.DOCUMENTS:
            for path in pattern.findall(self.read(relative)):
                self.assertTrue(
                    (REPO_ROOT / path).is_file(),
                    f"{relative} 指向 {path}，但仓库里没有这个文件",
                )
                checked += 1
        self.assertGreater(checked, 0, "一个 raw 链接都没找到，检查是不是正则失效了")

    def test_page_local_links_resolve(self) -> None:
        checked = 0
        for relative in self.HTML_PAGES:
            html = self.read(relative)
            targets = [
                target
                for target in re.findall(r'href="([^"#:][^"]*)"', html)
                + re.findall(r'src="([^"]+)"', html)
                if "://" not in target  # 外链与自定义 scheme 各自另有断言
            ]
            self.assertGreater(len(targets), 0, f"{relative} 里一个本地引用都没找到")
            for target in targets:
                self.assertTrue(
                    (REPO_ROOT / "docs" / target).is_file(),
                    f"{relative} 引用 {target}，但 docs/{target} 不存在",
                )
                checked += 1
        self.assertGreater(checked, 0)

    def test_pages_links_resolve_under_docs(self) -> None:
        """GitHub Pages 的源是 docs/，所以站点路径对应 docs/ 下的文件。"""
        prefix = f"{SOURCE_REPO.split('/')[0]}.github.io/{SOURCE_REPO.split('/')[1]}/"
        pattern = re.compile(re.escape(prefix) + r"([^\s)`\"<>]*)")
        checked = 0
        for relative in self.DOCUMENTS:
            for path in pattern.findall(self.read(relative)):
                path = path.rstrip("/")
                target = REPO_ROOT / "docs" / (path or "index.html")
                self.assertTrue(
                    target.is_file(), f"{relative} 指向站点路径 /{path}，但 docs/{path} 不存在"
                )
                checked += 1
        self.assertGreater(checked, 0, "一个 Pages 链接都没找到")


    def test_shadowrocket_one_tap_link_present(self) -> None:
        """两个页面都要保留小火箭的一键导入入口，且指向完整骨架模板。

        Shadowrocket 的 scheme 由社区维护的官方群组关键词文件给出：
        `shadowrocket://config/add/{url}` = 安装/使用配置。
        """
        for relative in self.HTML_PAGES:
            html = self.read(relative)
            match = re.search(r'href="shadowrocket://config/add/([^"]+)"', html)
            self.assertIsNotNone(match, f"{relative} 里没有小火箭一键导入按钮")
            self.assertTrue(
                match.group(1).endswith("shadowrocket/Shadowrocket.full.conf"),
                f"{relative} 的一键导入应指向完整骨架模板，实际是 {match.group(1)}",
            )

    def test_phone_import_page_offers_both_clients(self) -> None:
        """手机操作页要同时给两个客户端入口 —— 扫码的人不一定用小火箭。"""
        html = self.read("docs/import.html")
        self.assertIn("shadowrocket://config/add/", html)
        self.assertIn('href="karing/karing-diversion-rules.json"', html)


class TestQrCodes(unittest.TestCase):
    """二维码内容错了，要等用户扫了才发现，而且多数人不会反馈。所以直接解码回读。

    预期内容取自 scripts/make-qr.py（唯一来源），不在这里另抄一份。
    opencv 不是运行时依赖，没装就跳过 —— CI 里不装它。
    """

    @classmethod
    def setUpClass(cls) -> None:
        try:
            import cv2
        except ImportError:
            raise unittest.SkipTest("没有 opencv，跳过二维码解码校验")
        cls.cv2 = cv2
        cls.detector = cv2.QRCodeDetector()
        cls.qrcodes = load_script("make-qr.py").QRCODES

    def test_payloads_match_the_generator(self) -> None:
        self.assertTrue(self.qrcodes, "make-qr.py 里没有定义任何二维码")
        for relative, payload, _ in self.qrcodes:
            path = REPO_ROOT / relative
            self.assertTrue(path.is_file(), f"缺少 {relative}，跑一下 scripts/make-qr.py")
            decoded, _, _ = self.detector.detectAndDecode(self.cv2.imread(str(path)))
            self.assertEqual(decoded, payload, f"{relative} 的实际内容和声明不一致")

    def test_shadowrocket_qr_uses_the_app_scheme(self) -> None:
        """小火箭那张必须是 shadowrocket://config/add/... —— 系统相机扫不了它，
        只能用 App 内扫码，页面文案也要照此写。"""
        payloads = {rel: payload for rel, payload, _ in self.qrcodes}
        payload = payloads["docs/assets/shadowrocket-config-qr.png"]
        self.assertTrue(payload.startswith("shadowrocket://config/add/https://"))
        self.assertTrue(payload.endswith("shadowrocket/Shadowrocket.full.conf"))


class TestShadowrocketFallback(unittest.TestCase):
    """小火箭的兜底必须走代理，不能照抄 PC 版的 MATCH,DIRECT。

    PC 版前面有 global-domain 规则集兜住海外域名，最后那条 MATCH 只兜极小一部分；
    手机端没有那个规则集，同样的兜底会变成「没列出的墙外站全走直连、打不开」
    —— Wikipedia / IMDb / Bloomberg 这类全部中招。宁可国内小众站稍慢。
    """

    def test_fallback_goes_through_proxy(self) -> None:
        for path in SHADOWROCKET_FILES:
            rules = [
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#") and not line.startswith("[")
            ]
            finals = [line for line in rules if line.startswith("FINAL,")]
            self.assertEqual(finals, ["FINAL,Proxy"], f"{path.name} 的兜底策略不是走代理")
            self.assertIn("GEOIP,CN,CN", rules, f"{path.name} 少了国内 IP 规则")


class TestRemoteRuleSets(unittest.TestCase):
    """Google / YouTube / Telegram / Exchange 四个组改用远程规则集。

    URL 拼错的话小火箭那一行会**静默失效**（不报错，只是不命中），用户不会知道。
    所以生成出来就得验证它真拉得到、内容确实是规则集。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.rule_sets = load_script("build-shadowrocket-rules.py").RULE_SETS

    def test_exactly_the_big_services_use_rule_sets(self) -> None:
        self.assertEqual(
            set(self.rule_sets),
            {"Google", "YouTube", "Telegram", "Exchange", "Banks", "Brokers"},
            "改用/新增规则集的组要先想清楚 —— 手写能追上的就没必要引外部依赖",
        )

    def test_claude_and_ai_stay_hand_written(self) -> None:
        """这两块是我们自己的价值：Claude.list 只有 10 行、OpenAI+Gemini 66 行，
        都不如我们手写全。换成规则集是倒退。"""
        for policy in ("Claude", "AI"):
            self.assertNotIn(policy, self.rule_sets)

    def test_rule_sets_are_reachable_and_look_like_rule_sets(self) -> None:
        for policy, urls in self.rule_sets.items():
            for url in urls:
                try:
                    with urllib.request.urlopen(url, timeout=15) as response:
                        body = response.read().decode("utf-8", "replace")
                except Exception as error:  # noqa: BLE001
                    self.skipTest(f"网络不可用，跳过规则集校验：{error}")
                self.assertIn("DOMAIN", body, f"{url} 拉回来的内容不像规则集")
                self.assertGreater(len(body.splitlines()), 5, f"{url} 内容过短")


class TestShadowrocketOverlay(unittest.TestCase):
    """叠加片段是给「已经有完整机场配置」的人用的，必须只叠加、不接管。

    机场那份配置自带节点、DNS 设置和几千条通用规则。用我们的整份配置替换会把这些全丢掉，
    所以这份片段：不含 [General]（别覆盖人家的 DNS/隧道设置）、不含局域网段和兜底
    （人家本来就有）、不含任何节点。
    """

    PATH = REPO_ROOT / "shadowrocket" / "Shadowrocket.overlay.conf"

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = cls.PATH.read_text(encoding="utf-8")
        cls.rules = [
            line.strip()
            for line in cls.text.splitlines()
            if line.strip() and not line.startswith("#") and not line.startswith("[")
        ]

    def test_does_not_clobber_existing_general_settings(self) -> None:
        self.assertNotIn("[General]", self.text, "叠加片段不能带 [General]，会覆盖机场的 DNS/隧道设置")

    def test_leaves_fallback_to_the_existing_config(self) -> None:
        joined = " ".join(self.rules)
        for marker in ("FINAL,", "GEOIP,CN,CN"):
            self.assertNotIn(
                marker,
                joined,
                f"叠加片段不该自己带兜底（{marker}），用户配置里已经有了",
            )

    def test_still_carries_groups_and_rules(self) -> None:
        self.assertIn("[Proxy Group]", self.text)
        self.assertGreater(len(self.rules), 100, "叠加片段里规则太少，检查生成逻辑")
        self.assertIn("DOMAIN-SUFFIX,claude.ai,Claude", self.rules)

    def test_contains_no_proxy_nodes(self) -> None:
        """片段只带策略组和规则，节点由用户自己的订阅/机场配置提供。"""
        self.assertNotIn("[Proxy]", self.text)
        self.assertNotIn("trojan", self.text)


class TestClashProduct(unittest.TestCase):
    """Clash 覆写产物：与另外两份同源、同组名、同规则目标。

    这份产物不做格式转换（PC 的 Merge.yaml 本身就是 Clash 语法），
    只补 proxy-groups 并把 `Proxies` 改名成 `Proxy`，所以重点验"搬对了没有"。
    """

    PATH = REPO_ROOT / "clash" / "clash-override.yaml"
    BUILT_IN = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"}
    NO_PROXY_SUFFIX = ("no-resolve", "src")

    @classmethod
    def setUpClass(cls) -> None:
        try:
            import yaml
        except ImportError:
            raise unittest.SkipTest("没有 pyyaml，跳过 Clash 产物校验")
        cls.yaml = yaml
        cls.doc = yaml.safe_load(cls.PATH.read_text(encoding="utf-8"))

    def group_names(self) -> list[str]:
        return [group["name"] for group in self.doc["proxy-groups"]]

    def targets(self) -> list[str]:
        out = []
        for rule in self.doc["rules"]:
            fields = [field.strip() for field in rule.split(",")]
            while len(fields) > 1 and fields[-1] in self.NO_PROXY_SUFFIX:
                fields.pop()
            out.append(fields[-1])
        return out

    def test_group_names_and_order_match_other_products(self) -> None:
        """DIRECT 是 Clash 内置，不在这里定义，其余必须一一对应。"""
        expected = [policy for _, policy in EXPECTED_ORDER if policy != "DIRECT"]
        self.assertEqual(self.group_names(), expected)

    def test_every_rule_targets_a_known_group(self) -> None:
        known = set(self.group_names()) | self.BUILT_IN
        for rule, target in zip(self.doc["rules"], self.targets()):
            self.assertIn(target, known, f"规则指向了不存在的策略组: {rule}")

    def test_no_leftover_pc_policy_name(self) -> None:
        self.assertNotIn("Proxies", self.PATH.read_text(encoding="utf-8"))

    def test_has_match_fallback_to_direct(self) -> None:
        self.assertEqual(self.doc["rules"][-1], "MATCH,DIRECT")

    def test_must_proxy_domain_still_goes_to_proxy(self) -> None:
        self.assertIn("DOMAIN-SUFFIX,tgalileo.com,Proxy", self.doc["rules"])

    def test_exchange_group_is_populated(self) -> None:
        """交易所是手机端独有分组，PC 的规则里没有，靠 extra-rules.json 补。"""
        exchange = [rule for rule, target in zip(self.doc["rules"], self.targets()) if target == "Exchange"]
        self.assertTrue(exchange, "没有任何规则指向 Exchange 组")

    def test_region_groups_can_never_be_empty(self) -> None:
        """mihomo 不允许策略组一个候选都没有，否则整个配置加载失败。"""
        for group in self.doc["proxy-groups"]:
            if "include-all" in group:
                self.assertIn("proxies", group, f"{group['name']} 只有 include-all，没放兜底候选")
                self.assertTrue(group["proxies"], f"{group['name']} 的兜底候选是空的")

    def test_source_stamp_present(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        self.assertIsNotNone(
            re.search(r"^# Source: reroc8/clash-verge-share-kit v\d+\.\d+\.\d+$", text, re.MULTILINE),
            "Clash 产物头部没有标 PC 源版本",
        )


if __name__ == "__main__":
    unittest.main()
