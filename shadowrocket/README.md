# Shadowrocket 小火箭 AI 风控稳定规则

当前版本：`v0.1.2`

## 适合谁

- 已经在 iPhone / iPad 上使用 Shadowrocket。
- 已经有自己的订阅和节点。
- 主要想让 Claude、ChatGPT、Gemini 这类 AI 服务走更稳定的线路。
- 可以手动把节点放到几个策略组里。

## 推荐使用方式

小白优先导入完整骨架模板：

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/Shadowrocket.full.conf
```

它会声明下面这些策略名字，但不会提供任何节点。导入后仍然要把自己的订阅节点放到对应策略里。

| 策略名 | 放什么节点 |
|---|---|
| `Claude` | 只放美国节点 |
| `AI` | 美国节点优先，台湾节点备用 |
| `Google` | 常用稳定节点 |
| `YouTube` | 看视频稳定的节点 |
| `Exchange` | 台湾、新加坡节点 |
| `Telegram` | 常用稳定节点 |
| `Proxy` | 普通代理节点 |

## 高级用法

如果你已经在 Shadowrocket 里准备好了这些策略名字，可以只导入纯规则片段：

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/Shadowrocket.rules.conf
```

需要存在的策略名仍是：`Claude / AI / Google / YouTube / Exchange / Telegram / Proxy`。

`DIRECT` 是 Shadowrocket 内置策略，不需要手动创建。

## 兼容旧链接

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/Shadowrocket.conf
```

这个旧链接会继续保留，等同于纯规则片段。新用户建议优先用 `Shadowrocket.full.conf`。

手机入口页：

```text
https://reroc8.github.io/mobile-proxy-share-kit/
```

## 规则顺序

1. 局域网和常见国内服务直连。
2. Claude 先命中 `Claude`。
3. OpenAI / Gemini / Copilot / Cursor 等 AI 服务命中 `AI`。
4. Google 登录和 Gmail 命中 `Google`。
5. YouTube 视频命中 `YouTube`。
6. 交易所命中 `Exchange`。
7. Telegram 命中 `Telegram`。
8. 明确海外常见服务命中 `Proxy`。
9. 中国大陆 IP 直连。
10. 未命中规则默认直连。

## 参考逻辑

AI 域名覆盖参考了 `blackmatrix7/ios_rule_script` 里的 OpenAI、Claude、Gemini、Copilot 专项规则，但本文件按自己的策略组重新组织：

- Claude 不混入普通 AI，独立到 `Claude`。
- Gemini 先进入 `AI`，避免被 Google 组提前命中。
- OpenAI / Copilot 的核心接口归入 `AI`，通用 Cloudflare、Statsig、Bing、Google 支撑域不强行绑进 `AI`。
- DeepSeek / Kimi / Moonshot 等国内 AI 直连，不进入国际 `AI` 策略。
- 不使用广告拦截规则。

## 导入后 60 秒检查

| 检查项 | 打开什么 | 正常表现 | 如果不正常先看哪里 |
|---|---|---|---|
| Claude | `claude.ai` | 能打开并正常对话 | `Claude` 只选美国节点 |
| ChatGPT | `chatgpt.com` | 能打开并正常对话 | `AI` 先选美国节点 |
| Gemini | `gemini.google.com` | 能打开 Gemini | `AI` 不要混普通 Google 节点 |
| Google | `google.com` 或 Gmail | 能搜索或进邮箱 | `Google` 换稳定节点 |
| YouTube | `youtube.com` | 视频能播放 | `YouTube` 换视频稳定节点 |
| 交易所 | OKX / Bybit / Binance | 页面能打开 | `Exchange` 只选台湾/新加坡 |
| 国内网站 | 百度、淘宝、腾讯系网站 | 打开正常 | 确认没有开全局代理 |

## 一句话给小白

这份规则不是为了去广告，也不是为了全网代理。它只优先保证：Claude 走美区，ChatGPT/Gemini 等 AI 不和普通 Google/YouTube/Proxy 混在一起。

## 注意

这份规则不包含任何节点。导入规则之前，必须先导入自己的订阅并准备好策略组。
