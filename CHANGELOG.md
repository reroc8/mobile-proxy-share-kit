# Changelog

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
