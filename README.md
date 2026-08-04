<div align="center">

# 智链天河 · 企业运营 AI 工作台

### ZhiLink Tianhe Enterprise AI Workspace

**面向企业、园区服务窗口、商圈运营团队与中小经营主体的 AI 运营材料生成、复核、流转与归档平台**

<br/>

## 🎨 立即访问在线演示

<p>
  <a href="https://zhilink-tianhe-ai-workspace.onrender.com" target="_blank">
    <img src="frontend/assets/hero-enterprise-ai.png" alt="点击访问智链天河在线演示" width="92%" />
  </a>
</p>

### 👆 点击上方图片即可访问在线演示

<p>
  <a href="https://zhilink-tianhe-ai-workspace.onrender.com" target="_blank">
    <img src="https://img.shields.io/badge/立即体验-ZhiLink_Tianhe_AI_Workspace-2563EB?style=for-the-badge&logo=render&logoColor=white" alt="立即体验" />
  </a>
  <a href="https://github.com/liqinglq666/zhilink-tianhe-enterprise-ai-workspace" target="_blank">
    <img src="https://img.shields.io/badge/GitHub-项目仓库-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Repository" />
  </a>
</p>

<p>
  🌐 在线体验地址：
  <a href="https://zhilink-tianhe-ai-workspace.onrender.com"><b>https://zhilink-tianhe-ai-workspace.onrender.com</b></a>
</p>

<p>
  <b>体验功能：</b>
  企业档案 → 会议纪要 → 合同审阅 → 政策准备 → 供需协作 → 实施计划 → 报告归档 · 支持流式生成
</p>

