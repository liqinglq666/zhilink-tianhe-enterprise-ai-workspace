# 第一批发布加固

本批次解决四个发布前基础问题：持续集成、版本化数据库迁移、SQLite 外键完整性，以及项目删除后的关联数据完整性。

## 1. 持续集成

`.github/workflows/ci.yml` 在 Pull Request 和 `main` 推送时运行：

- Python 3.10、3.11、3.12 完整 `pytest`；
- Python 源码编译检查；
- `frontend/assets` 下全部 JavaScript 的 `node --check`；
- 全新 SQLite 数据库迁移及重复迁移；
- PostgreSQL 16 数据库迁移及重复迁移；
- 数据库 Schema 就绪检查；
- 生产 Docker 镜像构建。

Docker 构建只有在全部 Python 测试和两种数据库迁移都通过后才运行。

## 2. Alembic 数据库迁移

数据库结构从本批次开始由 Alembic 版本管理：

```text
alembic.ini
alembic/env.py
alembic/versions/20260805_0001_baseline.py
```

当前基线版本：

```text
20260805_0001
```

执行升级：

```bash
python scripts/migrate.py
```

检查数据库是否适合启动当前版本：

```bash
python scripts/check_schema.py
```

也可以直接使用 Alembic：

```bash
alembic current
alembic upgrade head
alembic history
```

### 兼容已有数据库

早期版本通过 `Base.metadata.create_all()` 建立数据表。基线迁移使用共享 SQLAlchemy Metadata 和 `checkfirst=True`：

- 空数据库会创建全部当前数据表；
- 已有数据库不会重复创建现有表；
- 迁移成功后写入 `alembic_version`；
- 后续字段、索引和约束变化必须新增显式 Alembic revision。

基线迁移不提供破坏性 downgrade。需要回到基线以前时，应恢复数据库备份，而不是删除全部业务表。

## 3. 部署顺序

生产发布必须按照以下顺序：

```text
创建数据库恢复点或备份
→ 部署新代码
→ python scripts/migrate.py
→ python scripts/check_schema.py
→ 启动 FastAPI
```

Docker 镜像已经把迁移和 Schema 检查加入启动命令。如果迁移或检查失败，Web 服务不会开始接收流量。

多实例平台更推荐把迁移命令作为独立的 release/pre-deploy job，只执行一次，再启动应用实例。不要让多个应用实例长期依赖 `create_all()` 修改数据库结构。

## 4. SQLite 外键完整性

SQLite 默认不会自动执行模型中声明的外键动作。本批次会在每个 SQLite DBAPI 连接建立时执行：

```sql
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;
```

因此以下 `ON DELETE` 约束会真正生效：

- 项目 → 项目版本；
- 项目 → 组织项目归属；
- 项目 → 人工审核事件；
- 项目 → 企业服务案件；
- 服务案件 → 节点、上下文和操作事件；
- 组织、成员、知识条目与知识版本之间的约束。

## 5. 项目永久删除

“删除项目”是永久操作。数据库级回归测试确认，删除项目后不会残留：

```text
organization_projects
project_versions
project_review_events
service_cases
service_case_nodes
service_case_contexts
service_case_events
```

用户账号和组织本身不会因项目删除而被删除。

需要保留企业服务台账时，应使用“归档项目”，不要执行永久删除。后续如果产品需要强制保留服务案件，可再将删除策略改为“存在服务案件时拒绝删除”。

## 6. 发布检查

本地最小检查：

```bash
python -m pip install -r requirements.txt
python scripts/migrate.py
python scripts/check_schema.py
pytest -q
find frontend/assets -type f -name '*.js' -print0 | xargs -0 -n1 node --check
docker build -t zhilink-tianhe:release-check .
```

正式发布前还应确认：

- 已备份 SQLite 文件或 PostgreSQL；
- `DATABASE_URL` 指向持久数据库；
- HTTPS 部署设置 `AUTH_COOKIE_SECURE=true`；
- CI 全部绿色；
- 桌面端与移动端核心流程完成一次人工冒烟测试。
