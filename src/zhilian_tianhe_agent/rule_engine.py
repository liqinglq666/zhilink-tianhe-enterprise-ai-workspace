# -*- coding: utf-8 -*-
"""无API Key时的本地规则兜底引擎。

这不是替代大模型，而是为了保证企业服务报告在无网络/无Key情况下仍可展示完整流程。
"""

from __future__ import annotations

import re
from typing import Dict, List

from .constants import LEGAL_DISCLAIMER
from .utils import load_json, safe_join, normalize_text


def _guess_stage(scale: str, stage: str) -> str:
    text = f"{scale} {stage}"
    if any(x in text for x in ["初创", "1-10", "10人", "种子", "原型"]):
        return "初创验证期"
    if any(x in text for x in ["成长", "扩张", "50", "100", "营收"]):
        return "成长扩张期"
    if any(x in text for x in ["成熟", "总部", "集团", "上市"]):
        return "成熟运营期"
    return stage or "常规运营期"


def build_profile_report(profile: Dict[str, str]) -> str:
    industry = profile.get("industry", "企业服务/商贸服务")
    name = profile.get("name", "该经营主体")
    scale = profile.get("scale", "")
    stage = _guess_stage(scale, profile.get("stage", ""))
    demands = profile.get("demands", "政策、合同、会议、供需协作")
    location = profile.get("location", "天河区园区/商圈/CBD")

    modules = []
    demand_text = demands + industry
    if any(k in demand_text for k in ["政策", "申报", "补贴", "扶持"]):
        modules.append("产业政策智能匹配")
    if any(k in demand_text for k in ["合同", "协议", "租赁", "采购", "合作", "风险"]):
        modules.append("合同文本风险提示")
    if any(k in demand_text for k in ["会议", "纪要", "协同", "任务", "项目推进"]):
        modules.append("会议纪要与任务分发")
    if any(k in demand_text for k in ["供需", "合作", "资源", "对接", "商户", "服务商", "客户"]):
        modules.append("企业供需协作助手")
    if any(k in demand_text for k in ["AI", "人工智能", "大模型", "智能", "数字化"]):
        modules.append("AI应用场景任务书生成")
    if not modules:
        modules = ["产业政策智能匹配", "合同文本风险提示", "企业供需协作助手"]

    return f"""
## 企业档案与AI企服需求诊断报告

### 1. 基本画像
- 服务对象：{name}
- 所属行业：{industry}
- 所在场景：{location}
- 发展阶段：{stage}
- 当前需求：{demands}

### 2. 运营痛点判断
1. 信息获取分散：政策、服务商、合作资源、活动信息往往分布在不同渠道，企业需要花费较高沟通成本。
2. 日常协同低效：会议纪要、任务跟进、商务沟通常依赖人工整理，容易出现责任人和时间节点不清。
3. 合作风险隐性化：租赁、采购、服务外包、品牌联动等合同条款中可能存在付款、交付、知识产权或数据安全风险。
4. 供需表达不标准：企业常常说不清“能提供什么、需要什么、适合对接谁”，导致资源撮合效率低。

### 3. 推荐优先使用模块
{chr(10).join([f"- {m}" for m in modules])}

### 4. 天河落地场景适配
- 园区企业服务中心：用于接待企业诉求、生成服务记录、整理政策方向和对接清单。
- 天河路商圈/商户运营：用于活动合作、品牌联动、商户供需撮合和合同风险提醒。
- 天河CBD商务团队：用于会议协同、服务采购、合同沟通和专业服务对接。

### 5. 下一步行动建议
1. 先用“企业档案”模块沉淀企业基本信息，形成可复用画像。
2. 将近期真实会议、合作协议或政策需求导入系统，生成第一份运营辅助报告。
3. 将“供需协作”结果转化为对接话术或AI应用场景任务书，用于园区/商圈活动试点。
""".strip()


