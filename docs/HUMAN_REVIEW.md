# 人工编辑、确认与审核工作流

第二阶段第 10 项为项目中的 AI 结果增加服务端控制的人工编辑、提交审核、批准、退回和确认流程。审核操作建立在项目存储、版本历史和组织 RBAC 之上。

## 为什么必须先保存项目

人工审核只针对已经保存的项目版本，不直接审核浏览器中尚未持久化的临时输出：

- 审核对象必须有稳定的项目 ID 和版本号；
- 审核操作必须进入项目版本历史；
- 多页面同时操作时必须使用 `lock_version` 防止覆盖；
- 组织审批必须记录真实登录成员和角色；
- 新生成但尚未保存的内容不能沿用旧审批状态。

如果浏览器中的结果与项目已保存内容不同，审核窗口会停止写入操作，并提示用户先保存项目。

## 审核状态

```text
ai_draft          AI 初稿，尚未人工编辑
edited            已人工编辑，尚未提交审核
pending_review    已提交，等待审核人员处理
changes_requested 审核人员退回修改
approved          组织管理员或所有者正式批准
confirmed         匿名工作区使用者本地确认
```

`confirmed` 不等同于组织审批。匿名工作区没有经过身份认证的审核人，因此不能生成 `approved` 状态。

## 角色权限

| 角色 | 编辑 | 提交审核 | 批准 | 退回 | 恢复 AI 原稿 |
|---|---:|---:|---:|---:|---:|
| `owner` | 是 | 是 | 是 | 是 | 是 |
| `admin` | 是 | 是 | 是 | 是 | 是 |
| `editor` | 是 | 是 | 否 | 否 | 是 |
| `viewer` | 否 | 否 | 否 | 否 | 否 |
| 匿名工作区 | 是 | 是 | 仅本地确认 | 否 | 是 |

前端会按角色显示按钮，但权限最终由后端执行，不能通过手工请求绕过。

## 服务端可信状态

审核状态保存在项目快照的 `reviews` 字段中，但该字段由服务端控制：

- 新建项目时，客户端提交的审核状态会被忽略；
- 普通项目保存不能直接修改审核状态；
- 如果模块结果发生变化，服务端自动把该模块重置为 `ai_draft`；
- 已批准材料重新生成后，旧批准立即失效；
- 只有专用审核接口可以产生 `edited`、`pending_review`、`approved` 等状态；
- 审核人姓名和角色由登录会话确定，不采用客户端自行提交的身份字段。

项目快照中的审核状态包含当前状态、AI 原始稿和哈希、当前工作稿哈希、修订次数、提交人与审核人、操作时间和说明。

AI 原始稿只在用户第一次执行审核操作后写入审核状态，未进入审核流程的普通项目不会无条件复制一份完整结果。

## 审核操作记录

新增 `project_review_events` 表，每一次审核动作都会产生不可变记录：

- 项目和业务模块；
- 操作类型；
- 操作前状态和操作后状态；
- 操作人用户 ID、显示名称和角色；
- 审核意见；
- 当前内容 SHA-256；
- 操作时间。

支持：

```text
save_edit       保存人工编辑
submit_review   提交审核
approve         审核通过
request_changes 退回修改
confirm         匿名空间本地确认
revert_ai       恢复 AI 原始稿
```

审核事件不会因为恢复旧项目版本而被删除。项目永久删除时，审核事件随项目清理。

## 与项目版本历史的关系

每一次有效审核操作都会：

1. 校验当前项目 `lock_version`；
2. 更新模块工作稿或审核状态；
3. 递增项目版本；
4. 创建新的不可变项目历史版本；
5. 写入一条审核事件。

例如：

```text
v1 AI 初稿
v2 人工编辑会议纪要
v3 提交人工审核
v4 审核退回修改
v5 再次人工编辑
v6 提交审核
v7 组织批准
```

旧版本和审核事件均继续保留。

## API

```text
GET  /api/projects/{project_id}/reviews
GET  /api/projects/{project_id}/reviews/{module}
GET  /api/projects/{project_id}/reviews/{module}/events
POST /api/projects/{project_id}/reviews/{module}/actions
```

退回示例：

```json
{
  "lock_version": 4,
  "action": "request_changes",
  "note": "请补充负责人和明确完成日期"
}
```

人工编辑并提交：

```json
{
  "lock_version": 5,
  "action": "submit_review",
  "content": "编辑后的完整 Markdown 内容",
  "note": "已根据审核意见补充责任人和时间节点"
}
```

组织写操作需要登录会话和 CSRF 令牌。匿名项目操作需要有效的 `X-Workspace-Key`。

## 前端行为

每个已生成模块结果下方新增审核状态栏。项目保存后，可以打开人工复核窗口：

- 查看当前审核状态；
- 编辑完整工作稿；
- 填写编辑说明或审核意见；
- 查看 AI 原始稿；
- 提交审核；
- 批准或退回；
- 查看审核事件时间线；
- 恢复 AI 原始稿。

如果当前浏览器结果和服务器项目版本不同，所有审核写入按钮会禁用。

## 当前边界

本阶段尚未实现指定审核人、多级会签、审核截止提醒、电子签名、附件、事件导出和审批模板。

`approved` 表示系统内具有 `owner` 或 `admin` 角色的成员完成了确认，不代表法律签署、财务授权或外部专业机构意见。

## 测试

```bash
PYTHONPATH=. pytest -q tests/test_review_workflow.py
node --check frontend/assets/review-workflow.js
python -m py_compile \
  backend/review_schemas.py \
  backend/review_store.py \
  backend/review_routes.py \
  backend/project_schemas.py \
  backend/project_routes.py
```

测试覆盖客户端伪造审批被拒绝、新内容使旧审核失效、匿名确认、编辑者提交、管理员批准和退回、意见必填、恢复原稿、版本递增、审核事件以及前端 bundle 接入。
