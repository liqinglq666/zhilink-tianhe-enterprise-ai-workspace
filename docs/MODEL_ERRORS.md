# 模型错误码

模型接口异常统一返回脱敏后的稳定错误结构，避免将供应商原始响应、账户信息或内部网关细节直接暴露给浏览器。

## 普通 API 响应

```json
{
  "detail": "模型接口鉴权失败，请检查 API Key。",
  "code": "MODEL_AUTH_FAILED",
  "retryable": false
}
```

模型限流时还会返回 `Retry-After` 响应头和 `retry_after` 字段。

## 流式 SSE 错误事件

```json
{
  "type": "error",
  "error": "模型服务请求过于频繁，请在 30 秒后重试。",
  "code": "MODEL_RATE_LIMITED",
  "retryable": true,
  "retry_after": 30
}
```

## 错误码说明

| 错误码 | 含义 | 建议操作 |
|---|---|---|
| `MODEL_NOT_CONFIGURED` | API Key、Base URL 或模型名未完整配置 | 补充模型配置 |
| `MODEL_CONFIG_INVALID` | Base URL 格式或安全校验失败 | 检查协议、域名和服务端允许列表 |
| `MODEL_GATEWAY_UNREACHABLE` | 模型网关域名无法解析 | 检查 Base URL 或网络 |
| `MODEL_AUTH_FAILED` | API Key 鉴权失败 | 更换或重新填写 API Key |
| `MODEL_PERMISSION_DENIED` | API Key 无权使用模型 | 检查模型权限和账户配置 |
| `MODEL_RATE_LIMITED` | 模型供应商触发限流 | 按 `retry_after` 等待后重试 |
| `MODEL_REQUEST_REJECTED` | 模型拒绝请求 | 检查模型名、接口路径和输入内容 |
| `MODEL_TIMEOUT` | 连接或生成超时 | 缩短输入或稍后重试 |
| `MODEL_CONNECTION_FAILED` | 无法连接模型服务 | 检查网络和 Base URL |
| `MODEL_REQUEST_FAILED` | 请求发送失败 | 检查网络和模型配置 |
| `MODEL_UNAVAILABLE` | 模型供应商暂时不可用 | 稍后重试 |
| `MODEL_REDIRECT_REJECTED` | 网关返回重定向 | 修正 Base URL |
| `MODEL_BAD_RESPONSE` | 返回内容无法解析或格式不兼容 | 更换兼容模型或网关 |
| `MODEL_EMPTY_RESPONSE` | 模型未返回有效文本 | 重新生成或更换模型 |
| `MODEL_GATEWAY_ERROR` | 网关返回其他异常 | 检查配置或稍后重试 |
| `MODEL_INTERNAL_ERROR` | Agent 处理阶段出现未知异常 | 稍后重试并检查服务日志 |

前端应优先展示 `detail` 或 SSE 的 `error`，并使用 `code` 决定是否引导用户修改配置。只有 `retryable=true` 时才建议用户直接重试。
