# 可验证的结构化 JSON 结果

第二阶段第 11 项把工作台中的 Markdown 结果升级为“可读 Markdown + 可验证 JSON”双轨输出。

## 设计选择

本阶段不要求模型额外生成一份 JSON，也不使用第二次模型调用。原因是：

- 两份独立模型输出可能互相矛盾；
- 模型 JSON 可能被截断、缺字段或包含无法解析的内容；
- 二次转换增加成本、延迟和失败点；
- 人工编辑后，模型生成的旧 JSON 会立即失效。

系统改为在 Markdown 完成后，由服务端确定性解析并生成 JSON。相同 Markdown、相同模块一定得到相同 JSON 和相同 SHA-256。

## Schema

当前 Schema 版本：

```text
1.0
```

顶层字段包括：

```text
schema_version
module
title
summary
sections
facts
inferences
risks
actions
pending_confirmations
evidence_ids
source_sha256
validation
```

每个章节会保留：

- 稳定章节编号；
- 标题；
- 类型：摘要、文本、列表、勾选清单、表格或混合；
- 正文；
- 列表项；
- 表格列和行；
- 章节引用的证据编号。

## 校验

`validation` 包含：

```text
valid
warnings
missing_required_sections
section_count
heading_count
evidence_reference_count
pending_confirmation_count
```

校验会检查：

- 是否存在 Markdown 二级标题；
- 是否识别到一句话结论；
- 是否包含当前模块要求的关键章节；
- 是否识别到证据编号；
- 文本出现待确认表述时，是否提取出结构化待确认项。

`valid=false` 不会删除 Markdown，只表示结构化结果需要人工复核。

## 内容哈希

`source_sha256` 是当前完整 Markdown 的 SHA-256。

外部系统可以通过以下流程验证 JSON 是否仍对应当前文本：

1. 对 Markdown 使用 UTF-8 编码；
2. 计算 SHA-256；
3. 与 `source_sha256` 比较；
4. 不一致时重新调用转换接口。

人工编辑、重新生成或审核修改内容后，旧 JSON 哈希将不再匹配。

## API

转换当前 Markdown：

```text
POST /api/structured/convert
```

请求：

```json
{
  "module": "meeting",
  "content": "## 一句话结论\n..."
}
```

读取精确 JSON Schema：

```text
GET /api/structured/schema
```

转换接口不调用模型、不保存输入，并继续受统一请求大小限制和写请求限流保护。

## 前端

每个生成结果下方新增结构化状态栏：

- Schema 校验是否通过；
- 章节数量；
- 证据编号数量；
- 待确认项数量；
- 校验告警数量。

结构化窗口支持：

- 查看一句话结论；
- 查看输入事实、AI 推断、风险、动作和待确认项；
- 查看章节、清单和表格；
- 查看原始 JSON；
- 复制 JSON；
- 下载 `.structured.json`。

浏览器仅把结构化 JSON 保存在当前会话。项目数据库仍以 Markdown 为事实来源，结构化 JSON 按需重新生成，避免保存冗余或过期副本。

## 模块要求

当前会检查以下关键章节：

| 模块 | 关键章节示例 |
|---|---|
| 企业档案 | 一句话结论、企业画像、主要运营痛点、待确认信息 |
| 会议纪要 | 一句话结论、关键决策、待办事项、待确认信息 |
| 合同审阅 | 一句话结论、重点风险、待确认、免责声明 |
| 政策准备 | 一句话结论、推荐关注方向、真实政策核验、待补齐 |
| 供需协作 | 一句话结论、供需标签、合作方案、待确认信息 |
| 实施计划 | 一句话结论、标准 SOP、数据与安全边界、待确认信息 |
| 运营报告 | 一句话结论、关键事项、待确认信息、风险声明 |

## 当前边界

当前结构化 JSON 是对 Markdown 的确定性结构化视图，不代表额外事实，也不会提升原始 AI 内容的真实性。

表格复杂合并单元格、嵌套 Markdown、非标准标题和模型格式偏差可能产生告警。此时应以 Markdown、原始输入证据和人工审核结果为准。

## 测试

```bash
PYTHONPATH=. pytest -q tests/test_structured_results.py
node --check frontend/assets/structured-results.js
python -m py_compile \
  backend/structured_routes.py \
  src/zhilian_tianhe_agent/structured_output.py
```

隔离验证结果为 `6 passed`。
