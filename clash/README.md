# 手机端 Clash 覆写

当前版本：`v0.2.5`

## 适合谁

- 手机或电脑上用 ClashMetaForAndroid / FlClash / Stash 这类 **mihomo 内核**的客户端。
- 已经有自己的订阅和节点。
- 想让 Claude、ChatGPT、Gemini 这些 AI 服务走稳定线路。

## 规则从哪来

由 `scripts/build-clash-rules.py` 从 PC 版仓库源码生成，**不要手改**。

这份产物和另外两份不一样：**它不做格式转换**。PC 版的 `Merge.yaml` 本身就是 Clash 语法，
手机端 Clash 吃同一套，所以这里只是把它搬过来，外加两件事：

1. **补一段 `proxy-groups`**。PC 那边靠 `Script.js` 按订阅里的节点动态建组；手机端没有 JS
   执行器，改用 mihomo 的 `include-all` + `filter`，按节点名里的地区字样自动把节点收进
   `US` / `SG` 组 —— 效果等同 PC 的自动分组。
2. 把策略名 `Proxies` 改成另两份产物统一用的 `Proxy`，并补上手机端独有的 `Exchange` 组。

地区识别用的正则直接取自 PC 版 `config/Script.js` 的 `regionPatterns`，保证两边认出来的
是同一批节点。

## 怎么用

**ClashMetaForAndroid**：设置 → 覆写 → 粘贴 `clash-override.yaml` 的内容（或填它的地址）→ 保存 → 重新加载配置。

**FlClash**：配置 → 对应订阅 → 覆写 / 自定义配置 → 粘贴同样内容。

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/clash/clash-override.yaml
```

然后：

- 到策略组里确认 `Claude` 指向 `US`，`Exchange` 指向 `SG`。
- 全局模式选「规则」。

## 分组

| 分组 | 默认走哪 | 说明 |
|---|---|---|
| `Claude` | `US` → `Proxy` → 直连 | Claude / Anthropic 全部域名 |
| `AI` | `US` → `SG` → `Proxy` → 直连 | OpenAI、Gemini、Perplexity、Cursor 等 |
| `YouTube` | `Proxy` → `US` → `SG` → 直连 | YouTube / googlevideo / ytimg |
| `Google` | `Proxy` → `US` → `SG` → 直连 | Google 登录、Gmail、OAuth |
| `Exchange` | `SG` → `Proxy` → 直连 | OKX、Bybit、Binance 等 |
| `Telegram` | `Proxy` → `US` → `SG` → 直连 | Telegram 域名与 IP 段 |
| `US` | 自动收美国节点 | 按节点名里的「美国 / US / 🇺🇸」等字样归类 |
| `SG` | 自动收新加坡节点 | 按「新加坡 / Singapore / 🇸🇬」等字样归类 |
| `Proxy` | 全部节点 | 通用出口 |
| `DIRECT` | —— | Clash 内置，不需要定义 |

`US` / `SG` 里都放了一个 `DIRECT` 兜底：mihomo 不允许策略组一个候选都没有，
订阅里没有美国节点时，整个配置不能因此加载失败。

## 和其他两份产物的关系

三份产物**规则内容同源**，分组名一致：

| 产物 | 客户端 | 分组数 |
|---|---|---|
| `karing/karing-diversion-rules.json` | Karing | 10（含 DIRECT） |
| `shadowrocket/*.conf` | Shadowrocket | 10（含 DIRECT） |
| `clash/clash-override.yaml` | mihomo 系 | 10（DIRECT 是内置的，只定义 9 个） |

## 还没验证的部分

- **产物本身验证过**：YAML 能解析、规则目标都指向存在的组、有 `MATCH` 兜底、组名与另两份一致，
  这些都在 `tests/test_products.py` 里钉住。
- **客户端加载这一步没有真机验证过**：我没法确认 CMFA / FlClash 的「覆写」是否接受
  这一份片段（尤其 `include-all` 是否在覆写里生效）。如果你用它跑通了，或者跑不通，
  都值得回来说一声。
- 跑不通时的回退：把 `rules:` 段整体粘到客户端的「自定义规则」里，`proxy-groups` 段按下面的
  分组表手动建组。

## 注意

这份产物**不含任何节点、订阅、账号**，只有策略组和路由规则，可以安全公开。
节点由你自己的订阅提供。
