# Mobile Proxy Share Kit

面向手机端的代理分流规则包。当前 `v0.3.0`，只维护两份产物。

两份产物的规则内容都从 PC 版 Clash Verge 的 `Merge.yaml` 生成，不会各走各的。

这个项目只提供规则和说明，**不包含任何订阅、节点、账号、密码或 token**。使用者必须先在客户端里导入自己的订阅。

## 两份产物

| 产物 | 覆盖 | 说明 |
|---|---|---|
| [`karing/`](karing/) | Karing（iOS / Android / Windows / macOS） | 自定义分流组 JSON，推荐 |
| [`shadowrocket/`](shadowrocket/) | Shadowrocket（iOS） | `.conf` 规则文件 |

用 ClashMetaForAndroid / FlClash / Stash / Hiddify 的，建议直接改用 Karing：同样是 sing-box 内核、免费、全平台，规则也能和 PC 版共用同一套逻辑，省一份维护成本。

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

1. 在 Shadowrocket 里先导入自己的订阅。
2. 导入完整骨架模板：

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/Shadowrocket.full.conf
```

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
  build-karing-rules.py             Merge.yaml -> Karing JSON
  build-shadowrocket-rules.py       Merge.yaml -> Shadowrocket .conf
  check-sensitive.sh
  build-release.command

docs/                           GitHub Pages 手机入口页
  index.html
  karing/karing-diversion-rules.json   Pages 同源下载副本，由脚本同步
```

## 规则来源与生成

两份产物都是脚本产物，**不手工维护**，规则源统一是 PC 版 Clash Verge 的 `Merge.yaml`：

```bash
python3 scripts/build-karing-rules.py      [Merge.yaml 路径]   # Karing
python3 scripts/build-shadowrocket-rules.py [Merge.yaml 路径]   # Shadowrocket
```

- 显式 `DOMAIN-SUFFIX` / `DOMAIN` / `DOMAIN-KEYWORD` 直接搬运。
- PC 端靠 `RULE-SET` 表达的宽泛覆盖，两个脚本各自换算：
  Karing 用内置规则集（`geosite:*` / `geoip:*` / `acl:*`），
  Shadowrocket 展开成显式域名（脚本里的 `RULE_SET_EXPANSION`）。
- `PROCESS-NAME`、`IP-CIDR`、`MATCH` 这类搬不过去的，在脚本里显式跳过，不静默丢弃。
- 未登记的规则集、未知策略名、未处理的规则类型、空策略组，都会直接报错退出，
  防止 PC 端改了而这两份产物悄悄落后。

`Shadowrocket` 有三份 `.conf`，`rules.conf` 与 `Shadowrocket.conf` 内容必须逐字节一致，
`build-release.command` 会校验；Karing 的 `karing/` 与 `docs/karing/` 同理。

## 参考来源

这不是泛用科学上网规则。参考了两个方向：

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
