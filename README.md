# Mobile Proxy Share Kit

面向手机端的代理分流规则包。当前 `v0.1.1` 只做 Shadowrocket 小火箭简化版。

这个项目只提供规则和说明，**不包含任何订阅、节点、账号、密码或 token**。使用者必须先在 Shadowrocket 里导入自己的订阅。

## 核心目标

唯一核心目标：**AI 风控稳定**。

这套规则优先保证：

- Claude 单独走 `Claude`，建议只放美国节点。
- ChatGPT / OpenAI / Gemini / Perplexity / Copilot / Cursor 等走 `AI`，建议美国优先，台湾备用。
- Gemini 先命中 `AI`，不会被普通 Google 规则抢走。
- Google 登录、Gmail、OAuth 走 `Google`。
- YouTube / googlevideo / ytimg 走 `YouTube`。
- OKX / Bybit / Binance 等交易所走 `Exchange`，建议只放台湾、新加坡节点。
- 不启用广告拦截 `REJECT`，减少登录、验证码、支付、风控接口误伤。

## 不解决什么

- 不提供节点，不替代机场订阅。
- 不自动识别节点地区，小火箭做不到 Clash Verge Rev 那种自动补策略组。
- 不保证绕过任何平台的账号地区限制。
- 不做系统级去广告。
- 不追求全网所有站点都代理，未命中规则默认直连。

## 文件

```text
shadowrocket/
  Shadowrocket.conf
  README.md

scripts/
  check-sensitive.sh
  build-release.command
```

## 小火箭快速使用

手机入口页：

```text
https://reroc8.github.io/mobile-proxy-share-kit/
```

最短流程：

1. 在 Shadowrocket 里先导入自己的订阅。
2. 建立或确认这些策略名字存在：`Claude / AI / Google / YouTube / Exchange / Telegram / Proxy`。
3. 把节点放进对应策略：
   - `Claude`：只放美国节点。
   - `AI`：美国节点优先，台湾节点备用。
   - `Exchange`：台湾、新加坡节点。
   - `Google / YouTube / Telegram / Proxy`：放你常用稳定节点。
4. 导入规则：

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/Shadowrocket.conf
```

5. 测试 Claude、ChatGPT/Gemini、Google、YouTube、交易所、国内网站。

## 参考来源

这不是泛用科学上网规则。初版参考了两个方向：

- `blackmatrix7/ios_rule_script`：参考其 OpenAI、Claude、Gemini、Copilot 等专项规则覆盖思路。
- `Hackl0us/SS-Rule-Snippet`：只参考其 Shadowrocket 懒人配置的导入形式。
- `Johnshall/Shadowrocket-ADBlock-Rules-Forever`：只参考其手机入口、二维码和多规则发布说明方式。

本项目没有照搬通用懒人整包，规则目标不同：

- 不使用一个泛用 `Proxy` 承接所有海外服务。
- 不使用广告拦截规则。
- AI 规则放在 Google / YouTube / 通用代理规则前面。
- 最终兜底为 `FINAL,DIRECT`，避免没识别的网站被强行送进普通代理。

## 安全原则

不要提交这些内容：

- 订阅链接
- 节点配置
- 账号、密码、token
- 含有真实节点链接的文件

## 免责声明

这套规则只整理流量路径，不处理平台账号合规问题。AI 服务、交易所、流媒体平台可能有自己的风控和地区限制，使用者需要遵守对应平台规则。
