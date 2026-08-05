# 企业服务工作流

第三阶段第 14 项把组织项目、官方政策引用、已发布知识库条目、责任人、处理节点、审核与结项记录串成可执行流程。

## 核心对象

```text
service_cases
service_case_nodes
service_case_contexts
service_case_events
```

每个流程必须绑定当前组织中的一个持久化项目，不能基于未保存的浏览器草稿创建正式办理记录。已归档项目不能创建新的服务流程。

## 默认六个节点

```text
1. 接收建档
2. 需求诊断
3. 资料与依据核验
4. 服务方案
5. 执行跟进
6. 结项审核
```

节点具有责任人、期限、状态、处理结果、审核说明以及开始、提交和完成时间。

## 流程状态

```text
draft
active
on_hold
pending_review
completed
cancelled
```

节点状态：

```text
pending
in_progress
blocked
pending_review
completed
skipped
```

编辑者可以领取、处理、阻塞恢复和提交节点。管理员或所有者可以批准、退回、跳过或重新打开节点。

## 办理依据快照

创建流程和主动刷新依据时，系统生成不可变 `service_case_contexts` 记录。快照包含：

- 项目 ID、名称、项目版本与更新时间；
- 企业画像和使用身份；
- 已保存模块结果的 SHA-256、摘要和人工审核状态；
- 从项目政策报告中识别出的 `POL-*` 官方引用和政府 HTTPS 原文链接；
- 当前组织中经过审核、仍有效的 `THKB-...@vN` 知识引用；
- 项目结果中识别出的待确认事项；
- 完整上下文 SHA-256。

快照只保存模块摘要和哈希，不重复保存全部项目正文。完整正文继续由项目版本历史保存。

政策链接会重新校验 HTTPS、政府域名、凭据和端口。人工修改报告后加入的普通外链不会进入正式流程快照。

## 知识引用校验

流程只能绑定：

```text
THKB-XXXXXXXX@vN
```

并且该版本必须：

- 属于当前组织；
- 是条目的当前发布版本；
- 条目未归档；
- 已到生效日期；
- 未超过失效日期。

草稿、待审核版本、旧发布版本和失效版本会被拒绝。

## 官方政策引用

官方引用从项目中已保存的政策结果附录读取。流程只保存：

- `POL-001` 等引用编号；
- 政策标题；
- 通过政府域名校验的 HTTPS 原文链接。

流程不会把本地政策方向库或普通知识条目改写成官方政策。

## 结项门槛

提交结项审核前，所有节点必须是：

```text
completed
或
skipped
```

管理员或所有者批准结项时，系统再次读取当前项目版本。如果项目在依据快照之后更新，结项会返回：

```text
WORKFLOW_CONTEXT_STALE
```

必须先刷新流程依据，再重新结项。

如果快照中仍有待确认事项，结项人必须显式确认这些事项已经在结项总结中处理，或明确转入后续跟踪。系统不会静默忽略未决问题。

## RBAC

| 角色 | 查看 | 创建/编辑 | 处理并提交节点 | 批准节点/结项 | 分配责任人 |
|---|---:|---:|---:|---:|---:|
| viewer | 是 | 否 | 否 | 否 | 否 |
| editor | 是 | 是 | 是，仅本人或未分配节点 | 否 | 否 |
| admin | 是 | 是 | 是 | 是 | 是 |
| owner | 是 | 是 | 是 | 是 | 是 |

只读成员不能被设置为流程责任人或节点处理人。

## API

```text
GET  /api/service-cases
POST /api/service-cases
GET  /api/service-cases/{case_id}
PUT  /api/service-cases/{case_id}
POST /api/service-cases/{case_id}/context/refresh
POST /api/service-cases/{case_id}/actions
PUT  /api/service-cases/{case_id}/nodes/{node_id}
POST /api/service-cases/{case_id}/nodes/{node_id}/actions
GET  /api/service-cases/{case_id}/events
```

所有接口要求登录和 `X-Organization-Id`，写操作还要求 `X-CSRF-Token`。

## 并发与审计

每次修改必须提交当前 `lock_version`。旧页面操作会返回 `WORKFLOW_VERSION_CONFLICT`，不会覆盖新状态。

事件表只追加，记录：

- 流程或节点动作；
- 操作前后状态；
- 操作人、角色和说明；
- 操作载荷 SHA-256；
- 时间。

## 前端

顶部“服务流程”入口支持：

- 从当前已保存项目新建流程；
- 自动带入最近一次知识库检索的发布版本引用；
- 查看项目、官方政策、组织知识和待确认事项；
- 启动、暂停、恢复、取消和重新打开流程；
- 处理、提交、批准、退回、跳过和重开节点；
- 分配责任人和期限；
- 刷新办理依据；
- 查看不可变操作时间线；
- 提交和批准结项。

## 当前边界

本阶段未实现外部工单系统同步、短信或邮件提醒、SLA 自动升级、附件上传、电子签章、跨组织协作和统计仪表盘。统计分析属于第 15 项。
