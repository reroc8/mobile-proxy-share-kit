# Karing 分流规则

当前版本：`v0.2.9`

## 适合谁

- 用 Karing（iOS / Android / Windows / macOS 同一套 App）。
- 已经有自己的订阅和节点。
- 主要想让 Claude、ChatGPT、Gemini 这类 AI 服务走更稳定的线路。
- 能接受在 Karing 里点几步把规则导进去。

## 规则从哪来

由 `scripts/build-karing-rules.py` 从 PC 版仓库的 GitHub 源码生成，**不要手改**。和 `shadowrocket/` 用的是同一个规则源、同一套分组顺序。

PC 靠 `RULE-SET` 表达、Karing 有内置规则集可对应的部分，用 `rule_set_build_in` 直接引用（`acl:Claude`、`geosite:google`、`acl:ChinaDomain`、`geosite:geolocation-!cn` 等），比展开成域名更省、也更新。

## 为什么不给 Clash 格式

Karing 导入 Clash 配置时**只取节点，不读 `proxy-groups` 和 `rules`**。给它一份 Clash 配置也带不进分流，所以这里用 Karing 自己的「自定义分流组」格式，也就是它导出时用的那份 JSON。

## 现在没法做到「一键导入」

Karing 的 URL Scheme 官方只开放了三种：

```text
karing://install-config?url=...&name=...   添加配置（订阅）
karing://restore-backup?url=...            恢复备份
karing://connect / disconnect / reconnect  连接控制
```

**没有导入分流组的 scheme**，所以自定义分流组只能走「下载 JSON → App 内导入」这条路。下面按这个流程写。

## 三步导入

1. **先把订阅加进 Karing**：首页「+」→「导入配置链接」，粘贴你自己的订阅。

2. **下载规则文件**（手机浏览器直接点，会存进「文件 / 下载」）：

