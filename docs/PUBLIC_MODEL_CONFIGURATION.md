# 比赛公共模型与用户自定义 API

## 目标

比赛部署可以在服务端配置一个公共 OpenAI-compatible 模型。评委打开网站后无需填写 API Key 即可生成内容；普通用户仍可在“模型与 API 配置”中填写自己的 Key、Base URL 和模型名称，并仅在当前浏览器会话中覆盖公共模型。

当前比赛默认供应商为阿里云百炼 DashScope，默认模型为 `qwen-plus`。

## 安全边界

- 只有 `PUBLIC_MODEL_ENABLED=true` 且 `PUBLIC_MODEL_*` 完整时，公共模型才会对访客开放。
- `PUBLIC_MODEL_API_KEY` 只存在于 Render 服务端环境变量中。
- 服务端 Key 不会写入 HTML、JavaScript、API 响应、数据库、项目快照或导出报告。
- 当前请求没有用户 Key 时，服务端强制使用 `PUBLIC_MODEL_BASE_URL` 和 `PUBLIC_MODEL_MODEL`，忽略客户端提交的 Base URL 和模型名称，防止公共 Key 被发送到恶意网关。
- 旧的 `OPENAI_API_KEY` 只用于本地脚本或后端私有调用，不会自动成为比赛公共 Key。
- 当前请求包含用户 Key 时，才使用用户填写的兼容接口；该 Key 只保存在浏览器 `sessionStorage` 和当前 HTTP 请求内。
- 所有模型地址继续执行 HTTPS、DNS 和内网地址检查。
- `/api/defaults` 只公开模型是否可用、供应商名称、模型名称和是否允许用户覆盖，不公开 Key 或服务端 Base URL。

## Render 环境变量

在 Render Web Service 的 **Environment** 页面添加：

```text
PUBLIC_MODEL_ENABLED=true
PUBLIC_MODEL_API_KEY=<只在 Render 中粘贴真实 Key，不要提交到 GitHub>
PUBLIC_MODEL_PROVIDER=阿里云百炼 DashScope
PUBLIC_MODEL_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PUBLIC_MODEL_MODEL=qwen-plus
PUBLIC_MODEL_TEMPERATURE=0.35
PUBLIC_MODEL_DAILY_REQUEST_LIMIT=200
ALLOW_USER_API_OVERRIDE=true
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=60
MAX_CONCURRENT_GENERATIONS_PER_CLIENT=1
```

缺少 `PUBLIC_MODEL_ENABLED=true` 时，即使环境中存在 Key，也不会开放给匿名评委使用。真实 Key 必须由项目管理员直接粘贴到 Render Secret 环境变量中，不要发到聊天、邮件正文、Issue 或 PR。

## 用户体验

### 公共模式

API Key 输入框留空，后端确认配置完整后页面显示：

```text
公共模型可用
阿里云百炼 DashScope · qwen-plus
```

生成请求在服务端使用比赛公共模型。浏览器只发送空 Key，不会接收到公共 Key。

### 公共模型未配置

页面显示：

```text
需配置模型
```

用户需要填写自己的 API Key、Base URL 和模型名称。前端不会因为输入框为空就误报公共模型在线。

### 自定义模式

用户填写自己的 API Key、Base URL 和模型名称后，页面状态变为“自定义 API”。清空用户 Key 后，在公共模型可用时恢复公共模式；公共模型未配置时恢复为“需配置模型”。

## 额度与成本

`PUBLIC_MODEL_DAILY_REQUEST_LIMIT` 是进程内请求尝试保险丝：达到上限后返回 `PUBLIC_MODEL_QUOTA_EXHAUSTED`，提示用户填写自己的 API。失败的上游调用也可能占用一次尝试额度。该计数会在 Render 实例重启后重置，也不会跨多个实例共享，因此不能替代供应商侧预算控制。

正式比赛前还应在阿里云控制台确认 Key 地域、`qwen-plus` 权限、余额和费用告警、QPS/TPM 限制，并在比赛结束后轮换或撤销 Key。

## 部署检查

配置环境变量后执行：

```text
Manual Deploy
→ Clear build cache & deploy
```

部署完成后：

1. 使用无痕窗口打开网站；
2. 不填写 API Key；
3. 确认首页显示“公共模型可用”和 `qwen-plus`；
4. 点击“测试当前模型”，确认连接成功；
5. 生成一份简短会议纪要；
6. 填写一个测试用用户 Key，确认状态切换为“自定义 API”；
7. 清空用户 Key，确认可以再次使用公共模式。

## 不要这样做

- 不要把真实 Key 写入 `.env.example`。
- 不要把 Key 写入前端 JavaScript、HTML 或图片。
- 不要在聊天、Issue、PR、日志或截图中发送真实 Key。
- 不要使用 `OPENAI_API_KEY` 代替比赛公共 Key。
- 不要允许空 Key 请求携带任意 Base URL 后再拼接服务端 Key。
