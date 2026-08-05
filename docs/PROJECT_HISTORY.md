# 项目与材料版本历史

第二阶段第 8 项为持久化项目增加不可变版本历史。版本历史建立在现有 SQLite/PostgreSQL 项目存储之上，并继续使用匿名工作区密钥隔离数据。

## 核心行为

- 新建项目时生成 v1。
- 每次有实际变化的显式保存生成下一版本。
- 项目名称、说明、归档状态变更也会生成版本。
- 保存内容与当前版本完全一致且未填写版本说明时，不创建重复版本。
- 用户可以为创建和保存填写最多 200 字的版本说明。
- 历史版本不可修改。
- 恢复旧版不会删除或覆盖历史，而是生成一个新的当前版本。

`lock_version` 同时作为当前项目版本号。客户端必须携带当前版本进行保存、归档和恢复，防止多个页面互相覆盖。

## 版本内容

每个版本保存：

- 项目 ID 和工作区哈希
- 连续版本号
- 变更类型
- 版本说明
- 发生变化的业务模块
- 恢复操作的来源版本号
- 当时的项目名称、说明和状态
- 完整项目业务快照
- 创建时间

历史快照与当前项目一样，明确不包含：

- 模型 API Key
- Base URL
- 模型名称
- 生成温度
- 浏览器原始工作区密钥

## 变更模块识别

服务端根据前后两个快照确定哪些材料发生变化，使用稳定模块编号：

```text
project   项目信息或当前页面
identity  使用身份
profile   企业档案
meeting   会议纪要
contract  合同审阅
policy    政策准备
match     供需协作
landing   实施计划
report    运营报告
```

识别同时覆盖表单内容、AI 结果和结果元数据。版本列表只返回模块编号和轻量摘要，完整快照只在用户打开某个版本详情时读取。

## 恢复规则

恢复历史版本时：

1. 校验项目 ID、工作区哈希和当前 `lock_version`。
2. 读取指定历史快照。
3. 只恢复业务快照，包括身份上下文、企业档案、表单、AI 结果和当前页面。
4. 保留当前项目名称、项目说明和归档状态，避免旧元数据意外覆盖当前管理状态。
5. 创建新的 `restore` 版本，并记录 `source_version_number`。

例如当前为 v5，恢复 v2 后会生成 v6：

```text
v1 创建项目
v2 补充会议材料
v3 合同审阅结果
v4 更新实施计划
v5 当前项目
v6 恢复自 v2
```

v3、v4、v5 仍然保留。

## 旧项目迁移

版本历史功能上线前已经存在的项目无法还原过去未保存的历史。应用启动项目存储时会为没有历史记录的旧项目创建一条 `baseline` 基线版本：

- 版本号沿用项目当前 `lock_version`；
- 快照为升级时数据库中的当前快照；
- 标记为“启用版本历史时的当前快照”。

这不会伪造升级前不存在的版本。

## API

所有接口都要求 `X-Workspace-Key`。

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/projects/{project_id}/versions` | 分页读取版本摘要，按版本号倒序 |
| `GET` | `/api/projects/{project_id}/versions/{version_number}` | 读取单个版本及完整快照 |
| `POST` | `/api/projects/{project_id}/versions/{version_number}/restore` | 把历史业务快照恢复为新版本 |

恢复请求示例：

```json
{
  "lock_version": 5,
  "version_label": "恢复到法务确认前版本"
}
```

并发冲突继续返回：

```json
{
  "detail": "项目已在其他页面更新，请重新载入后再操作。",
  "code": "PROJECT_VERSION_CONFLICT",
  "retryable": false,
  "current_version": 6
}
```

指定版本不存在时返回 `PROJECT_HISTORY_NOT_FOUND`。为防止枚举其他工作区的数据，跨工作区访问与项目不存在均返回 404。

## 数据表

新增 `project_versions` 表，主要字段包括：

- `id`
- `project_id`
- `workspace_hash`
- `version_number`
- `change_kind`
- `label`
- `changed_modules` JSON
- `source_version_number`
- `project_name`
- `project_description`
- `project_status`
- `snapshot` JSON
- `created_at`

`project_id + version_number` 具有唯一约束。删除项目时，其版本历史同时删除。

## 前端操作

项目管理器现在显示：

- 当前项目版本号
- 可选版本说明
- 版本历史列表
- 每个版本的变更模块、类型、时间和来源版本
- 只读材料摘要
- 恢复材料按钮

版本详情只显示经过 HTML 转义的摘要和字符数，不执行历史内容中的 HTML 或脚本。

## 当前边界

- 当前没有单独删除某一历史版本的接口。
- 当前没有自动保留数量或自动清理策略。
- 历史版本会增加数据库体积，生产部署应监控数据库增长并纳入备份。
- 当前匿名工作区不是正式账号认证；第 9 项将引入用户、组织和角色权限。
- 表结构目前通过 `create_all` 增加新表；正式长期生产迭代应引入 Alembic 等迁移工具。

## 测试

```bash
PYTHONPATH=. pytest -q tests/test_project_history.py
node --check frontend/assets/project-storage.js
python -m py_compile \
  backend/project_store.py \
  backend/project_schemas.py \
  backend/project_routes.py
```

针对性测试覆盖：

- v1 创建
- 保存生成新版本
- 会议和合同变更模块识别
- 版本列表不返回完整快照
- 版本详情读取
- 恢复旧版生成新版本
- 恢复来源版本记录
- 过期锁冲突
- 版本不存在错误
- 旧项目基线迁移
- 空保存不产生重复版本
- 跨工作区版本隔离
- 删除项目同步删除历史