```text
https://reroc8.github.io/mobile-proxy-share-kit/karing/karing-diversion-rules.json
```

   或者从 GitHub 原始地址取：

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/karing/karing-diversion-rules.json
```

3. **导入规则**：「分流」→「自定义分流组」→ 右上角 `⋮` →「导入」→ 选刚下载的 JSON。

## 导入后必做

Karing 的「分流规则」页才是真正决定流量去哪的地方，JSON 只提供了分组和域名。

1. **打开「自定义分流组」开关**，并把它排在 `final` 之前。
2. **把 `final` 设为代理**。没命中的站点走代理兜底 —— 宁可国内小众站稍慢，也不要墙外站打不开。国内域名和 IP 由 `🏠 国内直连` 组先兜住，不会受影响。
3. **逐组设置出站**。JSON 里给的是开箱可用的默认值：
   - `🤖 Claude` / `🧠 国际 AI` / `🎬 YouTube` / `🌐 Google` / `💱 交易所` / `✈️ Telegram` / `🇺🇸 美国` / `🇸🇬 新加坡` / `🚀 代理` → 当前选择（`currentSelected`）
   - `🏠 国内直连` → 直连（`direct`）
4. 首页模式切到「规则」。

## 地区隔离（Claude 只走美国）

这是本规则包的核心目的，但**出站不在 JSON 里，也没法在 JSON 里** —— 地区组的名字是你自己起的。

做法：

1. 建两个「自定义自动选择」组，一个只放美国节点、一个只放新加坡节点。
2. 回到「分流规则」页，逐组改出站：
   - `🤖 Claude` → 美国组（想更严格的话 `🧠 国际 AI` 也指过去）
   - `🇺🇸 美国` → 美国组
   - `🇸🇬 新加坡` → 新加坡组
   - `💱 交易所` → 台湾或新加坡组

PC 版里按地区写死的域名现在都有了独立分组，不用再从别处挪。

## 分组说明

| 分组 | 出站 | 说明 |
|---|---|---|
| `🤖 Claude` | 当前选择 | Claude / Anthropic 全部域名，含 MCP、ghost、b-cdn、Cloudflare 边缘 |
| `🧠 国际 AI` | 当前选择 | OpenAI、Gemini、Perplexity、Cursor、Copilot、HuggingFace、Midjourney 等 |
| `🎬 YouTube` | 当前选择 | YouTube / googlevideo / ytimg |
| `🌐 Google` | 当前选择 | Google 登录、Gmail、OAuth、支付 |
| `💱 交易所` | 当前选择 | OKX、Bybit、Binance、Coinbase 等 26 条 |
| `✈️ Telegram` | 当前选择 | Telegram 域名与官方 IP 段 |
| `🇺🇸 美国` | 当前选择 | 区域锁美国：`mail.com`、`lexmount.com`、`muse.meta.com`、`muse.ai` |
| `🇸🇬 新加坡` | 当前选择 | 区域锁新加坡：`dola.com` |
| `🏠 国内直连` | 直连 | 国内 AI 服务、钉钉、腾讯系直连，以及国内域名 / IP |
| `🚀 代理` | 当前选择 | 其余明确要走代理的海外站点 |

## 顺序不能乱

规则在「分流规则」页里**从上到下**匹配，先命中先生效。两条硬要求：

**1. `🎬 YouTube` 必须排在 `🌐 Google` 前面。** 否则 `youtubei.googleapis.com` 会被 `googleapis.com` 抢走，永远进不了 YouTube 组。

**2. 所有精确分组必须排在 `🏠 国内直连` 和 `🚀 代理` 前面。** PC 版里有 `tgalileo.com` 这种「在 cn 域名库里、但要走代理」的域名，靠精确规则前置才能改走代理。国内直连一旦提前就会把它判成直连，和 PC 的意图正好相反。

## 和 PC 版（Clash Verge）的差异

规则内容从 PC 版 `Merge.yaml` 生成，转不过来的部分在这里说清楚，别以为是漏了：

| PC 版 | Karing 上怎么处理 |
|---|---|
| `RULE-SET,google` | `geosite:google` |
| `RULE-SET,cn-domain` | `acl:ChinaDomain` |
| `RULE-SET,cn-ip` / `private-ip` | `acl:ChinaIp` |
| `RULE-SET,global-domain` / `tld-proxy` | `geosite:geolocation-!cn` |
| `RULE-SET,telegramcidr` | `geoip:telegram` |
| `RULE-SET,apple` / `icloud` | 不建组，按内置规则集与 IP 归属走 |
| 银行 / 券商 | **手机端独有**。Karing 内置规则集里没有金融分类，域名是从 LingJingMaster 的清单转过来的**生成时快照** —— 对方更新了要重跑生成脚本 |
| `PROCESS-NAME-REGEX` 进程级规则（钉钉、Muse） | 自定义分流组虽然支持进程名，但只在 PC 生效、名字要装完才知道，不预置 |
| `RULE-SET,applications,DIRECT` | 同上，属于按本机应用配置的事 |
| 交易所分组 | **手机端独有**，PC 版没有这块业务 |

## 60 秒检查

| 检查项 | 打开什么 | 正常表现 | 不正常先看哪里 |
|---|---|---|---|
| Claude | `claude.ai` | 能打开并正常对话 | `🤖 Claude` 出站是不是美国组 |
| ChatGPT | `chatgpt.com` | 能打开并正常对话 | `🧠 国际 AI` 出站 |
| Gemini | `gemini.google.com` | 能打开 Gemini | 上一条；再确认 `🧠 国际 AI` 排在 `🌐 Google` 前面 |
| Google | `google.com` 或 Gmail | 能搜索、能进邮箱 | `🌐 Google` 出站 |
| YouTube | `youtube.com` | 视频能播放 | `🎬 YouTube` 出站，且排在 Google 之前 |
| 交易所 | OKX / Bybit / Binance | 页面能打开 | `💱 交易所` 出站 |
| 国内网站 | 百度、淘宝、腾讯系 | 打开正常 | 确认 `final` 是直连、模式是「规则」 |

## 一句话给小白

这份规则不是为了去广告，也不是为了全网代理。它只优先保证：Claude 走美区，ChatGPT / Gemini 等 AI 不和普通 Google / YouTube / 代理混在一起。

## 注意

- 这份 JSON **不含任何节点、订阅、账号**，只有分组和域名规则，可以安全公开。
- 导入规则之前，必须先导入自己的订阅。
- 规则由脚本从 PC 版仓库源码生成，不要手改 JSON —— 改了会盖掉。PC 那边规则改完后，跑 `bash scripts/check-drift.sh --fix` 重新生成。
