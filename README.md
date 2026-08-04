# 智链天河 · 企业运营 AI 工作台

> 面向天河区企业、商圈、园区与企业服务窗口的轻量化 AI 运营工作台。

本项目通过 OpenAI-compatible 模型接口，提供企业档案、会议纪要、合同商务风险提示、政策准备、供需协作、实施计划与报告归档能力。系统不提供伪造的本地 AI 结果；涉及模型生成的业务模块必须由用户配置可用的 API Key、Base URL 和模型名称。

## 核心能力

- 企业档案：整理企业背景、需求、服务重点与行动建议
- 会议纪要：提取摘要、决策、待办、负责人和时间节点
- 合同审阅：识别付款、交付、知识产权、数据安全和违约等商务风险
- 政策准备：根据企业情况生成政策方向和材料准备建议
- 供需协作：整理供给、需求、目标对象和对接方案
- 实施计划：生成试点范围、角色、数据边界、部署方式和复核机制
- 报告归档：汇总结果并导出 Markdown、TXT 或 Word 文档

## 技术架构

- 前端：原生 HTML、CSS、JavaScript
- 后端：FastAPI、Pydantic
- 模型调用：OpenAI-compatible `/chat/completions`
- 文档导出：python-docx
- 默认存储：浏览器会话存储；后端不持久化 API Key 和业务原文

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

浏览器访问 `http://localhost:8000`。

## Docker

```bash
docker compose up --build
```

## 环境配置

复制 `.env.example` 并按部署环境调整。主要配置包括：

```env
MAX_BODY_BYTES=1500000
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60
MAX_CONCURRENT_GENERATIONS_PER_CLIENT=1
MODEL_REQUEST_TIMEOUT_SECONDS=120
MODEL_TEST_TIMEOUT_SECONDS=20
TRUST_PROXY_HEADERS=false
CORS_ALLOW_ORIGINS=
ALLOW_WILDCARD_CORS=false
ENABLE_HSTS=false
HSTS_MAX_AGE=31536000
```

### 生成取消与超时

流式生成期间，结果区域会显示“停止生成”按钮。浏览器端默认采用：

- 30 秒连接超时
- 120 秒无新输出超时；只要模型持续输出就会重新计时
- 10 分钟单次生成硬上限

用户取消或超时后，已经接收的部分内容只在当前结果区域临时展示，不会写入正式结果、最近材料或汇总报告。服务端会关闭上游流并释放该客户端的生成并发槽。

业务模型请求的服务端超时由 `MODEL_REQUEST_TIMEOUT_SECONDS` 控制，允许范围为 10–600 秒；模型连接测试由 `MODEL_TEST_TIMEOUT_SECONDS` 控制，允许范围为 5–120 秒。

### CORS 与安全头

同域部署不需要 CORS，默认保持 `CORS_ALLOW_ORIGINS` 为空。前后端分离时，只填写明确允许的来源；默认禁止 `*` 通配符。

应用默认发送 CSP、`nosniff`、点击劫持保护、Referrer Policy、Permissions Policy 和缓存控制等安全响应头。只有正式 HTTPS 域名稳定后才应启用 HSTS。

### 代理来源 IP

只有部署在会覆盖并清洗 `X-Forwarded-For` 的可信反向代理后，才可设置：

```env
TRUST_PROXY_HEADERS=true
```

否则保持默认 `false`，避免客户端伪造 IP 绕过限流。

## 模型错误契约

普通接口和流式接口会返回稳定、脱敏的模型错误码，不会向浏览器暴露模型供应商原始错误正文。详见：

```text
docs/MODEL_ERRORS.md
```

## 数据与隐私边界

- API Key 仅保存在当前浏览器会话，并随请求发送给后端
- 后端仅在当前请求内使用 API Key，不写入日志、数据库、文件或导出文档
- 用户主动点击生成后，输入文本会发送到所配置的模型服务商
- 默认不在后端持久化合同、会议记录、企业资料和模型输出
- AI 结果属于辅助材料，不替代法律、财务、政策申报等专业意见
- 合同、政策和正式业务材料必须经过对应专业人员复核

## 测试

```bash
pytest -q
```

仓库测试覆盖 API 基础行为、请求体限制、限流与并发保护、模型网关安全、错误分类、安全响应头、流式错误以及生成取消后的资源释放。
