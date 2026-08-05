# 官方政策检索、原文引用与降级边界

第三阶段第 12 项把原有“本地政策方向库”升级为两层政策工作流：

1. 从 allowlist 政府网站目录实时读取政策标题和官方原文；
2. 由模型基于服务端返回的 `POL-*` 来源生成适配分析；
3. 在模型结果后追加服务端确定生成的官方来源表、原文摘录和检索告警。

本地 `policy_directions.json` 继续存在，但只用于扩展检索词和材料准备方向，不能再被表述为官方政策来源。

## 默认官方目录

默认读取：

```text
https://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/
https://www.thnet.gov.cn/zwgk/zcjd/
```

第一项是天河区人民政府“天河政策”目录，第二项是政策解读目录。目录中的详情页可能位于天河区、广州市、广东省或中国政府官方域名。

默认域名后缀 allowlist：

```text
thnet.gov.cn
gz.gov.cn
gd.gov.cn
gov.cn
```

## 检索流程

```text
企业档案 + 政策需求
→ 本地生成检索词
→ 读取官方目录页
→ 过滤 allowlist 链接
→ 本地相关性排序
→ 并发读取候选官方详情页
→ 提取标题、机关、文号、日期、状态和原文摘录
→ 生成 POL-001、POL-002…
→ 模型分析
→ 服务端追加不可由模型省略的来源附录
```

查询词只用于本地排序，不会作为查询参数发送给商业搜索引擎。

## 状态识别

```text
active     页面存在明确未来失效日期
expired    页面失效日期早于当前日期
revoked    标题或原文明确出现废止、停止执行等表述
suspended  标题或原文明确出现暂缓、暂停实施等表述
unknown    页面未提供足够信息判断当前状态
```

`unknown` 不能被模型写成“现行有效”。`expired`、`revoked` 和 `suspended` 只能用于历史或风险提醒，不能作为当前申报依据。

## 引用结构

每个来源包含引用编号、标题、官方 URL、域名、文件类型、发布机关、文号、发布日期、实施日期、失效日期、页面状态、原文摘录、正文 SHA-256 和检索时间。

模型只能引用检索结果中实际存在的 `POL-*` 编号。最终 Markdown 会追加：

```text
## 官方政策来源与原文引用
## 政策检索边界
```

## API

```text
POST /api/policy/official/search
POST /api/policy/official
POST /api/policy/official/stream
```

仅搜索接口不调用模型。前端会把原 `/api/policy/stream` 调用切换到官方来源流式接口，其他模块不受影响。

## SSRF 与网络安全

检索器只允许 HTTP/HTTPS、标准端口和配置的政府域名后缀；每次重定向后重新验证域名；不接受用户直接提交任意抓取 URL；限制响应类型、最大字节数、目录页数、候选数、并发和超时，并使用短期内存缓存。

生产环境仍应通过网络出口策略阻止实例访问云元数据地址和内网管理地址。

## 降级策略

```text
ok           官方来源检索成功
partial      获得来源，但部分页面失败或产生告警
no_results   官方目录可访问，但没有明显匹配文件
unavailable  官方目录不可访问
disabled     部署配置关闭检索
```

没有可验证来源时，模型不得输出具体政策名称、文号、金额、截止日期或资格判断，只能给出检索建议和通用材料准备方向。

## 环境变量

```env
POLICY_RETRIEVAL_ENABLED=true
POLICY_CATALOG_URLS=https://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/;https://www.thnet.gov.cn/zwgk/zcjd/
POLICY_ALLOWED_DOMAINS=thnet.gov.cn,gz.gov.cn,gd.gov.cn,gov.cn
POLICY_FETCH_TIMEOUT_SECONDS=6
POLICY_CACHE_TTL_SECONDS=900
POLICY_MAX_CATALOG_PAGES=4
POLICY_MAX_RESULTS=6
```

## 当前边界

目录抓取不能保证覆盖全部政策；JavaScript 动态平台和 PDF 附件暂未解析；页面格式不统一时会标记“未稳定识别”；原文摘录不代表资格判断；缓存位于单个应用进程，多实例不会共享。

## 测试

```bash
PYTHONPATH=src:. pytest -q tests/test_policy_retrieval.py
node --check frontend/assets/policy-sources.js
python -m py_compile \
  src/zhilian_tianhe_agent/policy_retrieval.py \
  src/zhilian_tianhe_agent/official_policy.py \
  backend/policy_official_routes.py \
  backend/project_routes.py
```
