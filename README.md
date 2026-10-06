# Mobile Proxy Share Kit

面向手机端的代理分流规则包。当前 `v0.2.1`，只维护两份产物。

两份产物的规则内容都从 PC 版仓库 [`reroc8/clash-verge-share-kit`](https://github.com/reroc8/clash-verge-share-kit) 的 `Merge.yaml` 生成，分组结构、组顺序、规则条数都一致，不会各走各的。

这个项目只提供规则和说明，**不包含任何订阅、节点、账号、密码或 token**。使用者必须先在客户端里导入自己的订阅。

## 两份产物

| 产物 | 覆盖 | 分组数 |
|---|---|---|
| [`karing/`](karing/) | Karing（iOS / Android / Windows / macOS） | 10 |
| [`shadowrocket/`](shadowrocket/) | Shadowrocket（iOS） | 10 |

用 ClashMetaForAndroid / FlClash / Stash / Hiddify 的，建议直接改用 Karing：同样是 sing-box 内核、免费、全平台，规则也能和 PC 版共用同一套逻辑，省一份维护成本。

手机入口页：<https://reroc8.github.io/mobile-proxy-share-kit/> —— 页面上有二维码，手机扫完会打开一个**只有两个按钮**的精简页（小火箭一键导入 / Karing 下载 JSON），不用在长页面里翻找。

## 核心目标

唯一核心目标：**AI 风控稳定**。

这套规则优先保证：

- Claude 单独走一组，建议只放美国节点。
- ChatGPT / OpenAI / Gemini / Perplexity / Copilot / Cursor 等走 AI 组，建议美国优先，台湾备用。
- DeepSeek / Kimi / Moonshot 等国内 AI 直连，不混入国际 AI 风控路径。
- Gemini 先命中 AI，不会被普通 Google 规则抢走。
- Google 登录、Gmail、OAuth 走 Google。
- YouTube / googlevideo / ytimg 走 YouTube。
- 不启用广告拦截，减少登录、验证码、支付、风控接口误伤。

## 不解决什么

- 不提供节点，不替代机场订阅。
- 不保证绕过任何平台的账号地区限制。
- 不做系统级去广告。
- 不追求全网所有站点都代理，未命中规则默认直连。

## Karing 快速使用

手机入口页：

```text
https://reroc8.github.io/mobile-proxy-share-kit/
```

1. 在 Karing 里先导入自己的订阅。
2. 下载规则 JSON：

```text
https://reroc8.github.io/mobile-proxy-share-kit/karing/karing-diversion-rules.json
```

3. 「分流」→「自定义分流组」→ `⋮` →「导入」→ 选刚下载的文件。
4. 「分流规则」页打开「自定义分流组」开关，排在 `final` 之前，把 `final` 出站设为直连。
5. 建设备自己的美国自动选择组，把 `🤖 Claude` 的出站指过去。

Karing 没有开放导入分流组的 URL Scheme，做不到点一下直接进 App，只能走「下载文件 → App 内导入」。细节见 [`karing/README.md`](karing/README.md)。

## Shadowrocket 快速使用

一键导入（**只能在 iPhone / iPad 上用 Safari** 打开下面这个页面再点按钮，手机会自动跳进
Shadowrocket 下载并启用配置）：

```text
https://reroc8.github.io/mobile-proxy-share-kit/
```

按钮调用的是 `shadowrocket://config/add/{配置地址}`。电脑上、微信内置浏览器里点了不会有反应，
那就走手动步骤：

1. 在 Shadowrocket 里先导入自己的订阅。
2. 导入完整骨架模板：

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/Shadowrocket.full.conf
```

进入「配置」→ 右上角 `+` → 粘贴链接 → 下载 → 在远程文件里点它选「使用配置」→
回首页把「全局路由」改成「配置」。

3. 把自己的节点放进对应策略：
   - `Claude`：只放美国节点。
   - `AI`：美国节点优先，台湾节点备用。
   - `Exchange`：台湾、新加坡节点。
   - `US` / `SG`：地区锁定站点，分别只放美国 / 新加坡节点。
   - `Google / YouTube / Telegram / Proxy`：放你常用稳定节点。
4. 测试 Claude、ChatGPT/Gemini、Google、YouTube、交易所、国内网站。

高级用户如果已经自己建好了策略组，也可以只导入纯规则片段：

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/Shadowrocket.rules.conf
```

旧链接 `Shadowrocket.conf` 会继续保留，等同于纯规则片段，用来兼容已经保存过的二维码或书签。

> Karing 那边做不到一键导入 —— 它的官方 URL Scheme 只开放了添加订阅、恢复备份、连接控制三类，
> 没有导入分流组的入口。Karing 只能下载 JSON 后在 App 内导入。

## 文件

```text
karing/
  karing-diversion-rules.json   Karing 自定义分流组（产物，勿手改）
  README.md

shadowrocket/
  Shadowrocket.conf             旧链接兼容，内容同 rules.conf
  Shadowrocket.full.conf        完整骨架模板（多一段 [Proxy Group]）
  Shadowrocket.rules.conf       纯规则片段
  README.md

scripts/
  mobile_rules.py                   两个生成脚本的公共部分（取规则源、解析、映射检查）
  build-karing-rules.py             规则源 -> Karing JSON
  build-shadowrocket-rules.py       规则源 -> Shadowrocket .conf
  extra-rules.json                  PC 没有、手机端补充的分组（两个脚本共用）
  check-drift.sh                    检测产物是否落后于 PC 版源码
  check-sensitive.sh
  bump-version.py                   一处改齐所有位置的版本号
  build-release.command             出包（跑全部检查后打 zip）
  publish-release.sh                打 tag + 建 GitHub Release 并上传 zip

tests/
  test_products.py                  产物约束检查（组顺序、映射、内置规则集名字等，离线）

.github/workflows/
  verify.yml                        自动跑产物约束检查 + 漂移检测

docs/                           GitHub Pages 手机入口页
  index.html
  karing/karing-diversion-rules.json   Pages 同源下载副本，由脚本同步
```

## 版本号怎么算

**手机端的版本号只表示「规则内容」的版本。** 规则内容 = 域名、分组、分组顺序。

- **改了规则 → 发新版本。** 比如 PC 那边加了域名、或者手机端补了分组。
- **没改规则 → 不发版本。** 测试、CI、脚本、文档、构建流程这类工程改动，走普通 commit 就行。
  `scripts/bump-version.py` 会比对新旧两版的规则内容，完全相同就直接拒绝改版本号
  （确实要发用 `--force`）。

  这条规矩是补上的。在那之前版本号一度涨得没有意义：`v0.3.2` ~ `v0.3.5` 四个版本的
  规则内容与前一版**完全相同**（纯工程改动），而 `v0.3.0` / `v0.3.1` 是同一批工作的两半，
  中间那个状态两份产物还互相矛盾。这些版本号都已撤销 / 合并，详见 `CHANGELOG.md`。

手机端版本号和 PC 版**没有对应关系**，两套编号各管各的：

- 手机端版本（本仓库的 `VERSION.txt`）管规则内容的迭代。
- PC 版版本（[`reroc8/clash-verge-share-kit`](https://github.com/reroc8/clash-verge-share-kit) 的 `VERSION.txt`）是规则来源的真源版本，目前是 `v0.3.34`。

想知道某份产物是从 PC 哪一版生成的：

- Shadowrocket 的 `.conf` 头部有一行 `# Source: reroc8/clash-verge-share-kit v0.3.34`。
- Karing 的 JSON 是 Karing 私有格式，不往里加自定义字段（避免导入被拒），对应关系记在 `CHANGELOG.md` 每版条目里。

## 规则来源与生成

两份产物都是脚本产物，**不手工维护**。规则源是 PC 版仓库的 GitHub 源码：

```text
https://raw.githubusercontent.com/reroc8/clash-verge-share-kit/main/config/Merge.yaml
```

```bash
python3 scripts/build-karing-rules.py        [规则源] [--out-dir 目录]
python3 scripts/build-shadowrocket-rules.py  [规则源] [--out-dir 目录]
```

不传规则源就走上面的 GitHub 地址。**离线或想用本机那份配置时，传路径即可**：

```bash
python3 scripts/build-karing-rules.py ~/Desktop/Clash配置/clash-verge-share-kit/config/Merge.yaml
```

取的是 GitHub 源码而不是本机文件，好处是不依赖任何人的机器状态：谁 clone 下来跑出来的产物都一样，也能在 CI 里跑。

- 显式 `DOMAIN-SUFFIX` / `DOMAIN` / `DOMAIN-KEYWORD` 直接搬运。
- PC 端靠 `RULE-SET` 表达的宽泛覆盖，两个脚本各自换算：
  Karing 用内置规则集（`geosite:*` / `geoip:*` / `acl:*`），
  Shadowrocket 展开成显式域名（脚本里的 `RULE_SET_EXPANSION`）。
- `PROCESS-NAME`、`IP-CIDR`、`MATCH` 这类搬不过去的，在脚本里显式跳过，不静默丢弃。
- 未登记的规则集、未知策略名、未处理的规则类型、一个策略被两个组声明、空分组，
  都会直接报错退出。

## 怎么保证不出错

这个项目最容易出的两类错，各有一道防线。

**第一类：产物落后于 PC 版。** `v0.1.x` 到 `v0.2.1` 之间 Shadowrocket 落后了 93 条，原因是当时它由手工维护、没有接规则源。现在有三道闸：

1. **脚本生成** —— 产物不再是手写的，改 PC 配置后重新生成即可，不会再出现「改了一边忘了另一边」。

2. **漂移检测** —— `bash scripts/check-drift.sh` 会把产物重新生成到临时目录和仓库里的对比，
   不一致就报错并打印 diff；`--fix` 直接重新生成。

   ```bash
   bash scripts/check-drift.sh         # 只检测
   bash scripts/check-drift.sh --fix   # 检测并重新生成
   ```

3. **发版卡口** —— `build-release.command` 在打包前强制跑一遍漂移检测和产物约束检查，
   任何一项不过就不出包。

**第二类：产物本身被改错。** 几个关键约束（组顺序、地区映射、内置规则集名字）以前只写在注释里，
改错了没人拦。现在钉在 `tests/test_products.py` 里：

```bash
python3 -m unittest discover -s tests -v
```

约束包括：

- 两个产物的分组名与顺序完全一致，`YouTube` 在 `Google` 之前（否则 `youtubei.googleapis.com` 被 `googleapis.com` 抢走）
- 所有精确分组排在国内直连和代理之前（否则 `tgalileo.com` 会被判成直连）
- Karing 的域名集合是 Shadowrocket 的子集（两份产物同构）
- `tgalileo.com` 走代理、`mail.com` / `lexmount.com` / `muse.*` 走美国、`dola.com` 走新加坡
- `rule_set_build_in` 的名字在已验证白名单内（写错不会报错，只会静默不匹配）
- `domain_suffix` 带前导点、无跨组重复域名
- `.conf` 头部带 PC 源版本标注

**自动跑。** `.github/workflows/verify.yml` 在每次 push、PR，以及**每天定时**执行上面全部检查。
PC 版改了规则不会通知这边，定时检查是唯一的自动发现手段；一旦漂移，workflow 失败并给仓库所有者发邮件。

本地改完规则后的完整流程：

```bash
bash scripts/check-drift.sh --fix             # 按 PC 源码重新生成
python3 -m unittest discover -s tests -v      # 确认没破坏约束
git diff                                      # 看差异是否符合预期
```

## 发版流程

```bash
# 1. 先在 CHANGELOG.md 顶部写好新版本的变更说明（脚本不会替你写）
# 2. 一处命令改齐所有位置的版本号；CHANGELOG 缺条目会直接报错
python3 scripts/bump-version.py vX.Y.Z

# 3. 提交
git add -A && git commit -m "Ship vX.Y.Z: ..."

# 4. 出包（内部会跑版本一致性、产物约束、敏感信息扫描、漂移检测，任何一项不过都不出包）
bash scripts/build-release.command

# 5. 打 tag + 建 GitHub Release 并上传 zip（Release 说明自动从 CHANGELOG 抽取）
bash scripts/publish-release.sh --dry-run     # 先看看会做什么
bash scripts/publish-release.sh
```

发布包不在仓库里（`dist/` 被 gitignore），只通过 GitHub Release 分发：

```text
https://github.com/reroc8/mobile-proxy-share-kit/releases
```

## 思路来源

这一节说的是**思路**参考。规则内容本身来自上面那个 PC 版仓库，不是从这里抄的。

这不是泛用科学上网规则，思路参考了两个方向：

- `blackmatrix7/ios_rule_script`：参考其 OpenAI、Claude、Gemini、Copilot 等专项规则覆盖思路。
- `Johnshall/Shadowrocket-ADBlock-Rules-Forever`：只参考其手机入口、二维码和多规则发布说明方式。

本项目没有照搬通用懒人整包，规则目标不同：

- 不使用一个泛用 `Proxy` 承接所有海外服务。
- 不使用广告拦截规则。
- AI 规则放在 Google / YouTube / 通用代理规则前面。
- 最终兜底为直连，避免没识别的网站被强行送进普通代理。

## 安全原则

不要提交这些内容：

- 订阅链接
- 节点配置
- 账号、密码、token
- 含有真实节点链接的文件

提交前跑一遍 `scripts/check-sensitive.sh`。

## 免责声明

这套规则只整理流量路径，不处理平台账号合规问题。AI 服务、交易所、流媒体平台可能有自己的风控和地区限制，使用者需要遵守对应平台规则。