def build_meeting_report(meeting_text: str) -> str:
    text = normalize_text(meeting_text)
    sentences = re.split(r"[。！？\n]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    summary = "；".join(sentences[:3]) if sentences else "本次会议围绕企业运营、合作推进与任务落实展开。"

    owners = []
    for name in ["张", "李", "王", "陈", "刘", "运营", "法务", "财务", "技术", "市场"]:
        if name in text:
            owners.append(name)
    owner = owners[0] if owners else "待指定负责人"

    risk_items = []
    if any(k in text for k in ["合同", "协议", "签约"]):
        risk_items.append("合作协议需同步进行合同审阅检查。")
    if any(k in text for k in ["付款", "预算", "费用", "报价"]):
        risk_items.append("费用、付款节点和预算边界需要写入任务清单。")
    if any(k in text for k in ["数据", "会员", "客户", "隐私"]):
        risk_items.append("涉及客户或会员数据时需关注数据授权、脱敏和安全边界。")
    if not risk_items:
        risk_items.append("建议补充负责人、截止时间、验收标准，避免任务无法闭环。")

    return f"""
## 会议纪要与任务分发报告

### 1. 会议摘要
{summary}

### 2. 关键决策
- 围绕当前经营/合作需求形成初步推进方向。
- 建议将会议结论转化为任务清单，并同步明确责任人、截止时间和验收标准。
- 如涉及商户活动、采购服务或AI试点，应同步生成合同审阅清单与供需协作方案。

### 3. 待办事项表
| 事项 | 负责人 | 截止时间 | 优先级 | 依赖条件 |
|---|---|---|---|---|
| 整理会议结论并确认任务边界 | {owner} | 3个工作日内 | 高 | 会议记录完整 |
| 梳理合作方/商户/服务商需求 | 运营负责人 | 5个工作日内 | 高 | 明确供需信息 |
| 检查合同或合作协议风险 | 法务/商务负责人 | 签约前 | 高 | 提供协议文本 |
| 形成试点执行计划与验收指标 | 项目负责人 | 7个工作日内 | 中 | 明确预算和周期 |

### 4. 风险提醒
{chr(10).join([f"- {r}" for r in risk_items])}

### 5. 下一次会议建议议题
- 任务完成进度与阻塞点
- 合同条款与付款节点确认
- 商户/企业供需协作清单更新
- AI应用场景任务书是否进入试点
""".strip()


def build_contract_report(contract_text: str) -> str:
    rules = load_json("contract_risk_rules.json")
    text = normalize_text(contract_text)
    found = []
    for rule in rules:
        hits = [kw for kw in rule["keywords"] if kw in text]
        if hits:
            found.append((rule["name"], hits[:5], rule["advice"]))

    if not found:
        found = [
            ("条款完整性风险", ["未识别到高频关键词"], "建议补充付款、交付、验收、违约、保密、知识产权、数据安全等核心条款。")
        ]

    risk_rows = []
    for i, (name, hits, advice) in enumerate(found, 1):
        level = "高" if any(k in name for k in ["付款", "数据", "知识产权", "违约"]) else "中"
        risk_rows.append(f"| {level} | {name} | {safe_join(hits)} | {advice} |")

    return f"""
## 合同文本商务风险提示报告

> {LEGAL_DISCLAIMER}

### 1. 风险识别结果
| 风险等级 | 风险类型 | 触发关键词 | 修改/沟通建议 |
|---|---|---|---|
{chr(10).join(risk_rows)}

### 2. 重点条款建议
- 付款条款：写清付款比例、付款节点、发票要求、逾期责任。
- 交付与验收：写清交付物、验收标准、验收期限和整改机制。
- 知识产权：写清成果归属、使用范围、源文件/源代码交付边界。
- 数据安全：写清数据使用范围、脱敏要求、保密义务和删除机制。
- 合作边界：写清双方职责、需求变更、额外费用和沟通机制。

### 3. 签约前检查清单
- [ ] 是否明确合作目标和服务范围？
- [ ] 是否明确付款节点、发票和违约责任？
- [ ] 是否明确交付物与验收标准？
- [ ] 是否明确知识产权和数据安全责任？
- [ ] 是否明确争议解决方式和合同解除条件？
""".strip()


def build_policy_report(profile: Dict[str, str], demand: str = "") -> str:
    directions = load_json("policy_directions.json")
    text = " ".join(str(v) for v in profile.values()) + " " + demand
    scored = []
    for item in directions:
        score = sum(1 for kw in item["match_keywords"] if kw.lower() in text.lower())
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [item for score, item in scored[:3]]
    if all(score == 0 for score, _ in scored[:3]):
        selected = directions[:3]

    sections = []
    for item in selected:
        sections.append(
            f"""
### {item['direction']}
- 适配理由：企业档案或当前需求与“{item['direction']}”方向存在关联，可优先作为政策检索和材料准备方向。
- 建议准备材料：{safe_join(item['materials'])}
- 注意事项：避免只写概念，应补充真实应用场景、试点计划、预期成效和风险控制。""".strip()
        )

    return f"""
## 产业政策方向匹配报告

> 本模块基于企业档案与公开政策方向进行辅助判断，不承诺申报成功。

### 1. 企业当前需求
{demand or profile.get('demands', '暂未填写明确政策需求，可先从企业档案进行方向判断。')}

### 2. 推荐关注方向
{chr(10).join(sections)}

### 3. 申报前需要补齐的信息
- 企业基本资质与经营情况
- 项目/产品简介和应用场景说明
- 技术路线、创新点和落地计划
- 预算、周期、团队分工与预期成效
- 知识产权、数据合规、试点反馈等支撑材料

### 4. 园区/商圈服务窗口辅助话术
“我们可以先根据企业档案判断适配政策方向，并生成材料准备清单；后续如需正式申报，建议结合最新政策通知和主管部门要求进一步核验。”
""".strip()


def build_match_report(profile: Dict[str, str], offer: str, need: str, target: str, scenario: str) -> str:
    offer = offer or "产品/服务能力待补充"
    need = need or "合作资源/试点场景/客户渠道"
    target = target or "园区企业、商圈商户、AI服务商、专业服务机构"
    scenario = scenario or "园区/商圈企业日常运营"

    tags = []
    full_text = f"{offer} {need} {target} {scenario}"
    for tag, keys in {
        "AI应用试点": ["AI", "人工智能", "大模型", "智能"],
        "商圈运营": ["商圈", "商户", "零售", "会员", "活动"],
        "企业服务": ["法务", "财税", "人力", "咨询", "服务"],
        "营销推广": ["营销", "短视频", "品牌", "宣传"],
        "数据与系统": ["数据", "系统", "平台", "SaaS", "接口"],
        "空间与资源": ["办公", "场地", "空间", "融资", "客户"]
    }.items():
        if any(k in full_text for k in keys):
            tags.append(tag)
    if not tags:
        tags = ["企业供需协作", "商务合作", "园区服务"]

    scene_name = f"{profile.get('name', '企业')}AI应用场景试点" if "AI" in full_text or "智能" in full_text else f"{profile.get('name', '企业')}供需协作试点"

    return f"""
## 企业供需协作与AI应用场景任务书

### 1. 供需标签
{safe_join(tags)}

### 2. 供需信息
- 我能提供：{offer}
- 我需要：{need}
- 希望对接：{target}
- 业务场景：{scenario}

### 3. 推荐合作对象类型
- 园区企业服务中心：协助整理企业需求并组织对接。
- 商圈运营方/商户联盟：适合活动联动、营销推广、消费场景试点。
- AI应用开发商/数字服务商：适合承接智能客服、知识库、营销自动化、数据分析等需求。
- 专业服务机构：适合法务、财税、人力、知识产权、合同审阅等配套支持。

### 4. 合作模式建议
1. 小范围试点：选择1-3家商户/企业先行验证。
2. 联合服务包：由AI工具方 + 专业服务机构共同提供轻量化服务。
3. 活动场景导入：结合商圈活动、园区路演、企业服务日进行批量触达。

### 5. 对接话术草稿
您好，我们正在推进“{scenario}”相关合作。我们可提供“{offer}”，目前希望对接“{need}”。如贵方具备相关场景或资源，可先以小范围试点方式合作，我们可提供需求梳理、任务书生成和运营辅助材料，降低前期沟通成本。

### 6. AI应用场景任务书
- 场景名称：{scene_name}
- 需求背景：企业/商户希望在园区或商圈运营中提升效率、降低合作风险、增强资源链接能力。
- 业务痛点：需求表达不标准、合作对象难筛选、合同风险识别难、试点验收指标不清。
- AI解决方案：通过企业档案、文本分析和任务书生成，将模糊需求转化为标准化对接材料。
- 所需数据：企业基本信息、业务需求、会议记录、合同文本、供需信息、政策方向关键词。
- 技术路线：表单采集 → 大模型分析 → 规则库校验 → 结构化报告 → 导出Word/PDF。
- 实施周期：1-2周完成Demo试点，1个月内形成可复制服务流程。
- 验收指标：生成材料完整度、对接效率提升、风险提示准确率、用户满意度、试点转化数量。
- 服务商能力要求：熟悉企业服务场景，具备大模型应用开发、数据合规意识和轻量化部署能力。
- 风险提示：注意数据脱敏、合同材料保密、政策信息更新和人工复核机制。

### 7. 天河落地理由
天河区园区、商圈、CBD企业密集，商务合作频繁，适合用轻量化AI工具提升会议协同、合同审阅、政策助手和供需协作效率。
""".strip()


def build_landing_report(profile: Dict[str, str], landing_info: Dict[str, str], existing_results: Dict[str, str]) -> str:
    """生成企业服务视角的落地可行性与试点实施报告。"""
    name = profile.get("name", "示例经营主体")
    location = profile.get("location", "天河区园区/商圈/CBD")
    industry = profile.get("industry", "企业服务/现代商贸")
    pilot_scene = landing_info.get("pilot_scene", "园区/商圈企业服务窗口")
    user_roles = landing_info.get("user_roles", "园区企业服务人员、商圈运营人员、企业负责人")
    data_scope = landing_info.get("data_scope", "企业档案、会议记录、合同条款、政策需求、供需信息")
    deployment = landing_info.get("deployment", "网页应用轻量化部署，支持用户自填API Key，本地规则兜底")
    pilot_period = landing_info.get("pilot_period", "1个月")
    review_mode = landing_info.get("review_mode", "关键结论人工复核")

    text_blob = " ".join([str(profile), str(landing_info), str(existing_results)])
    scores = {
        "场景适配度": 90 if any(k in text_blob for k in ["商圈", "园区", "CBD", "企业服务"]) else 78,
        "操作便捷度": 88 if any(k in deployment for k in ["网页", "轻量", "API"]) else 76,
        "风险可控度": 86 if any(k in text_blob for k in ["人工复核", "脱敏", "不留存", "风险"]) else 72,
        "推广复制度": 84 if any(k in text_blob for k in ["服务窗口", "商圈", "园区", "标准化"]) else 74,
        "数据准备度": 82 if data_scope else 70,
    }
    avg = round(sum(scores.values()) / len(scores), 1)
    score_rows = "\n".join([f"| {k} | {v}/100 | {'较强' if v >= 85 else '可试点'} |" for k, v in scores.items()])

    generated = [title for title, content in existing_results.items() if str(content).strip()]
    generated_text = safe_join(generated) if generated else "暂未生成其他模块，可先完成企业档案、合同审阅、政策助手与供需协作。"

    return f"""
## 企业服务版落地可行性与试点实施报告

### 1. 业务场景适配判断
- 服务方向：企业运营 AI 工作台。
- 服务对象：{name}，所属行业为{industry}，主要落地场景为{location}。
- 方向匹配：本工具覆盖会议纪要生成、合同文本商务风险提示、产业政策方向匹配、企业供需协作与AI应用场景任务书生成，能够同时回应“办公效率提升”和“经营风险防控”两类业务重点。
- 已完成模块：{generated_text}

### 2. 落地可行性评分
| 维度 | 评分 | 判断 |
|---|---:|---|
{score_rows}
| 综合成熟度 | {avg}/100 | 建议进入小范围试点 |

### 3. 典型落地场景
- 园区/商圈/企业服务窗口：用于接待企业诉求、沉淀服务台账、生成政策材料清单和供需协作记录。
- 商圈运营方：用于品牌联动活动、商户合作协议、营销服务采购、活动复盘会议等高频运营场景。
- 企业用户：用于内部会议整理、合同风险初筛、政策方向理解、服务商沟通材料生成。

### 4. 试点SOP
1. 企业接待：由{user_roles}录入企业档案和当前诉求。
2. 信息采集：采集{data_scope}，上传前对客户姓名、手机号、商业秘密等敏感信息做脱敏处理。
3. AI生成：系统生成会议纪要、合同风险提示、政策方向、供需协作方案或场景任务书。
4. 人工复核：采用“{review_mode}”机制，由企业服务人员、商务负责人或专业机构复核关键结论。
5. 对接跟进：将生成结果转化为政策材料清单、合作邀约话术、服务商沟通清单和任务台账。
6. 反馈归档：记录是否完成对接、是否进入试点、企业满意度和风险处理结果。

### 5. 数据与安全边界
- API Key由使用者在页面自行填写，仅保存在当前会话，不写入代码、不导出报告、不上传仓库。
- 默认不建设企业敏感数据库；合同、会议、客户信息建议脱敏后再输入。
- 政策助手只提供方向建议，不承诺申报成功；合同模块只提供商务风险提示，不替代法律意见。
- 重要合同、政策申报、资金奖补、数据合规事项必须保留人工复核节点。
- 后续正式部署可增加日志审计、权限分级、数据留存开关和私有化模型网关。

### 6. 量化成效指标
| 指标类别 | 试点指标 | 建议采集方式 |
|---|---|---|
| 办公效率 | 会议纪要生成时间由30-60分钟降至5分钟内 | 对比人工整理耗时 |
| 风险防控 | 合同初筛覆盖付款、交付、违约、知识产权、数据安全等核心条款 | 风险清单命中率 |
| 政策服务 | 每家企业输出1份政策方向与材料清单 | 服务记录台账 |
| 供需协作 | 每次诉求生成1份对接话术或场景任务书 | 对接转化记录 |
| 用户满意度 | 企业服务对象满意度不低于85% | 问卷/回访 |
| 推广复制 | 形成可复用的企业档案表、服务SOP和报告模板 | 运营复盘 |

### 7. 试点计划
- 第1周：选取3-5家园区企业或商圈商户，完成企业档案和典型场景采样。
- 第2周：围绕会议纪要、合同审阅、政策助手、供需协作四类任务进行试用。
- 第3周：收集企业反馈，优化提示词、风险规则库、政策方向库和报告模板。
- 第4周：形成试点复盘报告，输出可复制SOP、指标数据和下一阶段推广建议。

### 8. 三个月推广路径
1. 第1个月：在{pilot_scene}完成小范围试点，验证工具稳定性与人工复核流程。
2. 第2个月：扩展到更多商户/企业服务日活动，形成批量服务模板。
3. 第3个月：接入真实政策库、企业服务资源库或园区服务系统，形成更准确的供需匹配。

### 9. 产品落地看点
- 轻量化：网页应用即可运行，低成本试点，不依赖重型系统建设。
- 实用性：覆盖企业服务窗口高频问题，能生成可下载报告和服务台账。
- 风险可控：明确政策、合同、数据安全边界，并保留人工复核机制。
- 可推广：适合园区、商圈、CBD、创业服务站复制使用。

### 10. 局限与后续改进
- 政策库需要定期更新，并与官方政策发布渠道保持一致。
- 真实企业供需匹配需要接入园区企业库、服务商库和运营反馈数据。
- 合同风险提示需由法律专业人员复核后用于正式签约。
- 正式上线前建议补充权限管理、日志审计、脱敏规则和私有化部署方案。
""".strip()
