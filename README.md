<div align="center">

<a href="https://zhilink-tianhe-ai-workspace.onrender.com">
  <img src="docs/assets/zhilink-tianhe-readme-hero.jpg" alt="智链天河 · Enterprise AI Workspace" width="100%" />
</a>

<br />
<br />

# 智链天河 · Enterprise AI Workspace

**把会议、合同、政策与执行，连成一条可落地的 AI 工作链。**

面向企业、园区服务窗口与商圈运营团队的企业级 AI 工作台。  
从信息输入、智能分析、人工复核，到项目执行、版本追踪与报告归档，形成可复核、可追踪、可落地的业务闭环。

<p>
  <a href="https://zhilink-tianhe-ai-workspace.onrender.com"><img src="https://img.shields.io/badge/Live_Demo-在线体验-2563EB?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Live Demo" /></a>
  <a href="https://github.com/liqinglq666/zhilink-tianhe-enterprise-ai-workspace/actions/workflows/ci.yml"><img src="https://github.com/liqinglq666/zhilink-tianhe-enterprise-ai-workspace/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-Production-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-Ready-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
</p>

**[进入在线工作台 →](https://zhilink-tianhe-ai-workspace.onrender.com)**

</div>

> [!NOTE]
> 在线地址用于作品展示与评审体验。免费实例可能存在冷启动；正式企业部署建议使用持久化 PostgreSQL、HTTPS、Secure Cookie、数据库备份与受控模型网关。

---

## Why ZhiLink Tianhe

企业业务真正困难的部分，往往不是“生成一段文字”，而是如何把分散的信息继续推进为 **可核对、可执行、可追踪、可归档** 的业务材料。

智链天河不是六个互相孤立的 AI 小工具，而是一套围绕企业运营过程设计的 **AI Workspace**：

<table>
<tr>
<td width="33%"><b>🧠 智能驱动</b><br/><sub>AI 深度理解会议、合同、政策与业务文本，自动提炼决策、风险、行动项与执行线索。</sub></td>
<td width="33%"><b>🔗 流程贯通</b><br/><sub>从记录与分析，到实施计划、项目版本和报告归档，把一次生成变成连续工作流。</sub></td>
<td width="33%"><b>🛡️ 合规可控</b><br/><sub>人工复核、RBAC、CSRF、审计留痕、版本历史和来源核验共同构成企业级安全边界。</sub></td>
</tr>
</table>

---

## Product Workflow

```mermaid
flowchart LR
    A[企业档案] --> B[会议纪要]
    A --> C[合同审阅]
    A --> D[政策助手]
    A --> E[供需协作]

    B --> F[实施计划]
    C --> F
    D --> F
    E --> F

    F --> G[报告归档]
    G --> H[(项目版本 / 历史恢复)]

    H -. 新一轮业务推进 .-> B

    classDef input fill:#EFF6FF,stroke:#2563EB,color:#0F172A,stroke-width:1.5px;
    classDef ai fill:#ECFEFF,stroke:#06B6D4,color:#0F172A,stroke-width:1.5px;
    classDef action fill:#F0FDF4,stroke:#22C55E,color:#0F172A,stroke-width:1.5px;
    classDef archive fill:#FFF7ED,stroke:#F59E0B,color:#0F172A,stroke-width:1.5px;

    class A input;
    class B,C,D,E ai;
    class F action;
    class G,H archive;
```

**核心设计原则：AI 负责提炼与辅助判断，业务人员负责复核与最终确认；系统负责把确认后的材料持续沉淀为可追踪的项目资产。**

---

## Core Capabilities

| 模块 | 解决什么问题 | 关键输出 |
| --- | --- | --- |
| **企业档案** | 建立统一业务上下文 | 企业背景、阶段、当前需求、组织上下文 |
| **会议纪要** | 把会议记录转成执行信息 | 摘要、关键决策、待办、负责人、时间节点、风险提醒 |
| **合同审阅** | 辅助发现商务与履约风险 | 付款、交付、违约、知识产权、数据安全等风险提示 |
| **政策助手** | 提升政策检索与核验效率 | 官方来源、摘录、状态、检索时间、人工核验边界 |
| **供需协作** | 结构化企业供需与合作机会 | 供给、需求、目标对象、合作场景、对接话术 |
| **实施计划** | 把分析结果继续推进到执行 | 试点路径、数据范围、负责人、节点、复核机制 |
| **报告归档** | 将阶段成果形成正式业务材料 | Markdown / TXT / DOCX、AI 整合报告、归档状态 |
| **项目与版本** | 避免 AI 工作只停留在临时会话 | 显式保存、乐观锁、不可变历史、历史恢复 |
| **账号与组织** | 支持企业多人协作 | HttpOnly Session、CSRF、组织空间、RBAC |
| **组织知识库** | 让组织知识可审核、可引用 | 版本、审核、发布、适用范围、引用编号 |

---

## System Architecture

```mermaid
flowchart TB
    subgraph Client["Frontend · Enterprise Workspace"]
        UI[Vanilla HTML / CSS / JavaScript]
        UX[Structured Results · Review · Export]
        UI --> UX
    end

    subgraph API["Application Layer · FastAPI"]
        ROUTER[API Routes]
        AUTH[Session · CSRF · RBAC]
        PROJECT[Project / History Store]
        WORKFLOW[Service Workflow]
        KNOWLEDGE[Organization Knowledge]
    end

    subgraph AI["AI & Domain Layer"]
        AGENT[Domain Agents]
        QUALITY[Evidence / Quality Guardrails]
        LLM[OpenAI-Compatible LLM Gateway]
        POLICY[Official Policy Fetcher]
    end

    subgraph Data["Persistence Layer"]
        ORM[SQLAlchemy 2]
        MIG[Alembic]
        DB[(SQLite / PostgreSQL)]
    end

    subgraph External["Controlled External Services"]
        MODEL[Model Provider]
        GOV[Allowlisted Government HTTPS Sources]
    end

    UX --> ROUTER
    ROUTER --> AUTH
    ROUTER --> PROJECT
    ROUTER --> WORKFLOW
    ROUTER --> KNOWLEDGE
    ROUTER --> AGENT

    AGENT --> QUALITY
    QUALITY --> LLM
    POLICY --> GOV
    LLM --> MODEL

    PROJECT --> ORM
    WORKFLOW --> ORM
    KNOWLEDGE --> ORM
    AUTH --> ORM
    ORM --> DB
    MIG --> DB
```

### Request lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as 业务用户
    participant UI as Workspace UI
    participant API as FastAPI
    participant Agent as Domain Agent
    participant LLM as Model Gateway
    participant DB as Project Store

    User->>UI: 输入会议 / 合同 / 政策 / 需求材料
    UI->>API: 发起受控请求
    API->>Agent: 注入上下文与业务规则
    Agent->>LLM: 受限模型调用
    LLM-->>Agent: AI 输出
    Agent-->>API: 结构化结果 + 事实边界校验
    API-->>UI: 展示可复核结果
    User->>UI: 人工复核 / 确认
    User->>UI: 显式保存项目
    UI->>API: 保存当前快照
    API->>DB: 新建可追踪版本
    DB-->>UI: 版本号 / 历史记录
```

---

## Security & Data Boundaries

企业 AI 应用的价值不仅来自模型能力，也来自**边界是否清晰**。当前项目重点约束如下：

- **API Key 最小暴露**：Key 不写入项目快照；浏览器自定义 Key 仅保存在当前 `sessionStorage`。
- **公共模型显式启用**：服务端公共模型必须由部署方主动配置；`OPENAI_API_KEY` 不会自动暴露为公共 Key。
- **模型网关约束**：Base URL 默认要求 HTTPS，并拒绝本机、内网与保留地址；企业部署可强制 `LLM_ALLOWED_HOSTS`。
- **模型资源上限**：completion token、最终输出字符、原始响应字节和流式总时长均有上限。
- **官方政策来源控制**：政策检索仅允许 allowlist HTTPS 政府域名，并限制响应大小、重定向、并发和 TTL cache。
- **组织权限模型**：owner / admin / editor / viewer RBAC，关键写操作在数据库事务内重新校验当前权限。
- **项目版本一致性**：显式保存、乐观锁、不可变历史；恢复历史会产生新版本而非覆盖旧记录。
- **Schema 单一入口**：项目、账号、组织、知识库 Schema 统一由 Alembic 管理，Web Runtime 不执行 `create_all`。
- **容器敏感文件隔离**：Docker build context 排除 `.env`、`runtime/`、SQLite 数据库与日志。
- **人工复核优先**：合同、政策、法律、财务和正式业务结论必须由相应负责人或专业人员复核。

> [!IMPORTANT]
> 智链天河定位为 **AI 辅助工作台**，不是自动审批系统。AI 输出可以加速整理、判断与协作，但不能替代授权人员作出正式法律、财务、政策或经营决策。

---

## Technology Stack

<div align="center">

| Layer | Technology |
| --- | --- |
| **Frontend** | Native HTML · CSS · JavaScript · Responsive SaaS Workspace |
| **Backend** | Python 3.10+ · FastAPI · Pydantic |
| **AI Layer** | Domain Agents · OpenAI-Compatible API · Evidence Guardrails |
| **Persistence** | SQLAlchemy 2 · Alembic · SQLite / PostgreSQL |
| **Security** | HttpOnly Session · CSRF · RBAC · Controlled Model Gateway |
| **Delivery** | Docker · GitHub Actions · Production Browser Acceptance |
| **Testing** | Pytest · PostgreSQL Migration Smoke · Headless Chrome |

</div>

---

## Repository Structure

```text
zhilink-tianhe-enterprise-ai-workspace/
├── backend/                      # FastAPI API、账号、项目、知识库、审核与服务流程
├── frontend/                     # 企业工作台 HTML / CSS / JavaScript
│   └── assets/                   # 模块化前端逻辑与视觉资源
├── src/zhilian_tianhe_agent/     # Agent、LLM client、政策检索与业务质量控制
├── alembic/                      # 数据库版本迁移
├── scripts/                      # migration / schema / release utilities
├── tests/                        # API、存储、安全、迁移、前端与浏览器回归测试
├── docs/                         # 设计说明与品牌资源
├── Dockerfile                    # Production container
└── README.md
```

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/liqinglq666/zhilink-tianhe-enterprise-ai-workspace.git
cd zhilink-tianhe-enterprise-ai-workspace
```

### 2. Create environment

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
```

### 3. Configure

```bash
cp .env.example .env
# Windows 可手动复制 .env.example 为 .env
```

### 4. Migrate database

```bash
python scripts/migrate.py
python scripts/check_schema.py
```

### 5. Run

```bash
uvicorn backend.main:app --reload
```

Open: **http://127.0.0.1:8000**

### 6. Test

```bash
pytest
```

> `requirements.txt` 仅包含生产依赖；`requirements-dev.txt` 在此基础上增加测试依赖。

---

## Docker Deployment

```bash
docker build -t zhilink-tianhe .
docker run --rm -p 8000:8000 --env-file .env zhilink-tianhe
```

容器启动流程：

```mermaid
flowchart LR
    A[Container Start] --> B[Alembic Migration]
    B --> C{Schema Ready?}
    C -- No --> D[Fail Fast]
    C -- Yes --> E[Start Uvicorn]
    E --> F[Healthcheck]
    F --> G[Web Ready]
```

PostgreSQL 环境下 migration 使用 advisory lock 串行化。正式多实例环境更推荐将 migration 作为独立 release / pre-deploy job，再启动 Web replicas。

---

## Key Environment Variables

完整配置请查看 `.env.example`。常用生产配置示例：

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
MODEL_MAX_RESPONSE_BYTES=960000
MODEL_MAX_STREAM_SECONDS=180

AUTH_COOKIE_SECURE=true
ENABLE_HSTS=true
TRUST_PROXY_HEADERS=false
```

如果启用 `TRUST_PROXY_HEADERS=true`，必须确保前置反向代理会覆盖并清洗客户端提供的 `X-Forwarded-For`。

---

## Engineering Quality

当前 CI 不只验证“代码能不能启动”，而是覆盖从迁移到真实浏览器的生产链路：

```mermaid
flowchart LR
    A[Push / Pull Request] --> B[Python 3.10]
    A --> C[Python 3.11]
    A --> D[Python 3.12]
    A --> E[PostgreSQL Migration Smoke]

    B --> F[Complete Pytest Suite]
    C --> F
    D --> F
    E --> G[Production Docker Build]
    F --> G
    G --> H[Runtime Verification]
    H --> I[Real Chrome Acceptance]
```

发布前至少确认：

```bash
python -m compileall backend src
pytest
python scripts/check_schema.py
```

并检查：

- CI 全绿；
- PostgreSQL migration smoke 通过；
- Production Docker build 通过；
- 真实浏览器 acceptance 通过；
- 企业部署已配置 HTTPS、Secure Cookie、数据库备份和模型预算；
- 公共 Demo 不包含生产密码、生产 API Key 或真实客户数据。

---

## Design Principles

1. **No Fake AI** — 模型不可用时返回明确错误，不伪造成功结果。
2. **Human in the Loop** — AI 输出默认需要人工复核，避免将生成内容误当成正式批准。
3. **Explicit Persistence** — 只有用户主动保存，当前项目状态才进入数据库版本。
4. **Traceable History** — 历史版本不可原地改写，恢复操作产生新版本。
5. **Verifiable Sources** — 政策与知识引用保留具体来源、版本和核验上下文。
6. **Least Runtime Side Effects** — Schema 与 legacy 数据修复不进入普通业务请求路径。
7. **Authorization at the Transaction Boundary** — 关键组织与流程写操作在事务内使用当前真实权限执行。

---

## Online Demo

<div align="center">

### [🚀 打开智链天河 Enterprise AI Workspace](https://zhilink-tianhe-ai-workspace.onrender.com)

点击 README 顶部品牌横幅，也可以直接进入在线工作台。

<sub>Demo 环境用于展示与评审。正式生产环境请配置独立数据库、HTTPS、备份策略与受控模型服务。</sub>

</div>

---

## License

All rights reserved unless otherwise stated by the repository owner.

---

<div align="center">

**智链天河 · ZhiLink Tianhe**  
*Enterprise AI Workspace*

**让企业 AI 从“生成内容”，走向“推进业务”。**

</div>