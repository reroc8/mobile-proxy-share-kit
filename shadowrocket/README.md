# Shadowrocket 小火箭 AI 风控稳定规则

当前版本：`v0.3.0`

## 适合谁

- 已经在 iPhone / iPad 上使用 Shadowrocket。
- 已经有自己的订阅和节点。
- 主要想让 Claude、ChatGPT、Gemini 这类 AI 服务走更稳定的线路。
- 可以手动把节点放到几个策略组里。

## 规则从哪来

三份 `.conf` 都由 `scripts/build-shadowrocket-rules.py` 从 PC 版 Clash Verge 的 `Merge.yaml` 生成，**不要手改**。和 `karing/` 用的是同一个规则源，两边不会再各走各的。

PC 靠 `RULE-SET` 表达、Shadowrocket 没有等价写法的部分，在脚本里展开成显式域名（脚本里的 `RULE_SET_EXPANSION`），逐条标注了对应哪个 PC 规则集。

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
| `US` | 只放美国节点（`mail.com`、`lexmount.com`、`muse` 系） |
| `SG` | 只放新加坡节点（`dola.com`） |
| `Proxy` | 普通代理节点 |

## 高级用法

如果你已经在 Shadowrocket 里准备好了这些策略名字，可以只导入纯规则片段：

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/Shadowrocket.rules.conf
```

需要存在的策略名仍是：`Claude / AI / Google / YouTube / Exchange / Telegram / US / SG / Proxy`。

`DIRECT` 是 Shadowrocket 内置策略，不需要手动创建。

## 兼容旧链接

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/Shadowrocket.conf
```

这个旧链接会继续保留，内容与 `Shadowrocket.rules.conf` 完全一致。新用户建议优先用 `Shadowrocket.full.conf`。

手机入口页：

```text
https://reroc8.github.io/mobile-proxy-share-kit/
```

## 规则顺序

1. 局域网和本机地址直连。
2. 国内 AI 服务、钉钉、腾讯系，以及国内常见网站直连。
3. Claude 先命中 `Claude`。
4. OpenAI / Gemini / Copilot / Cursor 等 AI 服务命中 `AI`。
5. YouTube 命中 `YouTube`。
6. Google 登录和 Gmail 命中 `Google`。
7. 交易所命中 `Exchange`。
8. Telegram 命中 `Telegram`。
9. `US` / `SG` 对应的地区锁定站点。
10. 明确海外常见服务命中 `Proxy`。
11. 中国大陆 IP 直连。
12. 未命中规则默认直连。

**YouTube 必须排在 Google 前面**：`youtubei.googleapis.com` 会被 `googleapis.com` 抢走。PC 版也是先写 YouTube 再套 Google 规则集，这里对齐它。

## 与 PC 版的差异

| PC 版 | Shadowrocket 上怎么处理 |
|---|---|
| `RULE-SET,google` | 展开成显式域名（`google.com`、`gmail.com`、`gstatic.com`、`googleapis.com`、`googleusercontent.com`） |
| `RULE-SET,cn-domain` / `applications` | 展开成显式国内站点，另有 `DOMAIN-SUFFIX,cn` 和 `DOMAIN-KEYWORD,-cn`，末尾还有 `GEOIP,CN,DIRECT` |
| `RULE-SET,global-domain` / `tld-proxy` | 展开成显式海外站点 |
| `RULE-SET,cn-ip` / `private-ip` | 由 `GEOIP,CN,DIRECT` 和开头的 `IP-CIDR` 覆盖 |
| `RULE-SET,apple` / `icloud` | 不单列，兜底就是直连 |
| `PROCESS-NAME-REGEX` 进程级规则（钉钉、Muse） | 小火箭没有进程名匹配，不预置 |
| 交易所分组 | **Shadowrocket 独有**，PC 版没有这块业务 |

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
