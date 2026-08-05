# 比赛公共模型与用户自定义 API

## 目标

比赛部署可以在服务端配置一个公共 OpenAI-compatible 模型。评委打开网站后无需填写 API Key 即可生成内容；普通用户仍可在“模型与 API 配置”中填写自己的 Key、Base URL 和模型名称，并仅在当前浏览器会话中覆盖公共模型。

## 安全边界

- `PUBLIC_MODEL_API_KEY` 只存在于 Render 服务端环境变量中。
- 服务端 Key 不会写入 HTML、JavaScript、API 响应、数据库、项目快照或导出报告。
- 当前请求没有用户 Key 时，服务端会强制使用 `PUBLIC_MODEL_BASE_URL` 和 `PUBLIC_MODEL_MODEL`，忽略客户端提交的 Base URL 和模型名称，防止公共 Key 被发送到恶意网关。
- 当前请求包含用户 Key 时，才使用用户填写的兼容接口；该 Key 只保存在浏览器 `sessionStorage` 和当前 HTTP 请求内。
- 所有模型地址继续执行 HTTPS、DNS 和内网地址检查。

## Render 环境变量

在 Render Web Service 的 **Environment** 页面添加：

```text
PUBLIC_MODEL_API_KEY=<在 Render 中粘贴真实 Key，不要提交到 GitHub>
PUBLIC_MODEL_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PUBLIC_MODEL_MODEL=qwen-plus
PUBLIC_MODEL_TEMPERATURE=0.35
PUBLIC_MODEL_DAILY_REQUEST_LIMIT=200
ALLOW_USER_API_OVERRIDE=true
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=60
MAX_CONCURRENT_GENERATIONS_PER_CLIENT=1
```

阿里云百炼 / DashScope 使用上面的 Base URL。其他 OpenAI-compatible 提供商只需要替换服务端 Base URL、模型名称和 Key。

## 用户体验

### 公共模式

API Key 输入框留空：

```text
公共模型可用
```

生成请求在服务端使用比赛公共模型。浏览器只发送空 Key，不会接收到公共 Key。

### 自定义模式

用户填写自己的：

```text
API Key
Base URL
模型名称
```

页面状态变为：

```text
自定义 API
```

清空用户 Key 后自动恢复公共模式。

## 额度与成本

`PUBLIC_MODEL_DAILY_REQUEST_LIMIT` 是进程内保险丝：达到上限后返回 `PUBLIC_MODEL_QUOTA_EXHAUSTED`，提示用户填写自己的 API。该计数会在 Render 实例重启后重置，也不会跨多个实例共享，因此不能替代供应商侧预算控制。

正式比赛前还应在模型供应商控制台配置：

- 日消费额度或余额上限；
- 费用告警；
- 单 Key QPS / TPM 限制；
- 只允许所需模型；
- 比赛结束后轮换或撤销 Key。

## 部署检查

配置环境变量后执行：

```text
Manual Deploy
→ Clear build cache & deploy
```

部署完成后：

1. 使用无痕窗口打开网站；
2. 不填写 API Key；
3. 点击“测试当前模型”；
4. 确认连接成功；
5. 生成一份简短会议纪要；
6. 填写一个测试用用户 Key，确认状态切换为“自定义 API”；
7. 点击“恢复公共模型”，确认可以再次使用公共模式。

## 不要这样做

- 不要把真实 Key 写入 `.env.example`。
- 不要把 Key 写入前端 JavaScript、HTML 或图片。
- 不要在聊天、Issue、PR、日志或截图中发送真实 Key。
- 不要允许空 Key 请求携带任意 Base URL 后再拼接服务端 Key。
