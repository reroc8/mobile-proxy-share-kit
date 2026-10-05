# Changelog

## 版本号怎么读

**版本号只表示「规则内容」的版本** —— 域名、分组、分组顺序。改了这些才发新版本；
测试、CI、脚本、文档这类工程改动走普通 commit，不占版本号。`scripts/bump-version.py`
会在规则内容没变时拒绝改版本号。

> **历史说明**：v0.3.2 ~ v0.3.5 这四个版本号的规则内容与 v0.3.1 **完全相同** ——
> 它们的改动全是工程性质（换规则源、加来源标注、加测试与 CI、加发版工具），
> 手机端拿到的规则一个字都没变。当时没有「只在规则变化时发版」这条规矩。
> **这四个版本号已撤销**（tag 与 Release 均已删除），改动本身完整保留在下面的
> 「未计入版本的工程变更」里。当前版本号回到 **v0.3.1**，也就是最后一个真正改过规则的版本。

手机端和 PC 版（[`reroc8/clash-verge-share-kit`](https://github.com/reroc8/clash-verge-share-kit)）
是**两套独立的版本号**。每版对应的 PC 源版本记在下面，Shadowrocket 的 `.conf` 头部也会写一行
`# Source: ...`。Karing 的 JSON 是 Karing 私有格式，不往里塞自定义字段（避免导入被拒），
对应关系看这里的记录。

## v0.3.1


- **补齐 Karing 与 Shadowrocket 的同构性**。两份产物此前分组不一致：
  - Karing 新增 `💱 交易所`（26 条），此前只有小火箭能分流交易所。
  - Karing 把 `🚀 代理` 里混着的地区锁定域名拆成 `🇺🇸 美国` 和 `🇸🇬 新加坡` 两个独立组，PC 版本来就是分开的。
  - 两份产物现在都是 10 个分组，分组名与顺序一一对应，Karing 比 Shadowrocket 多出的域名条目为 **0**。
- **修正 Karing 的规则顺序**：`🎬 YouTube` 移到 `🌐 Google` 之前。此前 `youtubei.googleapis.com` 会被 `googleapis.com` 抢走，永远进不了 YouTube 组。
- 两份产物的组顺序统一为「精确规则 → 国内直连 → 代理」。精确规则必须前置，否则 `tgalileo.com` 这类「在 cn 域名库里但要走代理」的域名会被判成直连，和 PC 的意图相反。
- 新增 `scripts/check-drift.sh`：把产物重新生成到临时目录再和仓库里的逐字节对比，不一致就报错并打印 diff，`--fix` 直接重新生成。
- `build-release.command` 打包前强制跑漂移检测，产物落后于 PC 配置就不出包。
- 手机端独有分组（交易所）的定义挪到 `scripts/extra-rules.json`，两个生成脚本共用一份，不再各写各的。
- 两个生成脚本支持 `--out-dir`；新增「一个 PC 策略被两个分组声明」的报错，避免先声明的组静默吞掉规则。

## 未计入版本的工程变更

下面这些改动发生在 v0.3.1 之后，但**没有改变任何规则内容**（域名、分组、顺序都没动），
按「版本号只表示规则内容」的约定不该占版本号。原先误发成了 v0.3.2 ~ v0.3.5，
现已撤销这四个版本号，改动本身完整保留在这里。

### 发版工具（原 v0.3.5）

- 新增 `scripts/bump-version.py`：一处命令改齐所有位置的项目版本号。此前版本号散在
  `VERSION.txt` / `README.md` / `karing/README.md` / `shadowrocket/README.md` 四处，
  手工改漏过一次（README 说是 v0.2.0、VERSION.txt 已是 v0.3.0）。脚本会在
  `CHANGELOG.md` 缺少对应版本条目时直接报错，避免「改了版本号没写说明」。
- 新增 `scripts/publish-release.sh`：出包 → 打 tag → 建 GitHub Release 并把 zip 传上去，
  Release 说明从 `CHANGELOG.md` 对应段落自动抽取。此前 `dist/` 在 `.gitignore` 里，
  发布包只留在本机，别人从仓库根本拿不到成品。
  ```bash
  bash scripts/publish-release.sh --dry-run   # 只检查
  bash scripts/publish-release.sh             # 真发
  ```
- 补齐 `v0.2.0` ~ `v0.3.4` 的历史 tag。此前只有 `v0.1.0` ~ `v0.1.2` 有 tag，
  v0.2.0 之后完全没有版本锚点。
- 产物约束测试从 17 条扩到 21 条，新增版本号一致性检查：`VERSION.txt`、三个 README、
  `CHANGELOG.md` 最新条目必须完全对齐，且该版本条目下必须有变更说明。
- `check-sensitive.sh` 的扫描范围补上 `tests/` 和 `.github/`。
- **对应 PC 源：`v0.3.34`**（规则内容与前几版相同，本次只改工程流程）

### 产物约束测试与 CI（原 v0.3.4）

- 新增 `tests/test_products.py`：17 条产物约束检查，离线运行。此前几个关键约束只写在注释里，
  改错了没人拦 —— 现在钉死了：组顺序、`YouTube` 必须先于 `Google`、精确分组必须先于国内直连 / 代理、
  两份产物同构、`tgalileo.com` 归属、`mail.com` / `muse.*` / `dola.com` 的地区归属、
  内置规则集名字必须在上次从 Karing 源码校验出的白名单内、`domain_suffix` 带前导点、
  无跨组重复域名、`.conf` 带来源标注。
  已用 6 组变异（调换顺序、挪动域名、改错规则集名、加额外域名、抹掉标注、打乱段位置）逐条确认过
  断言真的会失败，不是装饰性测试。
- 新增 `.github/workflows/verify.yml`：push / PR / 每天定时跑产物约束检查、敏感信息扫描与漂移检测。
  PC 版改了规则不会通知这边，定时检查是唯一的自动发现手段。
- `build-release.command` 打包前增加产物约束检查，不过就不出包。
- README 重写「怎么保证不出错」章节，按「产物落后」和「产物被改错」两类风险分别说明防线。
- **对应 PC 源：`v0.3.34`**（规则内容与 v0.3.3 相同，仅新增检查）

### 来源标注（原 v0.3.3）

- Shadowrocket 三份 `.conf` 的头部新增 `# Source: reroc8/clash-verge-share-kit v0.3.34`，
  标明该产物由 PC 的哪一版生成。此前产物里没有任何信息能追溯它对应 PC 的哪一版 ——
  两套版本号又都是 `v0.3.x`，很容易误以为有关系。
- 新增 `mobile_rules.fetch_source_version()`：从 PC 仓库拉 `VERSION.txt`，取不到不阻断生成。
- README 补充版本号说明。
- **对应 PC 源：`v0.3.34`**（规则内容与 v0.3.2 相同，仅新增来源标注）

  回填历史对应关系：

  | 手机端 | 对应 PC 源 |
  |---|---|
  | v0.1.0 ~ v0.1.2 | 手工维护，不对应任何 PC 版本 |
  | v0.2.0 起 | `v0.3.34` |

### 规则源与产物对齐（原 v0.3.2）

- **规则源改为 PC 版仓库的 GitHub 源码**，不再读本机 `~/Desktop/Clash配置/.../Merge.yaml`：
  ```text
  https://raw.githubusercontent.com/reroc8/clash-verge-share-kit/main/config/Merge.yaml
  ```
  好处是不依赖任何人的机器状态 —— 谁 clone 下来跑出来的产物都一样，漂移检测也能挂 CI 了。离线时传本地路径即可，行为不变。
- 新增 `scripts/mobile_rules.py`：把取规则源、解析 `rules:` 段、读补充分组、解析参数这些两个脚本重复的逻辑抽成一份。
  两份产物必须同构，逻辑各写一遍早晚会改一边忘一边 —— v0.3.0 之前 Shadowrocket 落后 93 条就是这么来的。
- `check-drift.sh` 支持 `RULES_SOURCE` 环境变量指定规则源，默认走 GitHub。
- 规则源拉取失败（网络异常、URL 不存在、本地文件缺失）都会给出明确报错，不会静默产出空规则。


## v0.3.0


- **Shadowrocket 规则对齐 PC 版**。此前它停在 v0.1.2 的手工快照上，PC 端后续新增的 93 条域名一条都没跟过来；现在两份产物的规则源统一为 PC 版 `Merge.yaml`，缺口为 0。
  - 补上的包括：国内 AI 全家桶（豆包、通义、混元、智谱、Minimax、阶跃等约 40 条）、Claude 边缘域名（`clau.de`、`claudemcpclient.com`、`anthropic.auth0.com`、`servd-anthropic-website.b-cdn.net` 等）、Gemini 生态（Antigravity、Jules、Opal、NotebookLM、Stitch、`aicode` / `aida` / `aisandbox-pa`）、Telegram 新域名、以及 `lexmount.com` / `muse.meta.com` / `dola.com` / `mail.com` / `tgalileo.com` 等地区特例。
- 新增 `scripts/build-shadowrocket-rules.py`：`Merge.yaml` → Shadowrocket 三份 `.conf`。PC 的 `RULE-SET` 展开成显式域名（`RULE_SET_EXPANSION`），并在 `RULE_SET_COVERAGE` 里逐条说明覆盖方式；出现未登记的规则集、未知策略名、未处理的规则类型或空策略组都会报错退出。
- **修正 Shadowrocket 的规则顺序缺陷**：`YouTube` 现在排在 `Google` 前面，避免 `youtubei.googleapis.com` 被 `googleapis.com` 抢走。PC 版本来就是这个顺序。
- 新增 `US` / `SG` 两个策略组，承接 PC 里按地区写死的规则；之前这些域名在 Shadowrocket 侧完全没有。
- 因对齐 PC 而移除了几条 PC 判定为误绑的规则：`ai.com`、`gateway.bingviz.*`、`services.bingapis.com`、`api.microsoftapp.net`、`edgeservices.bing.com`、`bing-shopping.microsoft-falcon.io`、`client-api.arkoselabs.com`。交易所分组是 Shadowrocket 独有业务，保留。
- `build-release.command` 增加 `Shadowrocket.conf` 与 `Shadowrocket.rules.conf` 的一致性校验。

## v0.2.0


- 新增 `karing/` 产物：Karing 全平台（iOS / Android / Windows / macOS）自定义分流组 JSON，7 组 190 条显式域名规则 + 8 个内置规则集。
- 新增 `scripts/build-karing-rules.py`：从 PC 版 Clash Verge `Merge.yaml` 生成 Karing JSON，显式规则直接搬运，`RULE-SET` 映射为 Karing 内置规则集，遇到未登记的规则集或策略名直接报错，防止两边漂移。
- Karing 分流用其原生「自定义分流组」系统：实测 Karing 导入 Clash 配置只取节点、不读 `proxy-groups` / `rules`，Clash 格式带不进分流。
- 查证并记录 Karing 官方 URL Scheme 不支持导入分流组（只有 `install-config` / `restore-backup` / `connect`），因此落地页不做「一键导入」，改为同源下载 JSON + App 内导入。
- 产物同步一份到 `docs/karing/`，让手机在 GitHub Pages 上能一键下载（同源 `download` 才生效）。
- 明确收窄产物范围：**只维护 `karing/` 和 `shadowrocket/` 两份**，不再做 `clash/` 与 `hiddify/`，这两类客户端引导改用 Karing。
- 落地页与 README 重写为双产物结构，并补上「国内直连 / `final` 设直连」「Claude 走的美国组怎么建」等必做步骤。

## v0.1.2


- 拆分 Shadowrocket 使用入口：小白优先用 `Shadowrocket.full.conf` 完整骨架模板，高级用户可用 `Shadowrocket.rules.conf` 纯规则片段。
- `Shadowrocket.conf` 保留为旧链接兼容文件，内容仍是纯规则片段，不包含节点或订阅。
- 收窄 AI 规则：移除 Cloudflare、Statsig、Bing、Google 通用支撑域对 `AI` 策略的误绑。
- 国内 AI 服务改为直连：DeepSeek、Kimi、Moonshot 不再进入国际 `AI` 策略。
- 修复未安装 `rg` 时敏感信息扫描可能扫到脚本自身的问题。
- GitHub Pages 二维码改为本地静态图片，不再依赖第三方二维码服务。

## v0.1.1


- 增加 GitHub Pages 手机入口页，方便 iPhone 用户打开后复制规则链接或扫码。
- 增加 Shadowrocket 导入二维码入口。
- README 补充三步导入说明和 Johnshall 项目的参考边界：只参考入口页/二维码/发布说明，不引入广告拦截。
- 强化小白文案：本项目核心是 AI 风控稳定，不是去广告或泛用全网代理。

## v0.1.0


- 初版发布 Shadowrocket 小火箭 AI 风控稳定简化规则。
- Claude 独立命中 `Claude`，建议只放美国节点。
- OpenAI / ChatGPT / Gemini / Perplexity / Copilot / Cursor 等 AI 服务命中 `AI`，且 AI 规则放在 Google 规则前。
- 参考 blackmatrix7 的 OpenAI / Claude / Gemini / Copilot 专项规则补充验证码、风控、实时语音和 Gemini 相关域名。
- Google、YouTube、Exchange、Telegram 分开命中独立策略。
- 不启用广告 `REJECT`，避免登录、验证码、支付、风控接口被误伤。
- 未命中规则默认 `FINAL,DIRECT`。
