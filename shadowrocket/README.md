# Shadowrocket 小火箭 AI 风控稳定规则

当前版本：`v0.2.11`

## 适合谁

- 已经在 iPhone / iPad 上使用 Shadowrocket。
- 已经有自己的订阅和节点。
- 主要想让 Claude、ChatGPT、Gemini 这类 AI 服务走更稳定的线路。
- 可以手动把节点放到几个策略组里。

## 规则从哪来

三份 `.conf` 都由 `scripts/build-shadowrocket-rules.py` 从 PC 版仓库的 GitHub 源码生成，**不要手改**。

结构是**混合**的：

- **Claude / AI 两个组手写域名** —— 这两块我们比公开规则集更全（`Claude.list` 只有 10 行，我们 11 条；OpenAI + Gemini 合计 66 行，我们 AI 组 93 条），而且是我们自己的价值所在，保持可审计。
- **Google / YouTube / Telegram / Exchange 四个组引用远程规则集**（`RULE-SET`，源是 `blackmatrix7/ios_rule_script`）。手写追不上：Google 16 → 708 条、YouTube 10 → 199、Telegram 12 → 50、交易所 26 → 209。小火箭原生支持这个，官方推荐配置也是这么写的。
- **`Banks` / `Brokers` 引用规则集**（LingJingMaster 的，blackmatrix7 没有金融类）。
- **`CN` 和 `Proxy` 各加了两层兜底**：`China.list` + `China_Domain.list`（3699 条）把国内域名逐条兜住；`Global.list` + `Global_Domain.list`（**34922 条**）把海外域名兜住。纯域名列表用 `DOMAIN-SET`，带类型的用 `RULE-SET`。

加了这几层之后，**实际覆盖从约 1550 条涨到约 38000 条** —— 只看文件行数会觉得少（175 行），因为绝大多数规则藏在十几条规则集引用后面。

规则集是**远程依赖**：在「配置 → 配置文件 → 编辑配置 → 规则集 URL」里可以看到加载状态。拉不到时那几行会失效，流量落到 `FINAL,Proxy` 兜底，不会断网。

PC 靠 `RULE-SET` 表达、Shadowrocket 没有等价写法的部分，在脚本里展开成显式域名（脚本里的 `RULE_SET_EXPANSION`），逐条标注了对应哪个 PC 规则集。

## 一键导入

有三条路，按你用哪台设备挑一条。

**① 已经在手机上** —— 用 Safari 打开手机操作页，点「一键导入」：

```text
https://reroc8.github.io/mobile-proxy-share-kit/import.html
```

**② 在电脑上看页面** —— 打开手机上的 Shadowrocket → 首页右上角扫码 → 扫入口页上那张二维码。
它直接编码了配置地址，扫完就下载并启用。

```text
shadowrocket://config/add/https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/%E6%98%9F%E5%90%9B%E5%88%86%E6%B5%81.conf
```

**③ 上面都不行** —— 手动四步：复制模板链接 → Shadowrocket「配置」→ 右上角 `+` → 粘贴 → 下载 →
在远程文件里点它选「使用配置」→ 回首页把「全局路由」改成「配置」。

### 几个容易踩的点

- **必须用 Shadowrocket 自带的扫码**，不能用 iOS 系统相机。系统相机的二维码动作类型是固定的
  一组（http/https、tel、mailto、sms、geo、vCard、iCalendar、Wi-Fi），不认 `shadowrocket://`，
  扫出来只会是一段文本。App 内扫码才认。
- **`shadowrocket://` 链接只能在 Safari 里点**，电脑浏览器、微信内置浏览器都不会有反应。
- 这个 scheme 形式不是官方开发者文档里的，来源是同类规则项目的实际做法
  （`Johnshall/Shadowrocket-ADBlock-Rules-Forever` 的二维码解码出来就是同样的
  `shadowrocket://config/add/https://...`）。所以手动路径一直保留着。

## 手动导入（一键失败时用）

1. 复制模板链接（见下面「推荐使用方式」）。
2. Shadowrocket →「配置」→ 右上角 `+` → 粘贴链接 → 下载。
3. 在「远程文件」里点它 →「使用配置」。
4. 回首页，把「全局路由」改成「配置」。

## 推荐使用方式

小白优先导入完整骨架模板：

