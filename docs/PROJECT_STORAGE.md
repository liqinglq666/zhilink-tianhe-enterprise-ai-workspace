# 项目存储

第二阶段第 7 项为工作台增加了可持久化项目。默认使用 SQLite，也可以通过同一套 SQLAlchemy 模型切换 PostgreSQL。

## 用户操作

页面顶部新增“项目”入口，支持：

- 新建并保存当前工作区
- 显式保存当前项目
- 打开已有项目
- 归档和恢复项目
- 删除项目
- 显示当前项目是否存在未保存更改

系统不会在用户输入时静默上传。只有点击“新建并保存”或“保存当前项目”时，项目快照才会写入数据库。

## 项目快照内容

项目快照只包含：

- 使用单位、角色和联系人等身份上下文
- 企业档案
- 各业务模块表单内容
- 已完成的 AI 结果
- 结果生成模式、错误状态和时间
- 当前所在页面

项目快照明确不包含：

- 模型 API Key
- Base URL
- 模型名称
- 生成温度
- 浏览器工作区原始密钥

项目 Schema 使用 `extra="forbid"`，即使客户端主动提交 `api_key` 等额外字段，也会被后端拒绝。

## 匿名工作区隔离

账号系统将在后续阶段实现。当前阶段为避免公开 Demo 中不同使用者互相看到材料，浏览器会生成一个 256 位随机工作区密钥，并通过请求头发送：

```text
X-Workspace-Key: <browser-generated-secret>
```

服务端只保存该密钥的 SHA-256 哈希，不保存原始值。所有项目查询、读取、更新和删除都同时校验项目 ID 与工作区哈希。

该机制用于阶段性数据隔离，但不等同于正式账号认证：

- 清除浏览器网站数据后，用户将失去匿名项目的访问密钥。
- 复制项目 URL 不会把访问权限转移给其他浏览器。
- 账号、组织和角色权限完成后，应把匿名项目迁移到正式用户或组织。

## 数据库配置

### SQLite

默认值：

```env
DATABASE_URL=sqlite:///./runtime/zhilink.db
```

本地启动时会自动创建 `runtime` 目录和 `projects` 表。

Docker Compose 默认使用：

```env
DATABASE_URL=sqlite:////app/runtime/zhilink.db
```

并将 `/app/runtime` 挂载到命名卷 `zhilink_project_data`，容器重建后项目数据仍会保留。

单实例、小团队试点和本地部署可以使用 SQLite。请勿让多个应用实例同时写入同一个通过网络文件系统共享的 SQLite 文件。

### PostgreSQL

多实例、正式生产或需要集中备份时使用 PostgreSQL：

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/zhilink
```

系统也会把常见的 `postgres://` 和 `postgresql://` 自动规范为 psycopg 连接地址。

### Render 和其他托管平台

Render 免费实例及其他不提供持久磁盘的托管环境，其容器文件系统可能在重启、重新部署或实例迁移后被清空。此时即使配置了本地 SQLite，项目也不能视为长期保存。

在线 Demo 要保留项目数据，应至少满足一项：

- 使用托管 PostgreSQL，并通过 `DATABASE_URL` 连接；
- 为应用挂载平台提供的持久磁盘，并把 SQLite 文件放在该磁盘中；
- 明确关闭项目保存入口，只把站点作为无持久化演示环境。

不得把临时容器文件系统中的 SQLite 描述为可靠的生产归档。

## API

所有接口都必须携带 `X-Workspace-Key`。

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/projects` | 列出当前工作区项目，默认不包含已归档项目 |
| `POST` | `/api/projects` | 创建项目并保存当前快照 |
| `GET` | `/api/projects/{project_id}` | 读取单个项目及完整快照 |
| `PUT` | `/api/projects/{project_id}` | 更新名称、说明、状态或快照 |
| `DELETE` | `/api/projects/{project_id}` | 永久删除项目 |

列表接口只返回项目摘要，不返回大体积快照。

## 并发保存

项目包含递增的 `lock_version`。更新时客户端必须提交当前版本：

```json
{
  "lock_version": 3,
  "name": "项目名称",
  "snapshot": {}
}
```

如果另一个页面已经保存了新版本，后端返回：

```json
{
  "detail": "项目已在其他页面更新，请重新载入后再保存。",
  "code": "PROJECT_VERSION_CONFLICT",
  "retryable": false,
  "current_version": 4
}
```

当前阶段只防止覆盖，不保留旧版本。完整版本历史在下一项实现。

## 数据表

`projects` 表当前包含：

- `id`
- `workspace_hash`
- `name`
- `description`
- `status`
- `snapshot` JSON
- `lock_version`
- `created_at`
- `updated_at`

应用首次访问项目接口时会创建初始表。后续正式修改表结构时应引入数据库迁移流程，不应仅依赖 `create_all` 修改既有生产表。

## 备份建议

SQLite：

1. 停止应用写入或使用 SQLite 在线备份能力。
2. 备份 `runtime/zhilink.db` 和 Docker 命名卷。
3. 定期在独立环境验证恢复。

PostgreSQL：

1. 使用云数据库自动备份或 `pg_dump`。
2. 设置保留周期和异地备份。
3. 在发布数据库结构变更前创建恢复点。

## 测试

```bash
PYTHONPATH=. pytest -q \
  tests/test_project_store.py \
  tests/test_project_routes.py \
  tests/test_project_app_integration.py
node --check frontend/assets/project-storage.js
```

当前隔离环境已执行存储层和路由层测试，结果为 `6 passed`；主应用集成测试已写入仓库，等待完整依赖环境或 CI 执行。

测试覆盖工作区隔离、密钥哈希、SQLite CRUD、归档过滤、乐观锁冲突、空项目名、凭据字段拒绝、主应用限流/安全响应头接入和 API 错误契约。
