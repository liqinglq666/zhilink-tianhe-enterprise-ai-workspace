# 智链天河 · 企业运营 AI 工作台

**ZhiLink Tianhe Enterprise AI Workspace** 是一个面向企业、园区服务窗口和商圈运营团队的 AI 运营工作台，用于把会议记录、合同条款、政策需求、供需信息和实施方案整理成可复核、可保存、可追踪版本、可导出的业务材料。

在线演示：<https://zhilink-tianhe-ai-workspace.onrender.com>

> 在线地址用于作品展示和评审体验。免费实例可能存在冷启动；正式部署请使用持久化 PostgreSQL、HTTPS 和受控模型网关。

## 核心能力

- 企业档案：整理企业背景、阶段和当前需求。
- 会议纪要：生成摘要、决策、待办、负责人和风险提醒。
- 合同审阅：提示付款、交付、违约、知识产权和数据安全等商务风险。
- 政策助手：检索 allowlist 政府 HTTPS 页面，保留官方链接、摘录、状态和检索时间，并明确人工核验边界。
- 供需协作：整理供给、需求、目标对象、合作场景和对接话术。
- 实施计划：生成试点路径、数据范围、复核机制和执行建议。
- 报告归档：导出 Markdown、TXT、DOCX。
- 项目与版本：显式保存、乐观锁、不可变历史、历史恢复。
- 账号与组织：HttpOnly Session、CSRF、组织空间、owner/admin/editor/viewer RBAC。
- 组织知识库：版本、审核、发布、适用范围和引用编号。

## 安全与数据边界

- API Key 不写入项目快照；浏览器自定义 Key 只保存在当前 `sessionStorage`。
- 服务端公共模型必须由部署方显式启用；`OPENAI_API_KEY` 不会自动暴露为公共 Key。
- 模型 Base URL 默认要求 HTTPS，并拒绝本机、内网、保留地址；企业部署可强制 `LLM_ALLOWED_HOSTS`。
- 模型请求设置 completion token 上限，并对最终输出字符数做服务端硬限制。
- 官方政策检索只允许 allowlist HTTPS 政府域名，限制单页响应大小、重定向、并发和 TTL cache 数量。
- 项目、账号、组织、知识库 Schema 由 Alembic 管理；Web 运行时不执行 `create_all` 或 legacy backfill。
- Docker build context 排除 `.env`、`runtime/`、SQLite 数据库和日志文件。
- AI 输出仅作为辅助材料；合同、政策、法律、财务及正式业务结论必须由相应负责人或专业人员复核。

## 技术栈

- Python 3.10+
- FastAPI
- SQLAlchemy 2
- Alembic
- SQLite（本地开发）/ PostgreSQL（正式部署）
- OpenAI-compatible LLM API
- 原生 HTML / CSS / JavaScript V4 工作台
- Docker
- Pytest + GitHub Actions

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # Windows 可手动复制
python scripts/migrate.py
uvicorn backend.main:app --reload
```

打开：<http://127.0.0.1:8000>

运行测试：

```bash
pytest
```

检查数据库 Schema：

```bash
python scripts/check_schema.py
```

## Docker

```bash
docker build -t zhilink-tianhe .
docker run --rm -p 8000:8000 --env-file .env zhilink-tianhe
```

容器启动顺序：

1. `scripts/migrate.py` 升级到 Alembic head；PostgreSQL 使用 advisory lock 串行化迁移。
2. 启动 Uvicorn。
3. Docker healthcheck 同时检查数据库 Schema 和 `/health`。

正式多实例环境更推荐把 migration 做成独立 release/pre-deploy job，再启动 Web replicas。

## 关键环境变量

完整配置见 `.env.example`。常用项：

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/zhilink

PUBLIC_MODEL_ENABLED=false
PUBLIC_MODEL_API_KEY=
PUBLIC_MODEL_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PUBLIC_MODEL_MODEL=qwen-plus

LLM_ALLOWED_HOSTS=dashscope.aliyuncs.com
LLM_REQUIRE_HOST_ALLOWLIST=true
MODEL_MAX_COMPLETION_TOKENS=8192
MODEL_MAX_OUTPUT_CHARS=120000

AUTH_COOKIE_SECURE=true
ENABLE_HSTS=true
TRUST_PROXY_HEADERS=false
```

如果启用 `TRUST_PROXY_HEADERS=true`，必须确保前置反向代理会覆盖并清洗客户端提供的 `X-Forwarded-For`。

## 数据库迁移

项目使用 Alembic 作为唯一 Schema 变更入口：

```bash
python scripts/migrate.py
python scripts/check_schema.py
```

当前迁移包含：

- `20260805_0001`：应用 Schema baseline。
- `20260816_0002`：把旧项目缺失的 baseline history 补齐；该数据迁移不再由 Web Runtime 执行。

不要在生产启动代码中恢复 `Base.metadata.create_all()`。

## 项目结构

```text
backend/                         FastAPI API、账号、项目、知识库、审核与服务流程
src/zhilian_tianhe_agent/       Agent、LLM client、政策检索与业务逻辑
frontend/                       V4 工作台 HTML/CSS/JS
alembic/                        Alembic migrations
scripts/                        migration / schema check
tests/                          API、存储、安全、迁移和 UI contract 测试
```

## 发布检查

发布前至少确认：

```bash
python -m compileall backend src
pytest
python scripts/check_schema.py
```

并检查：

- CI 全绿；
- PostgreSQL migration smoke 通过；
- Docker build 通过；
- 企业部署已配置 HTTPS、Secure Cookie、数据库备份和模型预算；
- 公共 Demo 不包含生产密码、生产 API Key 或真实客户数据。

## 设计原则

1. **不伪造 AI 结果**：模型不可用时返回明确错误。
2. **人工复核优先**：AI 输出不是自动批准的正式结论。
3. **显式持久化**：项目只有用户主动保存才进入数据库。
4. **版本可追踪**：历史版本不可原地改写，恢复会产生新版本。
5. **来源可核验**：政策和知识引用保留具体来源与版本。
6. **最少运行时副作用**：Schema、legacy 数据修复和部署准备不放在普通业务请求路径里。

## License

All rights reserved unless otherwise stated by the repository owner.