<br/>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Enterprise_Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![OpenAI Compatible](https://img.shields.io/badge/LLM-OpenAI_Compatible-412991?style=for-the-badge)
![DashScope](https://img.shields.io/badge/DashScope-Qwen_Ready-1E64FF?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Deployable-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-All_Rights_Reserved-black?style=for-the-badge)

</div>

---

## 在线 Demo 说明

当前在线体验版本部署在 **Render 免费实例** 上，主要用于作品展示、功能演示和评审体验。由于免费实例存在平台限制，网页在长时间无人访问后可能进入休眠状态，首次打开时可能出现几十秒冷启动等待，这是免费部署环境的正常现象，不代表系统不可用。

为控制演示成本，当前 Demo 采用轻量化部署方式：

- 不在服务端内置或保存大模型 API Key；
- 使用者需在网页左侧自行填写 OpenAI-Compatible API Key；
- API Key 默认仅保存在浏览器当前会话中；
- 业务文本和生成结果默认保存在浏览器会话，只有用户主动点击“新建并保存”或“保存当前项目”时才写入配置的项目数据库；
- 项目可保存在匿名浏览器工作区，也可登录后迁移到受 RBAC 保护的组织空间；
- Render 免费实例等无持久磁盘环境不能依赖本地 SQLite 长期保存项目、账号或版本历史，在线部署应配置 PostgreSQL 或持久磁盘；
- 当前版本主要用于功能验证、场景演示和产品原型展示。

项目存储与账号权限边界见：

- [`docs/PROJECT_STORAGE.md`](docs/PROJECT_STORAGE.md)
- [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md)
- [`docs/AUTH_RBAC.md`](docs/AUTH_RBAC.md)

> 说明：项目快照和版本历史不会保存模型 API Key、Base URL、模型名称或生成温度。

### 面向企业正式部署的建议方案

如果后续面向园区、商圈、企业服务窗口或具体企业客户正式使用，建议从“免费 Demo 部署”升级为“企业级生产部署”：

| 方向 | 建议措施 |
|---|---|
| 部署环境 | 使用云服务器、企业内网服务器、容器平台或专属 PaaS，避免免费实例休眠 |
| 访问稳定性 | 采用付费实例、自动扩缩容、健康检查、服务监控和异常告警 |
| 域名与安全 | 绑定企业专属域名，启用 HTTPS、同源反向代理、Secure Cookie、访问控制和安全网关 |
| 模型接口 | 接入企业统一大模型网关，或由企业集中配置模型 API Key |
| 用户权限 | 使用账号、组织空间和 RBAC，并继续补充邮箱验证、密码重置和审计日志 |
| 数据治理 | 增加数据脱敏、敏感字段过滤、日志分级、数据留存周期和删除机制 |
| 结果归档 | 使用 PostgreSQL、持久磁盘或对象存储，支持项目、历史报告、服务台账和版本追踪 |
| 运维保障 | 增加备份策略、数据库迁移、部署流水线、监控面板和故障恢复方案 |

因此，当前在线地址可以理解为 **公开演示版 / Demo Deployment**；正式企业落地时，可升级为 **私有化部署 / 专属云部署 / 企业内网部署**，以满足稳定性、安全性、权限管理和数据合规要求。

---

## 0. Executive Summary

**智链天河 · 企业运营 AI 工作台** 不是一个普通的 AI 聊天页面，而是一套围绕企业运营材料生产链路设计的轻量级 AI 工作台。

系统以真实企业运营事项为中心，将会议记录、合同条款、政策诉求、供需信息与实施方案等非结构化材料转化为可复核、可流转、可归档的结构化业务文档，帮助企业和服务人员降低材料整理成本，提高协同效率，并形成标准化服务台账。

> 一句话：  
> **把企业日常运营中的“杂乱文本、临时沟通、模糊需求”转化为“结构化材料、风险提示、行动清单和可归档报告”。**

---

## 1. Product Vision

在企业、园区和商圈日常运营中，很多工作并不缺信息，而是缺少把信息快速整理成标准材料的能力：

- 会议结束后，没人及时整理纪要和待办；
- 合同合作频繁，但风险条款难以及时识别；
- 政策信息很多，但企业不知道如何理解和准备材料；
- 企业、商户、服务商之间有供需，却缺少标准化表达；
- AI 应用场景想法很多，但难以转化为试点方案；
- 生成的材料分散在聊天记录、文档、邮件里，难以归档复用。

本项目将这些高频运营场景封装为一套企业级 AI 工作台：

```mermaid
mindmap
  root((企业运营 AI 工作台))
    业务材料生成
      会议纪要
      合同风险提示
      政策准备
      供需协作
      实施计划
    运营协同
      任务拆解
      对接话术
      材料清单
      行动建议
    风险治理
      数据脱敏
      人工复核
      API Key 不持久化
      合同法律边界
    输出归档
      单模块导出
      综合报告
      Word 文档
      Markdown
      TXT
```

---

## 2. Core Value Proposition

| 维度 | 传统方式 | 智链天河工作台 |
|---|---|---|
| 会议处理 | 人工整理，容易遗漏 | 自动生成摘要、决策、待办、负责人和时间节点 |
| 合同审阅 | 完全依赖人工经验 | 快速识别付款、交付、违约、知识产权、数据安全等商务风险 |
| 政策准备 | 信息分散，难以判断 | 根据企业需求输出政策方向、材料清单和注意事项 |
| 供需协作 | 需求表达不标准 | 自动形成供需标签、合作建议和对接话术 |
| 实施计划 | 想法难以落地 | 生成试点路径、数据边界、复核机制和评估指标 |
| 文档归档 | 材料分散，难复用 | 支持单模块和综合报告多格式导出 |

---

## 3. Feature Highlights

### 3.1 企业级首页 Hero

- 内置专业视觉图 `frontend/assets/hero-enterprise-ai.png`
- 用于展示企业 AI 工作台定位
- 适合作为 GitHub README、项目首页、路演演示和在线 Demo 首页视觉

### 3.2 轻量身份入口

支持设置当前使用身份：

- 单位 / 团队名称
- 使用角色
- 联系人 / 备注

角色包括：

```text
企业用户 / 园区服务人员 / 商圈运营人员 / 项目管理员
```

该轻量业务身份与正式登录账号分离：业务身份进入项目材料，登录账号和组织角色用于访问控制。

### 3.3 API 必填与用户自主管理

系统不内置 API Key，也不提供本地规则假生成。  
所有正式业务结果都需要使用者自行配置模型接口：

- DashScope / 通义千问
- OpenAI 官方接口
- DeepSeek / 火山方舟 / 硅基流动等兼容接口
- 企业私有化模型网关

### 3.4 天河场景快速填入

每个模块内置典型天河区企业服务场景，一键填入表单，便于体验者快速理解系统能力。

| 模块 | 示例一 | 示例二 |
|---|---|---|
| 企业档案 | 天河路商圈运营团队 | 天河CBD专业服务企业 |
| 会议纪要 | 商圈活动筹备会 | CBD企业服务例会 |
| 合同审阅 | 商户联动协议 | AI服务采购条款 |
| 政策准备 | AI应用场景与大模型政策 | 商圈促消费与数字化经营 |
| 供需协作 | 商圈找 AI 服务商 | CBD 企业找专业服务 |
| 实施计划 | 商圈 AI 运营试点 | 企业服务窗口试点 |

### 3.5 单模块多格式导出

每个模块生成后，无需进入报告归档，即可独立导出：

```text
Markdown / TXT / Word DOCX
```

### 3.6 综合报告归档

多个模块结果可统一汇总为企业运营报告，用于：

- 内部流转
- 服务台账
- 项目复盘
- 客户沟通
- 政策材料整理
- 企业数字化服务记录

### 3.7 显式项目存储与版本历史

页面顶部的“项目”入口支持创建、保存、打开、归档、恢复和删除项目。默认不会在输入过程中静默上传，只有用户主动保存时才把业务表单和生成结果写入 SQLite 或 PostgreSQL。

- 每次有效保存生成不可变版本；
- `lock_version` 防止多页面覆盖；
- 历史恢复会生成新版本，不改写已有记录；
- 模型 API Key 和接口配置不进入项目快照或历史。

### 3.8 账号、组织空间与 RBAC

- 支持邮箱密码注册和登录；
- 会话令牌使用 HttpOnly Cookie，密码使用带随机盐的 scrypt 哈希；
- 组织写操作需要 CSRF 令牌；
- 提供所有者、管理员、编辑者和只读成员四种角色；
- 组织成员可以跨设备访问同一组织项目；
- 所有者或管理员可以把当前浏览器匿名项目迁移到组织；
- 账号功能按同源 HTTPS 部署设计。

---

## 4. Capability Matrix

| 模块 | 输入 | AI 输出 | 适用场景 | 导出 |
|---|---|---|---|---|
| 企业档案 | 企业名称、行业、场景、规模、阶段、需求 | 企业画像、需求归纳、适用模块建议 | 企业服务接待、项目建档 | MD / TXT / DOCX |
| 会议纪要 | 会议记录、录音转写 | 摘要、决策、任务、负责人、风险提醒 | 运营会、项目推进会、招商会 | MD / TXT / DOCX |
| 合同审阅 | 合同关键条款 | 商务风险提示、复核建议、注意事项 | 服务合同、采购协议、商户合作 | MD / TXT / DOCX |
| 政策准备 | 政策需求、企业背景 | 政策方向、适配理由、材料清单 | 政策咨询、申报准备 | MD / TXT / DOCX |
| 供需协作 | 供给、需求、目标对象、场景 | 供需标签、合作建议、对接话术 | 企业撮合、商户合作、服务商对接 | MD / TXT / DOCX |
| 实施计划 | 试点场景、数据范围、部署方式、周期 | 试点路径、角色分工、KPI、风险控制 | AI 场景试点、工具落地 | MD / TXT / DOCX |
| 报告归档 | 已生成模块结果 | 综合运营报告 | 台账归档、汇报材料 | MD / TXT / DOCX |

---

## 5. Architecture Overview

```mermaid
flowchart LR
    subgraph Client["Client Layer"]
        Browser["Browser UI<br/>HTML / CSS / JavaScript"]
        Session["Session Storage<br/>API Key + Draft"]
        Workspace["Anonymous Workspace Key"]
        AuthCookie["HttpOnly Session Cookie"]
    end

    subgraph App["Application Layer"]
        FastAPI["FastAPI Server"]
        Schemas["Pydantic Schemas"]
        Service["Service Orchestration"]
        Static["Static Assets"]
        AuthAPI["Account + Organization RBAC"]
        ProjectAPI["Scoped Project + History API"]
    end

    subgraph Storage["Persistent Storage"]
        SQLite["SQLite · Single Instance"]
        Postgres["PostgreSQL · Production"]
        Accounts["Users · Organizations · Sessions"]
        Projects["Projects · Versions"]
    end

    subgraph Agent["Agent Layer"]
        Hub["Zhilian Agent Hub"]
        A1["Profile Agent"]
        A2["Meeting Agent"]
        A3["Contract Agent"]
        A4["Policy Agent"]
        A5["Match Agent"]
        A6["Landing Agent"]
        A7["Report Agent"]
    end

    subgraph Model["Model Gateway"]
        LLMClient["OpenAI-Compatible Client"]
        Provider["DashScope / OpenAI / Private Gateway"]
    end

    subgraph Export["Export Layer"]
        Markdown["Markdown"]
        TXT["TXT"]
        DOCX["Word DOCX"]
    end

    Browser --> Session
    Browser --> FastAPI
    Workspace --> ProjectAPI
    AuthCookie --> AuthAPI
    FastAPI --> Static
    FastAPI --> Schemas
    FastAPI --> Service
    FastAPI --> AuthAPI
    FastAPI --> ProjectAPI
    AuthAPI --> Accounts
    ProjectAPI --> Projects
    Accounts --> SQLite
    Accounts --> Postgres
    Projects --> SQLite
    Projects --> Postgres
    Service --> Hub
    Hub --> A1
    Hub --> A2
    Hub --> A3
    Hub --> A4
    Hub --> A5
    Hub --> A6
    Hub --> A7
    Hub --> LLMClient
    LLMClient --> Provider
    Service --> Markdown
    Service --> TXT
    Service --> DOCX
```

---

## 6. Request Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant User as 用户
    participant UI as 同源工作台
    participant API as FastAPI
    participant Auth as 账号与组织权限
    participant Project as 项目数据库
    participant Agent as 业务 Agent
    participant LLM as LLM Provider

    User->>UI: 注册或登录
    UI->>API: POST /api/auth/login
    API->>Auth: 校验 scrypt 密码哈希
    Auth-->>UI: HttpOnly 会话 Cookie + CSRF 令牌

    User->>UI: 选择组织和业务模块
    UI->>API: 业务输入 + 组织作用域
    API->>Auth: 校验成员角色
    API->>Agent: 调用对应 Agent
    Agent->>LLM: 发送结构化提示词
    LLM-->>Agent: 返回业务材料
    Agent-->>UI: 结构化结果

    User->>UI: 主动保存项目
    UI->>API: 项目快照 + 组织 + CSRF
    API->>Auth: 校验 project:update 权限
    API->>Project: 保存新版本，不保存模型凭据
    Project-->>UI: 返回项目和 lock_version
```

---

## 7. Data Governance

系统采用 **默认会话保存、用户主动项目持久化** 的设计方式：

```mermaid
flowchart TD
    A[用户输入 API Key] --> B[浏览器 sessionStorage]
    B --> C[随模型请求发送至 FastAPI]
    C --> D[仅当前模型请求内存使用]
    D --> E[调用大模型接口]
    E --> F[返回生成结果]
    F --> G[浏览器会话结果]
    G --> H[用户手动导出]
    G -->|用户主动保存| P[SQLite / PostgreSQL 项目与版本]

    B -.不写入.-> P
    C -.不记录 API Key.-> Log[日志]
    P -.不包含.-> Key[API Key / Base URL / Model]
```

### 安全边界

| 对象 | 处理方式 |
|---|---|
| API Key | 默认会话级保存，不写入项目数据库、版本历史、后端文件或报告 |
| 密码 | scrypt 加盐哈希，不保存明文 |
| 登录会话 | HttpOnly、SameSite=Lax Cookie；数据库只保存令牌哈希 |
| 组织写操作 | Cookie 会话 + CSRF Cookie/Header 双重校验 |
| 业务表单与 AI 结果 | 默认保存在浏览器会话；用户主动保存项目时才写入配置的数据库 |
| 匿名工作区密钥 | 原始值仅保存在浏览器，服务端只保存 SHA-256 哈希 |
| 合同文本 | 建议用户脱敏后输入；保存项目意味着用户明确选择持久化该表单内容 |
| 客户数据 | 不建议输入完整手机号、身份证号、银行卡号等敏感信息 |
| AI 输出 | 作为初稿与辅助判断，必须人工复核 |
| 导出报告 | 只包含生成结果，不包含 API Key 和模型配置 |

---

## 8. Frontend Interaction Model

```mermaid
flowchart TB
    Home["运营总览 / Hero 首页"] --> Status["工作台状态"]
    Home --> Account["登录 / 组织"]
    Home --> Identity["业务身份"]
    Home --> API["配置模型接口"]
    Home --> Projects["项目管理"]
    Home --> Modules["业务模块"]

    Account --> Login["注册 / 登录"]
    Account --> Org["组织空间切换"]
    Account --> Members["成员和角色"]
    Account --> Claim["匿名项目迁移"]

    Projects --> Create["新建并保存"]
    Projects --> Save["保存当前项目"]
    Projects --> History["版本历史"]
    Projects --> Archive["归档 / 恢复"]

    Modules --> Profile["企业档案"]
    Modules --> Meeting["会议纪要"]
    Modules --> Contract["合同审阅"]
    Modules --> Policy["政策准备"]
    Modules --> Match["供需协作"]
    Modules --> Landing["实施计划"]

    Profile --> Result["模块结果面板"]
    Meeting --> Result
    Contract --> Result
    Policy --> Result
    Match --> Result
    Landing --> Result

    Result --> Copy["复制结果"]
    Result --> MD["下载 Markdown"]
    Result --> TXT["下载 TXT"]
    Result --> DOCX["下载 Word"]
    Result --> Report["报告归档"]
```

---

## 9. Directory Structure

```text
zhilian_tianhe_agent_fastapi_enterprise_ui_final/
├── backend/
│   ├── main.py                 # FastAPI app, routes, middleware
│   ├── schemas.py              # AI request/response models
│   ├── auth_schemas.py         # Account and organization API models
│   ├── auth_routes.py          # Login, session, organization and member endpoints
│   ├── auth_store.py           # Password hashing, sessions, RBAC and scoped projects
│   ├── project_schemas.py      # Persistent project and history models
│   ├── project_routes.py       # Scoped project CRUD and history endpoints
│   ├── project_store.py        # SQLite / PostgreSQL project store
│   └── service.py              # Agent hub creation and export helpers
│
├── frontend/
│   ├── index.html              # Enterprise SaaS single-page UI
│   └── assets/
│       ├── app.js              # State management, API calls, export
│       ├── account-access.js   # Login, organizations, members and CSRF headers
│       ├── account-access.css  # Account and organization UI
│       ├── project-storage.js  # Project and version management
│       ├── project-storage.css # Project manager UI
│       ├── project-history.css # Version history UI
│       ├── style.css           # Enterprise UI design system
│       └── hero-enterprise-ai.png
│
├── docs/
│   ├── AUTH_RBAC.md
│   ├── PROJECT_STORAGE.md
│   └── PROJECT_HISTORY.md
├── data/
├── src/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── .env.example
├── LICENSE
└── README.md
```

---

## 10. Quick Start

### 10.1 Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 10.2 Configure Storage and Accounts

```env
DATABASE_URL=sqlite:///./runtime/zhilink.db
AUTH_ALLOW_REGISTRATION=true
PASSWORD_MIN_LENGTH=10
SESSION_TTL_HOURS=168
AUTH_COOKIE_SECURE=false
```

PostgreSQL production example：

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/zhilink
AUTH_COOKIE_SECURE=true
```

### 10.3 Run Locally

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

---

## 11. API Configuration

Default recommended configuration:

| Field | Value |
|---|---|
| Provider | 通义千问 DashScope |
| Base URL | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Model | `qwen-plus` |
| Temperature | `0.35` |

The platform also supports any OpenAI-compatible endpoint. Model interface configuration is not written into projects or version history.

---

## 12. Backend API Reference

### AI and export

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serve frontend |
| `GET` | `/health` | Health check |
| `GET` | `/api/defaults` | Provider presets and module metadata |
| `POST` | `/api/test-connection` | Test LLM connectivity |
| `POST` | `/api/profile` | Generate enterprise profile |
| `POST` | `/api/meeting` | Generate meeting notes |
| `POST` | `/api/contract` | Generate contract risk hints |
| `POST` | `/api/policy` | Generate policy preparation suggestions |
| `POST` | `/api/match` | Generate supply-demand collaboration plan |
| `POST` | `/api/landing` | Generate implementation plan |
| `POST` | `/api/report` | Generate AI-integrated report |
| `POST` | `/api/report/markdown` | Export Markdown |
| `POST` | `/api/report/txt` | Export TXT |
| `POST` | `/api/report/docx` | Export Word DOCX |

### Accounts and organizations

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register and create an owner organization |
| `POST` | `/api/auth/login` | Login and create HttpOnly session |
| `GET` | `/api/auth/session` | Read current session and organizations |
| `POST` | `/api/auth/logout` | Revoke current session |
| `GET/POST` | `/api/organizations` | List or create organizations |
| `GET/POST` | `/api/organizations/{id}/members` | List or add registered members |
| `PUT/DELETE` | `/api/organizations/{id}/members/{user_id}` | Change role or remove member |
| `POST` | `/api/organizations/{id}/claim-workspace-projects` | Move current anonymous projects into organization |

### Projects and history

| Method | Endpoint | Description |
|---|---|---|
| `GET/POST` | `/api/projects` | List or create projects in current scope |
| `GET/PUT/DELETE` | `/api/projects/{project_id}` | Read, save/archive, or delete project |
| `GET` | `/api/projects/{project_id}/versions` | List immutable versions |
| `GET` | `/api/projects/{project_id}/versions/{version}` | Read historical snapshot |
| `POST` | `/api/projects/{project_id}/versions/{version}/restore` | Restore historical material as a new version |

---

## 13. Deployment

### Docker Compose

```bash
docker compose up -d --build
```

Compose 默认将 SQLite 放入 `zhilink_project_data` 命名卷。正式多实例部署应将 `DATABASE_URL` 切换为 PostgreSQL。

生产账号部署必须使用：

```env
AUTH_COOKIE_SECURE=true
ENABLE_HSTS=true
```

账号功能要求同源 HTTPS。前后端分离时应使用 Nginx、云网关或平台 rewrites 把 UI 和 FastAPI 统一到同一公开域名。

Render 免费实例等无持久磁盘环境不能依赖容器内 SQLite 长期保存项目、账号或版本历史；应配置托管 PostgreSQL、持久磁盘，或关闭持久化和账号能力。

---

## 14. Testing

Run tests:

```bash
pytest -q
```

Targeted account and project tests:

```bash
PYTHONPATH=. pytest -q \
  tests/test_project_store.py \
  tests/test_project_routes.py \
  tests/test_project_history.py \
  tests/test_auth_rbac.py \
  tests/test_project_app_integration.py
```

Check frontend JavaScript:

```bash
node --check frontend/assets/app.js
node --check frontend/assets/account-access.js
node --check frontend/assets/project-storage.js
```

Check Python compilation:

```bash
python -m compileall backend src tests
```

---

## 15. Design Principles

- Not a generic chatbot.
- Not a heavy ERP system.
- Not a simple form demo.
- A lightweight enterprise AI workspace with evidence-grounded output, explicit versioned storage, organization RBAC and export capability.

---

## 16. Development Guide

### Modify UI

```text
frontend/index.html
frontend/assets/style.css
frontend/assets/account-access.css
frontend/assets/project-storage.css
frontend/assets/project-history.css
```

### Modify Interactions

```text
frontend/assets/app.js
frontend/assets/account-access.js
frontend/assets/project-storage.js
```

### Modify Accounts and RBAC

```text
backend/auth_schemas.py
backend/auth_routes.py
backend/auth_store.py
docs/AUTH_RBAC.md
```

### Modify Project Storage

```text
backend/project_schemas.py
backend/project_routes.py
backend/project_store.py
docs/PROJECT_STORAGE.md
docs/PROJECT_HISTORY.md
```

### Modify Agent Outputs

```text
src/zhilian_tianhe_agent/prompts.py
```

### Modify LLM Provider Logic

```text
src/zhilian_tianhe_agent/llm_client.py
```

---

## 17. Roadmap

```mermaid
gantt
    title 智链天河企业运营 AI 工作台 Roadmap
    dateFormat  YYYY-MM-DD

    section V1 Enterprise Workspace
    企业级 UI 与 Hero 首页            :done, v1a, 2026-07-01, 2d
    用户自填 API 与连接测试            :done, v1b, 2026-07-02, 2d
    业务模块结构化输出                 :done, v1c, 2026-07-03, 2d
    单模块 MD/TXT/Word 导出            :done, v1d, 2026-07-04, 2d
    天河场景快速填入                   :done, v1e, 2026-07-05, 2d

    section V2 Operational Layer
    SQLite/PostgreSQL 项目存储         :done, v2a, 2026-08-04, 1d
    项目和材料版本历史                 :done, v2b, 2026-08-04, 1d
    账号、组织空间与 RBAC              :done, v2c, 2026-08-04, 1d
    人工编辑、确认和审核               :active, v2d, 2026-08-05, 7d

    section V3 Enterprise Deployment
    私有模型网关适配                   :v3a, 2026-08-24, 7d
    管理后台与审计日志                 :v3b, 2026-09-01, 10d
    内网部署与权限策略                 :v3c, 2026-09-12, 10d
```

---

## 18. Recommended GitHub Metadata

### Repository Name

```text
zhilian-tianhe-enterprise-ai-workspace
```

### Description

```text
Enterprise AI operations workspace for meeting notes, contract risk review, policy preparation, supply-demand collaboration, implementation planning and report archiving.
```

### Topics

```text
enterprise-ai
fastapi
openai-compatible
dashscope
qwen
ai-agent
business-automation
contract-review
meeting-summary
policy-assistant
b2b-saas
report-generation
```

---

## 19. License

```text
Copyright (c) 2026 李庆
All Rights Reserved.
```

本项目当前采用 **保留所有权利（All Rights Reserved）** 方式发布。即使仓库公开展示，也不代表开放复制、修改、再发布、商用部署或二次参赛授权。

未经作者明确书面许可，任何第三方不得：

- 复制、修改、分发或再授权本项目；
- 将本项目用于商业交付或对外提供服务；
- 将本项目改名包装后作为自己的作品、产品或参赛项目提交；
- 移除作者信息、版权声明或项目来源说明；
- 复用本项目的 UI 设计、业务流程、提示词结构、数据文件或文档内容进行衍生发布。

---

## 20. Final Statement

> **智链天河 · 企业运营 AI 工作台** 以企业运营材料为核心对象，以大模型为生成引擎，以证据化输出、显式版本存储、组织权限和报告归档为交付形态，面向真实企业服务场景，提供一套轻量、可部署、可复核、可扩展的 AI 工作台解决方案。
