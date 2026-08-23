# 天河企业服务知识库

第三阶段第 13 项提供一个组织级、可维护、可审核、可追溯的企业服务知识库。

## 核心原则

每条知识必须具有：稳定引用编号、不可变版本号、明确来源类型、来源标题与维护方、来源链接或参考编号、内容与来源元数据 SHA-256、适用范围、生效与失效日期、审核状态和审核记录。

## 引用编号

条目稳定编号示例：

```text
THKB-12AB34CD
```

实际引用必须包含发布版本：

```text
THKB-12AB34CD@v3
```

只引用稳定编号而不包含版本号是不完整的，因为条目后续可能继续编辑。

## 当前版本与发布版本

知识条目同时维护：

```text
current_version
published_version
```

当已发布的 v2 被编辑时：

```text
current_version   = 3
published_version = 2
review_status     = draft
```

检索仍继续使用已批准的 v2。只有 v3 经过提交和管理员/所有者批准后，发布版本才会切换到 v3。新草稿不会未经审核覆盖线上引用。

## 状态

审核状态：

```text
draft
in_review
approved
rejected
```

生命周期状态：

```text
active
archived
```

归档条目不会进入检索，即使它以前有已批准版本。

## 角色权限

| 角色 | 查看发布知识 | 查看草稿 | 创建/编辑/提交 | 批准/退回/归档 |
|---|---:|---:|---:|---:|
| viewer | 是 | 否 | 否 | 否 |
| editor | 是 | 是 | 是 | 否 |
| admin | 是 | 是 | 是 | 是 |
| owner | 是 | 是 | 是 | 是 |

权限由后端根据组织成员关系执行。

## 来源类型

```text
official       政府官方来源
internal       组织内部资料
service_guide  企业服务指南
case           服务案例
template       材料模板
faq            常见问题
other          其他参考
```

`official` 必须填写 HTTPS 政府网站链接、发布机关和可核对的原文摘录，并通过政府域名校验。其他来源即使经过组织审核，也不能被描述为政府政策、法定要求或官方资格结论。

## 有效期和适用范围

每个版本可以限定：适用区域、行业、主体类型、服务场景、使用角色、生效日期和失效日期。

尚未生效和已经失效的发布版本不会进入检索。当前检索请求能够根据企业档案中的区域和行业执行明确不匹配排除，并对“广州市天河区 / 广州市天河 / 天河区”等常见行政区后缀进行归一化。条目未填写区域或行业边界时会返回人工复核告警。

企业档案当前没有独立的主体类型字段，团队人数或经营规模不能可靠代表“企业、个体工商户、小微企业”等主体类型，因此不会据此执行硬过滤。主体类型、服务场景和使用角色会保留在检索结果中，供企业服务人员或后续工作流显式确认。

## 检索

```text
POST /api/knowledge/search
```

检索只使用当前组织中 `active`、拥有 `published_version`、已生效且未失效的版本。返回结果包含具体 `THKB-...@vN` 引用、摘录、来源、适用范围、有效期、相关度和复核告警。

`markdown_context` 可作为后续 AI 工作流的受控知识上下文，并明确区分组织知识和政府官方来源。

## API

```text
GET  /api/knowledge
POST /api/knowledge
POST /api/knowledge/search
GET  /api/knowledge/{article_id}
PUT  /api/knowledge/{article_id}
GET  /api/knowledge/{article_id}/versions
GET  /api/knowledge/{article_id}/events
POST /api/knowledge/{article_id}/actions
```

所有接口要求登录会话和 `X-Organization-Id`。写操作还要求 `X-CSRF-Token`。知识库不提供匿名空间，避免内部服务材料被其他浏览器用户读取。

## 审核动作

```text
submit
approve
reject
archive
unarchive
restore
```

恢复历史版本不会改写旧版本，而是生成一个新的草稿版本。审核事件保存版本、操作前后状态、操作人、角色、说明和时间。

## 前端

顶部“知识库”入口支持搜索已发布知识、复制带版本号的 AI 引用上下文、新建与编辑草稿、提交审核、批准或退回、归档与恢复、查看版本历史、恢复历史版本和查看审核记录。

所有正文、摘录和来源字段均经过 HTML 转义后展示。

## 当前边界

本阶段未实现文件上传、向量数据库、任意网站抓取、自动发布政策检索结果、跨组织共享、单条 ACL 和自动注入全部 Agent。

`window.ZHILINK_KNOWLEDGE.search()` 与 `/api/knowledge/search` 已提供稳定集成接口。第 14 项企业服务工作流将基于该接口按具体任务注入已批准知识。

## 测试

```bash
PYTHONPATH=. pytest -q tests/test_knowledge_base.py tests/test_knowledge_scope.py
node --check frontend/assets/knowledge-base.js
python -m py_compile \
  backend/knowledge_schemas.py \
  backend/knowledge_store.py \
  backend/knowledge_routes.py
```
