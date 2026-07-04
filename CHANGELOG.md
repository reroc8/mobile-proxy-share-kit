# Changelog

## v0.1.0

- 初版发布 Shadowrocket 小火箭 AI 风控稳定简化规则。
- Claude 独立命中 `Claude`，建议只放美国节点。
- OpenAI / ChatGPT / Gemini / Perplexity / Copilot / Cursor 等 AI 服务命中 `AI`，且 AI 规则放在 Google 规则前。
- 参考 blackmatrix7 的 OpenAI / Claude / Gemini / Copilot 专项规则补充验证码、风控、实时语音和 Gemini 相关域名。
- Google、YouTube、Exchange、Telegram 分开命中独立策略。
- 不启用广告 `REJECT`，避免登录、验证码、支付、风控接口被误伤。
- 未命中规则默认 `FINAL,DIRECT`。