```text
https://raw.githubusercontent.com/reroc8/mobile-proxy-share-kit/main/shadowrocket/%E6%98%9F%E5%90%9B%E5%88%86%E6%B5%81.conf
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
| `US` | **自动筛**美国节点（不用手动放） |
| `SG` | **自动筛**新加坡节点 |
| `HK` | **自动筛**香港节点 |
| `CN` | 国内流量，默认直连 |
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

这个旧链接会继续保留，内容与 `Shadowrocket.rules.conf` 完全一致。新用户建议优先用 `星君分流.conf`。

手机入口页：

```text
https://reroc8.github.io/mobile-proxy-share-kit/
```

## 地区组是自动的

`US` / `SG` / `HK` 三个组用 `policy-regex-filter` 按节点名里的地区字样**自动收节点**，你不需要手动往里拖：

```
US = url-test,url=http://www.gstatic.com/generate_204,interval=600,tolerance=0,timeout=5,policy-regex-filter=🇺🇸|美国|美國|United States|洛杉矶|圣何塞|西雅图|芝加哥|纽约|达拉斯|凤凰城|硅谷
```

**只认旗帜 emoji、中文、英文全称和城市名，刻意不收 `US` / `SG` / `HK` 这类两字母缩写。**

缩写不可靠：节点叫「🇺🇸 美国 SG 中转」时，加词边界也挡不住那个独立的 `SG`，美国节点会被
收进 SG 组 —— 这正是踩过的坑（SG 组里混进了 2 个美国节点）。收窄的代价是「US 01」这种
纯缩写命名不进地区组，但它们仍在 `Proxy` 组里，手动选得到。选错国家比选不到严重得多。

`policy-select-name` 给业务组设默认出口，例如
`Claude = select,US,Proxy,CN,policy-select-name=US` —— 导入后 Claude 直接走美国组。

`CN` 组默认 `DIRECT`。国内流量不直接写 `DIRECT` 而是走这个组，是为了判定出错时能一键切走。

## 规则顺序

1. 局域网和本机地址直连（`Rule` 段开头，固定不动）。
2. Claude 命中 `Claude`。
3. OpenAI / Gemini / Copilot / Cursor 等 AI 服务命中 `AI`。
4. YouTube 命中 `YouTube`。
5. Google 登录和 Gmail 命中 `Google`。
6. 交易所命中 `Exchange`。
7. Telegram 命中 `Telegram`。
8. `US` / `SG` 对应的地区锁定站点。
9. 国内 AI 服务、钉钉、腾讯系，以及国内常见网站直连。
10. 明确海外常见服务命中 `Proxy`。
11. 中国大陆 IP 直连。
12. 未命中规则走 `Proxy`（**兜底走代理，不是直连**，理由见下）。

顺序不能乱，有两条硬要求：

**1. `YouTube` 必须排在 `Google` 前面。** 否则 `youtubei.googleapis.com` 会被 `googleapis.com` 抢走，永远进不了 `YouTube`。

**2. 所有精确策略必须排在国内直连和 `Proxy` 前面。** PC 版里有 `tgalileo.com` 这种「在 cn 域名库里、但要走代理」的域名，靠精确规则前置才能改走代理。国内直连一旦提前就会把它判成直连，和 PC 的意图正好相反。

这份顺序和 `karing/` 那份完全一致，两个客户端行为一样。

## 与 PC 版的差异

| PC 版 | Shadowrocket 上怎么处理 |
|---|---|
| `RULE-SET,google` | 也改用远程规则集 `Google.list`（708 条），不再展开 |
| `RULE-SET,cn-domain` / `applications` | 展开成显式国内站点，另有 `DOMAIN-SUFFIX,cn` 和 `DOMAIN-KEYWORD,-cn`，末尾还有 `GEOIP,CN,DIRECT` |
| `RULE-SET,global-domain` / `tld-proxy` | 展开成显式海外站点 |
| `RULE-SET,cn-ip` / `private-ip` | 由 `GEOIP,CN,DIRECT` 和开头的 `IP-CIDR` 覆盖 |
| `RULE-SET,apple` / `icloud` | 不单列；Apple 域名按 IP 归属走（国内 CDN 直连、海外走代理） |
| 银行 / 券商 | **手机端独有**，PC 版没有这两组 |
| `PROCESS-NAME-REGEX` 进程级规则（钉钉、Muse） | 小火箭没有进程名匹配，不预置 |
| 交易所分组 | **手机端独有**，PC 版没有这块业务 |

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
