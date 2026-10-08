# Hiddify 路由规则

当前版本：`v0.2.9`

## 先说清一件事：这份做不到「分组隔离」

Hiddify 的规则里，`outbound` 是一个**枚举**，只有四个值（定义在 `hiddify-app` 的
`android/app/src/main/protos/v2/config/route_rule.proto`）：

```protobuf
enum Outbound { proxy = 0; direct = 1; direct_with_fragment = 2; block = 3; }
```

**没有「节点组」的概念。** 所以这份产物只能表达「这个域名走代理 / 直连」，
**做不到「Claude 走美国、AI 走别的」** —— 那是 Shadowrocket / Clash 才有能力做的事。

这份里的「组」（`🤖 Claude`、`🧠 国际 AI`…）只是**规则的组织方式**，方便你在 Hiddify
的规则列表里看和单独开关，**不影响出口**。

如果你的核心诉求是出口隔离，用 `shadowrocket/` 或 `clash/` 那两份，别用这份。

## 什么时候用这份

- 你已经用 Hiddify，不想换客户端
- 你要的是**精确的「哪些域名走代理」**判断（比机场给的默认规则细）
- 你不介意手动切节点来换出口地区

## 产物

| 文件 | 是什么 |
|---|---|
| `hiddify-route-rules.json` | 规则本体，`{"rules": [...]}` |
| `import-link.txt` | **一键导入链接**，就是上面 JSON 的 base64 |

## 怎么导入

链接长这样（内容在 `import-link.txt` 里，6000 多字符）：

```text
hiddify:///settings/routing-options?routeRule=<base64>
```

两条路：

**① 直接点链接** —— 在手机上打开 `import-link.txt`，点那个链接，Hiddify 会弹确认框。

**② 从剪贴板导入** —— 复制链接全文，打开 Hiddify →「设置 → 路由选项」→ 从剪贴板导入。
（这条路在微信里打开链接时更可靠，因为微信内置浏览器不处理 `hiddify://` 这种自定义协议。）

> 这个格式不是我编的，是抄 Hiddify 自己的导出函数（`rules_notifier.dart` 的
> `exportJsonToClipboard`），它导出到剪贴板用的就是这个 `hiddify:///settings/routing-options?routeRule=`。

## 分组

| 组 | outbound | 内容 |
|---|---|---|
| `🤖 Claude` | proxy | Claude / Anthropic 全部域名 |
| `🧠 国际 AI` | proxy | OpenAI、Gemini、Perplexity、Cursor 等 |
| `🎬 YouTube` | proxy | YouTube / googlevideo / ytimg |
| `🌐 Google` | proxy | Google 登录、Gmail、OAuth |
| `💱 交易所` | proxy | OKX、Bybit、Binance 等 |
| `✈️ Telegram` | proxy | Telegram 域名 |
| `🌍 地区锁定` | proxy | 必须走特定地区的域名（`mail.com`、`lexmount.com`、`muse` 系、`dola.com`） |
| `🏠 国内直连` | direct | 国内域名 + 国产 AI 服务 |
| `🚀 代理` | proxy | 通用海外域名 |

顺序就是 `list_order` —— Hiddify 按这个顺序匹配，精确的排前面。

## 还没有的

- **银行 / 券商**：它们在 PC 规则源里不存在，另外三份产物是引 `LingJingMaster` 的规则集。
  这份要加得引入同样的外部数据源。
- **海外域名兜底**：`Global_Domain` 那种三万多条的规则集还没接。目前没命中的域名
  由 Hiddify 自己的兜底逻辑处理，不受这份控制。

## 注意

这份产物**不含节点、订阅、账号**，只有域名和「走不走代理」的判断，可以安全公开。
