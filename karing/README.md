# Karing 分流规则

当前版本：`v0.2.0`

## 适合谁

- 用 Karing（iOS / Android / Windows / macOS 同一套 App）。
- 已经有自己的订阅和节点。
- 主要想让 Claude、ChatGPT、Gemini 这类 AI 服务走更稳定的线路。
- 能接受在 Karing 里点几步把规则导进去。

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

## 导入后必做两件事

Karing 的「分流规则」页才是真正决定流量去哪的地方，JSON 只提供了分组和域名。

1. **打开「自定义分流组」开关**，并把它排在 `final` 之前。
2. **逐组设置出站**。JSON 里给的是开箱可用的默认值：
   - `🤖 Claude` / `🧠 国际 AI` / `🌐 Google` / `🎬 YouTube` / `✈️ Telegram` / `🚀 代理` → 当前选择（`currentSelected`）
   - `🏠 国内直连` → 直连（`direct`）
3. **把 `final` 设为直连**。这是兜底，和 PC 版的 `MATCH,DIRECT` 一致：没命中的站点直连，避免国内 `.com` 小站被误送进代理。
4. 首页模式切到「规则」。

## 地区隔离（Claude 只走美国）

这是本规则包的核心目的，但**出站不在 JSON 里，也没法在 JSON 里** —— 地区组的名字是你自己起的。

做法：

1. 在 Karing 里建一个「自定义自动选择」组，只放美国节点（例如命名 `US`）。
2. 回到「分流规则」页，把 `🤖 Claude` 的出站指到这个美国组。
3. 想更严格的话，`🧠 国际 AI` 也指到同一个组。

PC 版里有几条按地区写死的规则，在 Karing 上统一落进了 `🚀 代理`，需要区别对待时手动挪：

| 域名 | PC 版目标 | 建议 |
|---|---|---|
| `mail.com` | 美国 | 挪到你的美国组 |
| `lexmount.com` | 美国 | 挪到你的美国组 |
| `muse.meta.com` / `muse.ai` | 美国 | 挪到你的美国组 |
| `dola.com` | 新加坡 | 挪到你的新加坡组 |

## 分组说明

| 分组 | 出站 | 说明 |
|---|---|---|
| `🤖 Claude` | 当前选择 | Claude / Anthropic 全部域名，含 MCP、ghost、b-cdn、Cloudflare 边缘 |
| `🧠 国际 AI` | 当前选择 | OpenAI、Gemini、Perplexity、Cursor、Copilot、HuggingFace、Midjourney 等 |
| `🌐 Google` | 当前选择 | Google 登录、Gmail、OAuth、支付 |
| `🎬 YouTube` | 当前选择 | YouTube / googlevideo / ytimg |
| `✈️ Telegram` | 当前选择 | Telegram 域名与官方 IP 段 |
| `🏠 国内直连` | 直连 | 国内 AI 服务、钉钉、腾讯系直连，以及国内域名 / IP |
| `🚀 代理` | 当前选择 | 其余明确要走代理的海外站点 |

## 和 PC 版（Clash Verge）的差异

规则内容从 PC 版 `Merge.yaml` 生成，转不过来的部分在这里说清楚，别以为是漏了：

| PC 版 | Karing 上怎么处理 |
|---|---|
| `RULE-SET,apple / icloud,DIRECT` | 不建组，兜底就是直连 |
| `RULE-SET,tld-proxy,Proxies` | 不搬。兜底是直连，照搬会把大量国内 `.com` 误送进代理 |
| `PROCESS-NAME-REGEX` 进程级规则（钉钉、Muse） | Karing 的自定义分流组虽然支持进程名，但只在 PC 生效，且名字要装完才知道，所以不预置 |
| `RULE-SET,applications,DIRECT` | 同上，属于按本机应用配置的事 |
| 交易所分组 | PC 版本身没有交易所规则，这里保持对齐；需要的话自己加组 |

## 60 秒检查

| 检查项 | 打开什么 | 正常表现 | 不正常先看哪里 |
|---|---|---|---|
| Claude | `claude.ai` | 能打开并正常对话 | `🤖 Claude` 出站是不是美国组 |
| ChatGPT | `chatgpt.com` | 能打开并正常对话 | `🧠 国际 AI` 出站 |
| Gemini | `gemini.google.com` | 能打开 Gemini | 上一条；再确认 `🧠 国际 AI` 排在 `🌐 Google` 前面 |
| Google | `google.com` 或 Gmail | 能搜索、能进邮箱 | `🌐 Google` 出站 |
| YouTube | `youtube.com` | 视频能播放 | `🎬 YouTube` 出站 |
| 国内网站 | 百度、淘宝、腾讯系 | 打开正常 | 确认 `final` 是直连、模式是「规则」 |

规则在「分流规则」页里**从上到下**匹配，先命中先生效。所以 `🤖 Claude` 和 `🧠 国际 AI` 必须排在 `🌐 Google` 前面，否则 Gemini 会被 Google 组提前接走。

## 一句话给小白

这份规则不是为了去广告，也不是为了全网代理。它只优先保证：Claude 走美区，ChatGPT / Gemini 等 AI 不和普通 Google / YouTube / 代理混在一起。

## 注意

- 这份 JSON **不含任何节点、订阅、账号**，只有分组和域名规则，可以安全公开。
- 导入规则之前，必须先导入自己的订阅。
- 规则由 `scripts/build-karing-rules.py` 从 PC 版 `Merge.yaml` 生成，不要手改 JSON —— 改了会盖掉。
