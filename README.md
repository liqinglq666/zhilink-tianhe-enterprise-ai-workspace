# 智链天河

面向中小企业和园区服务场景的文档处理工作台。项目将企业档案、会议记录、合同条款、政策需求和供需信息整理成结构化结果，并支持 Markdown、TXT 和 DOCX 导出。

在线地址：<https://zhilink-tianhe-ai-workspace.onrender.com>

Render 免费实例长时间无人访问后会休眠，首次打开可能需要等待冷启动。

## 功能

- 企业档案整理
- 会议纪要与待办提取
- 合同商务风险提示
- 政策方向与材料清单整理
- 供需信息结构化
- 实施计划生成
- 单模块及综合报告导出
- 流式输出

合同审阅和政策建议仅供内部整理与人工复核，不构成法律或政策申报意见。

## 使用模型接口

服务端不保存公共模型密钥。使用者需要在页面中填写：

```text
API Key
Base URL
Model
```

接口需兼容 OpenAI Chat Completions。自定义地址必须使用 HTTPS，且不能指向回环、内网或保留地址。

## 本地运行

### Python

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
```

macOS / Linux：

```bash
source .venv/bin/activate
```

安装并启动：

```bash
python -m pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

健康检查：

```text
GET /health
```

### Docker

```bash
docker build -t zhilink-tianhe .
docker run --rm -p 8000:8000 zhilink-tianhe
```

## API

主要接口：

```text
GET  /health
GET  /api/defaults
POST /api/test-connection
POST /api/profile
POST /api/meeting
POST /api/contract
POST /api/policy
POST /api/match
POST /api/landing
POST /api/report
POST /api/report/markdown
POST /api/report/txt
POST /api/report/docx
```

带 `/stream` 后缀的接口返回 Server-Sent Events。

请求体默认限制为约 1.5 MB，可通过 `MAX_BODY_BYTES` 调整。服务会按实际接收字节数执行限制，不只依赖 `Content-Length`。

## 目录

```text
.
├── backend/                 # FastAPI API、Schema 和导出逻辑
├── frontend/                # 单页前端与静态资源
├── src/zhilian_tianhe_agent/
│   ├── agents.py            # 各业务模块
│   ├── constants.py
│   └── llm_client.py        # OpenAI-compatible 客户端
├── tests/
├── Dockerfile
├── render.yaml
└── requirements.txt
```

## 安全说明

- API Key 不应写入源码或提交到仓库。
- 面向正式业务部署时应增加登录、权限、审计和数据留存策略。
- 合同、会议和企业材料可能包含敏感信息，提交前应完成脱敏。
- CORS、请求体上限和模型网关白名单应按部署环境配置。

## 测试

```bash
python -m pytest
```

## License

本项目保留全部权利，具体见仓库许可文件。
