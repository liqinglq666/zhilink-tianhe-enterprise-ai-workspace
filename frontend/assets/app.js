const state = {
  defaults: null,
  profile: {},
  identity: {},
  results: {},
  meta: {},
};

const resultKeys = ["profile", "meeting", "contract", "policy", "match", "landing"];
const resultTitles = {
  profile: "企业档案",
  meeting: "会议纪要",
  contract: "合同审阅",
  policy: "政策准备",
  match: "供需协作",
  landing: "实施计划",
  report: "运营报告",
};


const pageMeta = {
  home: { kicker: "运营总览", title: "企业运营 AI 工作台", subtitle: "面向企业日常运营的会议、合同、政策、供需协作与报告归档能力。" },
  profile: { kicker: "企业档案", title: "企业基础资料管理", subtitle: "补充企业背景，用于提升政策准备、供需协作和实施计划的贴合度。" },
  meeting: { kicker: "会议纪要", title: "会议记录结构化处理", subtitle: "将会议记录整理为摘要、决策、待办事项、负责人、时间节点和风险提醒。" },
  contract: { kicker: "合同审阅", title: "合同条款商务风险提示", subtitle: "识别付款、交付、违约、知识产权、数据安全和合作边界等风险。" },
  policy: { kicker: "政策准备", title: "政策方向与材料清单", subtitle: "根据企业情况或政策需求生成方向建议、材料清单和注意事项。" },
  match: { kicker: "供需协作", title: "合作需求整理与对接", subtitle: "整理供给、需求和目标对象，生成合作建议、对接话术和方案框架。" },
  landing: { kicker: "实施计划", title: "试点执行与复核机制", subtitle: "生成试点场景、使用角色、数据边界、部署方式、复核机制和评估指标。" },
  report: { kicker: "报告归档", title: "业务材料汇总导出", subtitle: "按需汇总已生成结果，导出 Markdown、TXT 或 Word 文档。" },
};
const formInputIds = [
  "profileName", "profileIndustry", "profileLocation", "profileScale", "profileStage", "profileRole", "profileDemands",
  "meetingInput", "contractInput", "policyDemand", "offerInput", "needInput", "targetInput", "scenarioInput",
  "pilotScene", "userRoles", "dataScope", "deployment", "pilotPeriod", "reviewMode",
];

const exampleScenarios = {
  "profile-mall": {
    label: "天河路商圈运营团队",
    fields: {
      profileName: "天河路商圈青年品牌联动运营小组",
      profileIndustry: "现代商贸、品牌零售、餐饮服务、数字营销、商圈运营",
      profileLocation: "天河路商圈 / 商圈运营服务场景",
      profileScale: "运营团队约12人，联合商户约30家，覆盖餐饮、咖啡、潮流零售、文创集合店和生活服务门店。",
      profileStage: "已具备线下经营基础，正在探索数字化营销、会员运营、商户协同和AI辅助办公。",
      profileRole: "商圈运营人员 / 商户联合运营负责人",
      profileDemands: "1. 商户联动活动筹备周期短，会议内容多，任务分工容易遗漏；\n2. 多家商户参与合作，活动协议、宣传权益、费用分摊和违约责任需要提前识别风险；\n3. 团队不熟悉商贸促消费、数字化转型、青年创业、人工智能应用等政策方向；\n4. 商户之间资源分散，缺少清晰的供需标签和合作对接话术；\n5. 希望用AI生成活动执行清单、合同风险提示、政策准备建议和合作方案，形成可归档的运营报告。"
    }
  },
  "profile-cbd": {
    label: "天河CBD专业服务企业",
    fields: {
      profileName: "天河CBD企业服务与专业服务协同团队",
      profileIndustry: "专业服务、科技服务、企业咨询、数字服务、园区企业服务",
      profileLocation: "天河CBD / 商务楼宇 / 园区企业服务窗口",
      profileScale: "核心团队约20人，服务对象包括中小企业、科技企业、商务团队和专业服务机构。",
      profileStage: "已具备企业服务基础，正在提升政策服务、合同材料初筛、企业供需对接和服务台账归档能力。",
      profileRole: "园区服务人员 / 企业服务专员 / 项目管理员",
      profileDemands: "1. 企业咨询事项多，政策需求、合同问题和合作需求分散；\n2. 服务人员需要快速形成初步材料，便于后续人工复核和专业机构跟进；\n3. 希望把企业需求整理为政策方向、供需标签、服务对接建议和实施计划；\n4. 需要形成可归档的企业服务记录，提升窗口服务效率。"
    }
  },
  "meeting-mall": {
    label: "商圈活动筹备会",
    fields: {
      meetingInput: "会议主题：天河路商圈暑期青年品牌联动促消费活动筹备会\n\n会议时间：2026年7月8日 15:00-16:30\n参会人员：商圈运营负责人李经理、市场推广负责人陈璐、法务顾问周律师、商户代表王先生、咖啡品牌负责人林女士、文创店负责人何女士、技术支持负责人赵工。\n\n会议内容：\n1. 本次活动暂定名称为“夏日有礼·智惠天河青年消费季”，计划联合30家商户开展满减优惠、打卡集章、短视频传播和会员积分活动。\n2. 活动时间初步定为2026年8月1日至8月31日，7月15日前完成商户报名，7月20日前确认活动方案，7月25日前完成宣传物料设计。\n3. 市场推广负责人陈璐负责制定统一宣传方案，包括小红书、抖音、公众号推文、商场电子屏海报和线下展架。\n4. 商户代表王先生提出，希望明确各商户的费用承担比例、宣传资源权益、优惠券核销方式和客户数据使用边界。\n5. 法务顾问周律师提醒，商户合作协议中需要明确活动费用、结算周期、违约责任、知识产权归属、顾客投诉处理和数据使用授权。\n6. 技术支持负责人赵工建议引入AI工具，用于整理会议纪要、生成活动执行任务表、检查合作协议风险、生成商户对接话术，并形成每周进展报告。\n7. 初步决定由运营组负责总协调，市场组负责宣传，法务顾问负责协议审阅，技术组负责AI工具配置，各商户需在7月15日前提交参与活动的优惠方案。\n8. 下一次会议定于7月16日下午召开，重点确认商户名单、活动预算、宣传计划和合同模板。"
    }
  },
  "meeting-cbd": {
    label: "CBD企业服务例会",
    fields: {
      meetingInput: "会议主题：天河CBD企业服务窗口月度服务复盘会\n\n参会人员：企业服务中心负责人、政策服务专员、法务合作顾问、数字化服务商代表、楼宇运营代表。\n\n会议内容：\n1. 本月企业咨询集中在政策申报、合同条款初筛、人才服务、办公空间对接和数字化工具选型。\n2. 政策服务专员反馈，部分企业无法准确描述自身行业、规模和申报需求，导致材料准备效率低。\n3. 法务合作顾问建议，合同审阅模块应重点提示付款节点、交付验收、知识产权、数据安全和违约责任。\n4. 楼宇运营代表提出，希望系统能够将企业“我能提供什么”和“我需要什么”整理成供需标签，用于后续资源对接。\n5. 决定下月选择10家企业试用AI工作台，重点测试会议纪要、合同审阅、政策准备和供需协作四个模块。\n6. 服务中心负责收集企业反馈，数字化服务商负责工具配置，法务顾问负责结果复核标准说明。"
    }
  },
  "contract-merchant": {
    label: "商户联动协议",
    fields: {
      contractInput: "天河路商圈品牌联动促消费活动合作协议（节选）\n\n甲方：天河路商圈青年品牌联动运营小组\n乙方：参与活动商户\n\n一、合作内容\n甲方负责组织“夏日有礼·智惠天河青年消费季”活动，乙方自愿参与本次活动，并提供相应优惠、服务或产品。甲方负责统一宣传、活动策划、线上推广和活动统筹，乙方负责门店执行、顾客接待和优惠核销。\n\n二、活动时间\n活动时间暂定为2026年8月1日至2026年8月31日。如因天气、政策、不可抗力或其他原因导致活动延期，甲方有权调整活动安排，乙方应予以配合。\n\n三、费用与结算\n乙方应按照甲方通知缴纳活动服务费，具体金额以后续通知为准。活动期间涉及的优惠补贴、宣传费用、物料费用和第三方服务费用，由甲方根据实际情况另行确定。结算周期原则上为活动结束后30个工作日内完成，但如存在数据核对、顾客投诉或第三方平台延迟等情况，甲方可适当顺延。\n\n四、宣传与知识产权\n甲方可使用乙方门店名称、Logo、产品图片、门店照片和活动素材用于本次活动宣传。乙方提交的图片、视频、文案等素材应保证不侵犯第三方知识产权。活动期间形成的宣传海报、短视频、活动文案、数据报告等成果，归甲方所有。\n\n五、数据使用\n活动过程中产生的顾客报名信息、核销记录、消费数据、会员信息等，由甲方统一收集和管理。甲方可根据活动运营需要进行数据分析、用户画像、后续营销和合作推广。乙方应配合提供必要经营数据。\n\n六、违约责任\n如乙方未按要求执行活动方案，或因服务质量问题造成顾客投诉，甲方有权取消乙方活动资格。因乙方原因造成甲方损失的，乙方应承担赔偿责任。若甲方因活动调整、宣传效果不达预期或第三方平台原因导致乙方收益低于预期，甲方不承担赔偿责任。"
    }
  },
  "contract-ai": {
    label: "AI服务采购条款",
    fields: {
      contractInput: "AI运营工具服务采购协议（节选）\n\n甲方：某园区企业服务中心\n乙方：AI应用服务商\n\n1. 乙方为甲方提供会议纪要生成、合同条款风险提示、政策材料准备、供需协作方案生成和报告导出功能。\n2. 服务周期为3个月试点期，费用分两期支付：合同签署后支付50%，试点结束并通过验收后支付50%。验收标准包括系统可用性、输出结构完整度、响应速度和用户满意度。\n3. 乙方应保证系统支持用户自填API Key，默认不持久化保存企业合同、会议纪要、客户信息和经营数据。\n4. 甲方提供必要业务场景和脱敏测试材料，乙方不得将甲方提供的数据用于其他商业用途或模型训练。\n5. 乙方应在服务期内提供技术支持，重大故障应在24小时内响应。若系统连续三次无法满足约定功能，甲方有权要求整改或暂停付款。\n6. 双方对系统生成内容的使用边界确认如下：AI生成内容仅作为业务辅助材料，不替代法律、财务、政策申报等专业意见，最终结果需由甲方指定人员复核。"
    }
  },
  "policy-ai": {
    label: "AI应用场景与大模型政策",
    fields: {
      policyDemand: "我们是位于天河区的企业服务与AI应用团队，计划将会议纪要、合同审阅、政策材料准备、供需协作和报告归档做成轻量化AI工作台，用于服务园区企业、商圈商户和青年创业团队。希望了解适合关注哪些政策方向，包括人工智能应用场景落地、行业大模型应用、企业数字化转型、算力与模型服务、数据安全合规、创新创业扶持等。请输出政策方向建议、适配理由、材料准备清单、申报注意事项和下一步行动建议。"
    }
  },
  "policy-commerce": {
    label: "商圈促消费与数字化经营",
    fields: {
      policyDemand: "我们是天河路商圈的运营团队，联合多家餐饮、咖啡、文创、零售和生活服务门店，计划开展暑期促消费活动，并引入AI工具辅助活动会议纪要、合作协议风险提示、商户供需对接、营销文案生成和活动复盘报告。希望了解可关注的政策方向，包括商贸促消费、商圈数字化经营、中小企业数字化转型、青年创业、文旅商融合、品牌活动支持等。请给出适配理由、材料准备清单和申报注意事项。"
    }
  },
  "match-mall-ai": {
    label: "商圈找AI服务商",
    fields: {
      offerInput: "我们可以提供天河路商圈线下活动场景、30家左右商户资源、门店客流入口、品牌联动活动组织能力、商户宣传渠道、线下打卡空间和真实消费反馈数据。部分商户愿意参与AI营销、会员运营、智能客服和活动数据分析试点。",
      needInput: "我们需要AI技术服务支持，包括会议纪要自动生成、合同风险提示、商户供需标签整理、活动执行计划生成、营销文案生成、用户反馈整理、活动数据分析和阶段性运营报告导出。",
      targetInput: "AI应用开发团队、数字营销服务商、园区企业服务机构、商圈运营机构、法律顾问、政策咨询机构、短视频运营团队、青年创业服务站、品牌赞助方和高校学生创新团队。",
      scenarioInput: "希望在1个月内完成一次小规模商圈AI运营试点，先选择5-10家商户参与，验证AI工具在会议协同、合同审阅、活动执行、商户对接和报告归档中的实际效果。"
    }
  },
  "match-cbd-service": {
    label: "CBD企业找专业服务",
    fields: {
      offerInput: "我们可以提供天河CBD商务楼宇企业服务入口、企业需求收集渠道、园区活动组织能力、专业服务机构资源和企业服务台账。",
      needInput: "我们需要政策咨询、合同初筛、财税服务、人力资源服务、AI工具服务、数据合规咨询和企业供需对接资源。",
      targetInput: "专业服务机构、AI工具服务商、律师事务所、财税服务机构、人力资源服务商、园区运营机构和产业服务平台。",
      scenarioInput: "围绕企业服务窗口，帮助企业快速整理政策需求、合同风险点、服务需求和合作对象，并形成可复核的服务记录。"
    }
  },
  "landing-mall": {
    label: "商圈AI运营试点",
    fields: {
      pilotScene: "天河路商圈青年品牌联动促消费活动AI运营试点",
      userRoles: "商圈运营人员、商户负责人、市场推广人员、法务顾问、技术服务人员",
      dataScope: "会议记录、商户合作协议关键条款、活动政策需求、商户供需信息、活动执行记录和脱敏反馈数据",
      deployment: "FastAPI网页应用，用户自填API Key，不默认持久化保存业务原文；生成结果由运营负责人和专业人员复核后使用",
      pilotPeriod: "4周小范围试点，首批选择5-10家商户参与",
      reviewMode: "AI生成内容先由运营负责人初审，合同风险由法务顾问复核，政策材料由政策服务人员复核，最终报告归档到活动服务台账"
    }
  },
  "landing-service-window": {
    label: "企业服务窗口试点",
    fields: {
      pilotScene: "天河CBD企业服务窗口AI辅助服务试点",
      userRoles: "园区服务人员、企业服务专员、政策服务专员、法务合作顾问、项目管理员",
      dataScope: "企业咨询记录、政策需求描述、合同关键条款、供需对接信息、服务跟进记录和脱敏企业背景资料",
      deployment: "部署为企业服务窗口内部网页工具，支持用户自填模型API，默认不保存敏感原文，导出材料用于服务记录和人工复核",
      pilotPeriod: "1个月试点，选择10家企业服务案例进行验证",
      reviewMode: "服务专员生成初稿后，由政策、法务或对应专业人员复核；涉及合同、财税、政策申报等内容必须标注AI辅助边界"
    }
  }
};

const REQUEST_TIMEOUT_MS = 180000;

function $(id) { return document.getElementById(id); }
function qsa(sel) { return Array.from(document.querySelectorAll(sel)); }

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
}

function setLoading(button, loading, text) {
  if (!button) return;
  if (loading) {
    button.dataset.oldText = button.textContent;
    button.textContent = text || "生成中...";
    button.classList.add("loading");
    button.disabled = true;
  } else {
    button.textContent = button.dataset.oldText || button.textContent;
    button.classList.remove("loading");
    button.disabled = false;
  }
}

function getConfig() {
  return {
    api_key: sessionStorage.getItem("zhilian_api_key") || $("apiKey").value.trim(),
    base_url: $("baseUrl").value.trim(),
    model: $("modelName").value.trim(),
    temperature: Number($("temperature").value || 0.35),
  };
}

function saveConfig() {
  sessionStorage.setItem("zhilian_api_key", $("apiKey").value.trim());
  localStorage.setItem("zhilian_base_url", $("baseUrl").value.trim());
  localStorage.setItem("zhilian_model", $("modelName").value.trim());
  localStorage.setItem("zhilian_temperature", $("temperature").value);
  localStorage.setItem("zhilian_provider", $("providerSelect").value);
  updateModeBadge();
}

function updateModeBadge() {
  const badge = $("modeBadge");
  const key = $("apiKey").value.trim();
  const homeStatus = $("homeApiStatus");
  const topStatus = $("topApiStatus");
  if (key) {
    badge.textContent = "已配置";
    badge.className = "status-badge ai";
    if (homeStatus) homeStatus.textContent = "已配置";
    if (topStatus) { topStatus.textContent = "API 已配置"; topStatus.className = "top-status ready"; }
  } else {
    badge.textContent = "待配置";
    badge.className = "status-badge local";
    if (homeStatus) homeStatus.textContent = "待配置";
    if (topStatus) { topStatus.textContent = "API 待配置"; topStatus.className = "top-status pending"; }
  }
}

function getIdentityLabel() {
  const org = (state.identity && state.identity.org || "").trim();
  const role = (state.identity && state.identity.role || "").trim();
  if (org && role) return `${org} · ${role}`;
  if (org) return org;
  if (role) return role;
  return "未设置";
}

function renderIdentity() {
  const label = getIdentityLabel();
  if ($("identityDisplay")) $("identityDisplay").textContent = label;
  if ($("homeIdentityStatus")) $("homeIdentityStatus").textContent = label;
  if ($("identityOrg")) $("identityOrg").value = state.identity.org || "";
  if ($("identityRole")) $("identityRole").value = state.identity.role || "企业用户";
  if ($("identityContact")) $("identityContact").value = state.identity.contact || "";
}

function loadIdentity() {
  state.identity = JSON.parse(localStorage.getItem("zhilian_identity") || "{}");
  if (!state.identity.role) state.identity.role = "企业用户";
  renderIdentity();
}

function saveIdentity() {
  state.identity = {
    org: ($("identityOrg")?.value || "").trim(),
    role: ($("identityRole")?.value || "企业用户").trim(),
    contact: ($("identityContact")?.value || "").trim(),
  };
  localStorage.setItem("zhilian_identity", JSON.stringify(state.identity));
  renderIdentity();
}

function openIdentityModal() {
  renderIdentity();
  const modal = $("identityModal");
  modal.classList.add("show");
  modal.setAttribute("aria-hidden", "false");
  setTimeout(() => $("identityOrg")?.focus(), 30);
}

function closeIdentityModal() {
  const modal = $("identityModal");
  modal.classList.remove("show");
  modal.setAttribute("aria-hidden", "true");
}

function requireApiConfig() {
  const cfg = getConfig();
  if (!cfg.api_key || !cfg.base_url || !cfg.model) {
    throw new Error("请先在左侧模型设置中填写 API Key、Base URL 和模型名称。当前版本不提供本地示例生成。");
  }
  return cfg;
}

function getProfile() {
  return {
    name: $("profileName").value.trim(),
    industry: $("profileIndustry").value.trim(),
    location: $("profileLocation").value.trim(),
    scale: $("profileScale").value.trim(),
    stage: $("profileStage").value.trim(),
    contact_role: $("profileRole").value.trim(),
    demands: $("profileDemands").value.trim(),
  };
}

function saveProfileToState() {
  state.profile = getProfile();
  sessionStorage.setItem("zhilian_profile", JSON.stringify(state.profile));
}

function loadProfileFromState() {
  const saved = JSON.parse(sessionStorage.getItem("zhilian_profile") || "{}");
  state.profile = saved;
  $("profileName").value = saved.name || "";
  $("profileIndustry").value = saved.industry || "";
  $("profileLocation").value = saved.location || "";
  $("profileScale").value = saved.scale || "";
  $("profileStage").value = saved.stage || "";
  $("profileRole").value = saved.contact_role || "";
  $("profileDemands").value = saved.demands || "";
}

function getProfileContext() {
  if (state.results.profile) return state.results.profile;
  const profile = state.profile || getProfile();
  const pairs = [
    ["使用单位", state.identity?.org], ["使用身份", state.identity?.role], ["联系人", state.identity?.contact],
    ["名称", profile.name], ["行业", profile.industry], ["场景", profile.location],
    ["规模", profile.scale], ["阶段", profile.stage], ["角色", profile.contact_role], ["需求", profile.demands],
  ].filter(([, value]) => String(value || "").trim());
  if (!pairs.length) return "";
  return pairs.map(([key, value]) => `${key}：${value}`).join("\n");
}

function saveFormState() {
  const data = {};
  formInputIds.forEach(id => {
    const el = $(id);
    if (el) data[id] = el.value;
  });
  sessionStorage.setItem("zhilian_form_inputs", JSON.stringify(data));
}

function loadFormState() {
  const data = JSON.parse(sessionStorage.getItem("zhilian_form_inputs") || "{}");
  formInputIds.forEach(id => {
    const el = $(id);
    if (el && Object.prototype.hasOwnProperty.call(data, id)) el.value = data[id];
  });
  saveProfileToState();
}

function applyExample(exampleKey) {
  const example = exampleScenarios[exampleKey];
  if (!example) {
    toast("未找到该场景示例。");
    return;
  }
  Object.entries(example.fields || {}).forEach(([id, value]) => {
    const el = $(id);
    if (el) el.value = value;
  });
  saveFormState();
  saveProfileToState();
  toast(`已填入示例：${example.label}`);
}

async function apiPost(url, payload) {
  saveConfig();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!resp.ok) {
      const text = await resp.text();
      let detail = text;
      try { detail = JSON.parse(text).detail || text; } catch (_) {}
      throw new Error(detail);
    }
    return await resp.json();
  } catch (err) {
    if (err.name === "AbortError") throw new Error("请求超时，请缩短输入内容或检查模型接口后重试。");
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMarkdown(md) {
  const lines = String(md || "").split(/\r?\n/);
  let html = "";
  let inList = false;
  let tableBuffer = [];

  function flushList() {
    if (inList) { html += "</ul>"; inList = false; }
  }
  function flushTable() {
    if (!tableBuffer.length) return;
    html += "<table>";
    tableBuffer.forEach((row, idx) => {
      const cells = row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(c => c.trim());
      if (idx === 1 && cells.every(c => /^:?-{3,}:?$/.test(c))) return;
      html += idx === 0 ? "<thead><tr>" : "<tr>";
      cells.forEach(c => html += idx === 0 ? `<th>${escapeHtml(c)}</th>` : `<td>${escapeHtml(c)}</td>`);
      html += idx === 0 ? "</tr></thead><tbody>" : "</tr>";
    });
    html += "</tbody></table>";
    tableBuffer = [];
  }

  for (const raw of lines) {
    const line = raw.trim();
    if (line.startsWith("|") && line.endsWith("|")) { flushList(); tableBuffer.push(line); continue; }
    flushTable();
    if (!line) { flushList(); html += "<br/>"; continue; }
    if (line.startsWith("### ")) { flushList(); html += `<h3>${escapeHtml(line.slice(4))}</h3>`; continue; }
    if (line.startsWith("## ")) { flushList(); html += `<h2>${escapeHtml(line.slice(3))}</h2>`; continue; }
    if (line.startsWith("# ")) { flushList(); html += `<h1>${escapeHtml(line.slice(2))}</h1>`; continue; }
    if (line.startsWith("- ")) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${escapeHtml(line.slice(2))}</li>`;
      continue;
    }
    if (/^\d+\.\s/.test(line)) {
      flushList();
      html += `<p>${escapeHtml(line)}</p>`;
      continue;
    }
    if (line.startsWith("> ")) { flushList(); html += `<blockquote>${escapeHtml(line.slice(2))}</blockquote>`; continue; }
    flushList();
    html += `<p>${escapeHtml(line)}</p>`;
  }
  flushList(); flushTable();
  return html;
}

function splitMarkdownSections(md) {
  const lines = String(md || "").split(/\r?\n/);
  const sections = [];
  let current = { title: "核心结论", lines: [] };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (/^##\s+/.test(line)) {
      if (current.lines.join("\n").trim()) sections.push(current);
      current = { title: line.replace(/^##\s+/, "").trim(), lines: [] };
    } else if (/^#\s+/.test(line)) {
      if (current.lines.join("\n").trim()) sections.push(current);
      current = { title: line.replace(/^#\s+/, "").trim(), lines: [] };
    } else {
      current.lines.push(line);
    }
  }
  if (current.lines.join("\n").trim()) sections.push(current);
  return sections.length ? sections : [{ title: "生成结果", lines: [String(md || "")] }];
}

function renderStructuredMarkdown(md) {
  const sections = splitMarkdownSections(md);
  return `<div class="result-body">${sections.map((section, idx) => {
    const content = section.lines.join("\n").trim();
    return `<article class="result-section-card">
      <div class="result-section-title"><span>${String(idx + 1).padStart(2, "0")}</span><h3>${escapeHtml(section.title)}</h3></div>
      <div class="result-section-content">${renderMarkdown(content)}</div>
    </article>`;
  }).join("")}</div>`;
}

function showResult(key, result) {
  const panel = $(`${key}Result`);
  if (!panel) return;
  if (!result || !result.content) {
    panel.className = "result-panel empty";
    panel.textContent = `${resultTitles[key] || "结果"}会显示在这里。`;
    return;
  }
  panel.className = "result-panel";
  const timeText = result.time
    ? new Date(result.time).toLocaleString()
    : new Date().toLocaleTimeString();
  const errorText = result.error ? `<span class="meta-pill danger">调用异常：${escapeHtml(result.error).slice(0, 80)}</span>` : "";
  const title = resultTitles[key] || "生成结果";
  const meta = `
    <div class="result-header">
      <div>
        <p class="result-label">${escapeHtml(title)}</p>
        <h3>${escapeHtml(title)}生成结果</h3>
      </div>
      <div class="result-actions">
        <button class="inline-action copy-result" data-key="${escapeHtml(key)}" type="button">复制结果</button>
        <div class="inline-download-group" role="group" aria-label="下载本模块结果">
          <span class="download-group-label">下载</span>
          <button class="inline-action export-result" data-key="${escapeHtml(key)}" data-format="md" type="button">MD</button>
          <button class="inline-action export-result" data-key="${escapeHtml(key)}" data-format="txt" type="button">TXT</button>
          <button class="inline-action export-result" data-key="${escapeHtml(key)}" data-format="docx" type="button">Word</button>
        </div>
      </div>
    </div>
    <div class="result-meta">
      <span class="meta-pill">${escapeHtml(result.mode || "AI模型模式")}</span>
      <span class="meta-pill">${escapeHtml(timeText)}</span>
      ${errorText}
    </div>`;
  panel.innerHTML = meta + renderStructuredMarkdown(result.content);
}
function setResult(key, result) {
  const time = new Date().toISOString();
  state.results[key] = result.content || "";
  state.meta[key] = { mode: result.mode || "AI模型模式", error: result.error || "", time };
  sessionStorage.setItem("zhilian_results", JSON.stringify(state.results));
  sessionStorage.setItem("zhilian_meta", JSON.stringify(state.meta));
  showResult(key, { ...result, time });
  updateProgress();
  updateModeBadge();
}

function loadResultsFromSession() {
  state.results = JSON.parse(sessionStorage.getItem("zhilian_results") || "{}");
  state.meta = JSON.parse(sessionStorage.getItem("zhilian_meta") || "{}");
  for (const key of [...resultKeys, "report"]) {
    if (state.results[key]) {
      showResult(key, {
        content: state.results[key],
        mode: state.meta[key]?.mode || "已保存结果",
        error: state.meta[key]?.error || "",
        time: state.meta[key]?.time || "",
      });
    }
  }
  updateProgress();
}

function updateProgress() {
  const done = resultKeys.filter(k => Boolean(state.results[k])).length;

  if ($("generatedCount")) $("generatedCount").textContent = `${done} 项`;
  if ($("homeGeneratedCount")) $("homeGeneratedCount").textContent = `${done} 项`;
  if ($("reportDoneCount")) $("reportDoneCount").textContent = `${done}/${resultKeys.length}`;

  const statusList = $("toolStatusList");
  if (statusList) {
    const visibleKeys = ["meeting", "contract", "policy", "match", "profile", "landing", "report"];
    statusList.innerHTML = visibleKeys.map(k => {
      const doneFlag = Boolean(state.results[k]);
      return `<button class="tool-status-item ${doneFlag ? "done" : ""}" data-goto="${k}" type="button">
        <span>${escapeHtml(resultTitles[k])}</span><strong>${doneFlag ? "已生成" : "未生成"}</strong>
      </button>`;
    }).join("");
  }

  qsa(".nav button").forEach(btn => {
    const section = btn.dataset.section;
    const doneFlag = section === "report" ? Boolean(state.results.report) : Boolean(state.results[section]);
    btn.classList.toggle("done", doneFlag);
  });

  qsa("[data-tool-key]").forEach(card => {
    const key = card.dataset.toolKey;
    card.classList.toggle("done", Boolean(state.results[key]));
  });
  updateRecentMaterials();
}

function updateRecentMaterials() {
  const container = $("recentMaterials");
  if (!container) return;
  const items = Object.keys(state.results || {})
    .filter(key => state.results[key] && resultTitles[key])
    .map(key => ({ key, title: resultTitles[key], time: state.meta[key]?.time || "", content: state.results[key] || "" }))
    .sort((a, b) => String(b.time).localeCompare(String(a.time)))
    .slice(0, 5);
  if (!items.length) {
    container.className = "recent-list empty";
    container.textContent = "暂无生成材料。配置 API 后进入业务模块生成内容，这里会自动显示最近材料。";
    return;
  }
  container.className = "recent-list";
  container.innerHTML = items.map(item => {
    const timeText = item.time ? new Date(item.time).toLocaleString() : "当前会话";
    const summary = item.content.replace(/[#*_`|>-]/g, "").replace(/\s+/g, " ").trim().slice(0, 90) || "已生成业务材料";
    return `<article class="recent-item">
      <div class="recent-item-icon">${escapeHtml(item.title.slice(0, 1))}</div>
      <div><h4>${escapeHtml(item.title)}</h4><p>${escapeHtml(timeText)} · ${escapeHtml(summary)}</p></div>
      <button class="secondary small" data-goto="${escapeHtml(item.key)}" type="button">查看</button>
    </article>`;
  }).join("");
}


function go(section) {
  qsa(".page").forEach(p => p.classList.toggle("active-page", p.id === section));
  qsa(".nav button").forEach(b => b.classList.toggle("active", b.dataset.section === section));
  const meta = pageMeta[section] || pageMeta.home;
  if ($("pageKicker")) $("pageKicker").textContent = meta.kicker;
  if ($("pageTitle")) $("pageTitle").textContent = meta.title;
  if ($("pageSubtitle")) $("pageSubtitle").textContent = meta.subtitle;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function collectBaseResults() {
  return {
    "企业档案": state.results.profile || "",
    "会议纪要": state.results.meeting || "",
    "合同审阅": state.results.contract || "",
    "政策准备": state.results.policy || "",
    "供需协作": state.results.match || "",
    "实施计划": state.results.landing || "",
  };
}

function collectResultsForReport(includeAiSummary = false) {
  const base = collectBaseResults();
  if (includeAiSummary && state.results.report) {
    return { "AI整合报告": state.results.report, ...base };
  }
  return base;
}

function collectSingleModuleResult(key) {
  const title = resultTitles[key] || "模块结果";
  const content = state.results[key] || "";
  return { title, results: { [title]: content }, content };
}

async function runProfile(button) {
  saveProfileToState();
  if (!state.profile.name && !state.profile.demands) throw new Error("请至少填写企业名称或当前需求。");
  const res = await apiPost("/api/profile", { config: requireApiConfig(), profile: state.profile });
  setResult("profile", res);
}

async function runMeeting(button) {
  const text = $("meetingInput").value.trim();
  if (text.length < 8) throw new Error("会议内容过短，请补充会议背景、决策或待办事项。");
  const res = await apiPost("/api/meeting", { config: requireApiConfig(), text, profile_summary: getProfileContext() });
  setResult("meeting", res);
}

async function runContract(button) {
  const text = $("contractInput").value.trim();
  if (text.length < 12) throw new Error("合同文本过短，请粘贴关键条款后再生成风险提示。");
  const res = await apiPost("/api/contract", { config: requireApiConfig(), text, profile_summary: getProfileContext() });
  setResult("contract", res);
}

async function runPolicy(button) {
  saveProfileToState();
  const demand = $("policyDemand").value.trim();
  const hasProfile = Object.values(state.profile || {}).some(v => String(v || "").trim());
  if (!demand && !hasProfile) throw new Error("请先填写企业档案或政策需求，系统才能给出更贴合的政策方向建议。");
  const res = await apiPost("/api/policy", { config: requireApiConfig(), profile: state.profile, demand });
  setResult("policy", res);
}

async function runMatch(button) {
  saveProfileToState();
  const payload = {
    config: requireApiConfig(), profile: state.profile,
    offer: $("offerInput").value.trim(),
    need: $("needInput").value.trim(),
    target: $("targetInput").value.trim(),
    scenario: $("scenarioInput").value.trim(),
  };
  if (![payload.offer, payload.need, payload.target, payload.scenario].some(Boolean)) throw new Error("请至少填写供给、需求、目标对象或业务场景中的一项。");
  const res = await apiPost("/api/match", payload);
  setResult("match", res);
}

async function runLanding(button) {
  saveProfileToState();
  const landingInfo = {
    pilot_scene: $("pilotScene").value.trim(),
    user_roles: $("userRoles").value.trim(),
    data_scope: $("dataScope").value.trim(),
    deployment: $("deployment").value.trim(),
    pilot_period: $("pilotPeriod").value.trim(),
    review_mode: $("reviewMode").value.trim(),
  };
  const existing = {
    "企业档案": state.results.profile || "",
    "会议纪要": state.results.meeting || "",
    "合同审阅": state.results.contract || "",
    "政策准备": state.results.policy || "",
    "供需协作": state.results.match || "",
  };
  const res = await apiPost("/api/landing", { config: requireApiConfig(), profile: state.profile, landing_info: landingInfo, existing_results: existing });
  setResult("landing", res);
}

async function runReport(button) {
  const results = collectResultsForReport(false);
  if (!Object.values(results).some(Boolean)) throw new Error("还没有可整合的模块结果，请先完成至少一个模块。");
  const res = await apiPost("/api/report", { config: requireApiConfig(), results, use_ai_summary: true });
  setResult("report", res);
}

async function requestDownload(url, payload, filename, contentType, emptyMessage, timeoutMessage) {
  const hasContent = payload && payload.results && Object.values(payload.results).some(Boolean);
  if (!hasContent) throw new Error(emptyMessage || "还没有可导出的结果。");
  saveConfig();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!resp.ok) {
      const text = await resp.text();
      let detail = text;
      try { detail = JSON.parse(text).detail || text; } catch (_) {}
      throw new Error(detail);
    }
    const blob = await resp.blob();
    const a = document.createElement("a");
    const objectUrl = URL.createObjectURL(new Blob([blob], { type: contentType }));
    a.href = objectUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  } catch (err) {
    if (err.name === "AbortError") throw new Error(timeoutMessage || "导出超时，请稍后重试。");
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function downloadReportFile(url, filename, contentType) {
  const results = collectResultsForReport(true);
  await requestDownload(
    url,
    { config: getConfig(), results, use_ai_summary: false },
    filename,
    contentType,
    "还没有可导出的结果。",
    "报告导出超时，请精简结果内容后重试。",
  );
}

async function downloadModuleFile(key, format) {
  const single = collectSingleModuleResult(key);
  if (!single.content) throw new Error("当前模块还没有生成结果，请先点击生成。");
  const safeTitle = single.title.replace(/[\/:*?"<>|]/g, "_");
  if (format === "md") {
    await requestDownload(
      "/api/report/markdown",
      { config: getConfig(), results: single.results, use_ai_summary: false },
      `${safeTitle}.md`,
      "text/markdown;charset=utf-8",
      "当前模块还没有可导出的结果。",
      "模块导出超时，请稍后重试。",
    );
    return;
  }
  if (format === "txt") {
    await requestDownload(
      "/api/report/txt",
      { config: getConfig(), results: single.results, use_ai_summary: false },
      `${safeTitle}.txt`,
      "text/plain;charset=utf-8",
      "当前模块还没有可导出的结果。",
      "模块导出超时，请稍后重试。",
    );
    return;
  }
  if (format === "docx") {
    await requestDownload(
      "/api/report/docx",
      { config: getConfig(), results: single.results, use_ai_summary: false },
      `${safeTitle}.docx`,
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "当前模块还没有可导出的结果。",
      "模块导出超时，请稍后重试。",
    );
    return;
  }
  throw new Error("不支持的导出格式。");
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

function downloadTextFile(filename, content, contentType = "text/plain;charset=utf-8") {
  const blob = new Blob([content], { type: contentType });
  const a = document.createElement("a");
  const objectUrl = URL.createObjectURL(blob);
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

function attachRun(id, fn, text) {
  $(id).addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    try {
      setLoading(btn, true, text || "生成中...");
      await fn(btn);
      toast("生成完成");
    } catch (err) {
      toast(err.message || String(err));
    } finally {
      setLoading(btn, false);
    }
  });
}

async function initDefaults() {
  const resp = await fetch("/api/defaults");
  state.defaults = await resp.json();
  const providerSelect = $("providerSelect");
  providerSelect.innerHTML = Object.keys(state.defaults.provider_presets).map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");

  const fallbackProvider = "通义千问 DashScope";
  const savedProvider = localStorage.getItem("zhilian_provider") || fallbackProvider;
  const activeProvider = state.defaults.provider_presets[savedProvider] ? savedProvider : fallbackProvider;
  providerSelect.value = activeProvider;
  const preset = state.defaults.provider_presets[activeProvider] || state.defaults.provider_presets[fallbackProvider];
  $("apiKey").value = sessionStorage.getItem("zhilian_api_key") || "";
  $("baseUrl").value = localStorage.getItem("zhilian_base_url") || preset.base_url;
  $("modelName").value = localStorage.getItem("zhilian_model") || preset.model;
  $("temperature").value = localStorage.getItem("zhilian_temperature") || "0.35";
  $("tempValue").textContent = $("temperature").value;
  updateModeBadge();
}

function clearAll() {
  if (!confirm("确认清空当前输入和生成结果吗？API Key 也会从当前会话清除。")) return;
  sessionStorage.removeItem("zhilian_api_key");
  sessionStorage.removeItem("zhilian_profile");
  sessionStorage.removeItem("zhilian_results");
  sessionStorage.removeItem("zhilian_meta");
  sessionStorage.removeItem("zhilian_form_inputs");
  localStorage.removeItem("zhilian_api_panel_collapsed");
  location.reload();
}

function bindEvents() {
  qsa(".nav button").forEach(btn => btn.addEventListener("click", () => go(btn.dataset.section)));
  $("toggleApiPanel").addEventListener("click", () => {
    const panel = $("apiPanel");
    const collapsed = !panel.classList.contains("collapsed");
    panel.classList.toggle("collapsed", collapsed);
    $("toggleApiPanel").textContent = collapsed ? "展开" : "收起";
    $("toggleApiPanel").setAttribute("aria-expanded", String(!collapsed));
    localStorage.setItem("zhilian_api_panel_collapsed", collapsed ? "1" : "0");
  });
  formInputIds.forEach(id => {
    const el = $(id);
    if (el) el.addEventListener("input", () => { saveFormState(); if (id.startsWith("profile")) saveProfileToState(); });
  });
  $("providerSelect").addEventListener("change", () => {
    const preset = state.defaults.provider_presets[$("providerSelect").value];
    $("baseUrl").value = preset.base_url;
    $("modelName").value = preset.model;
    saveConfig();
    toast(preset.tip);
  });
  ["apiKey", "baseUrl", "modelName", "temperature"].forEach(id => $(id).addEventListener("input", () => { $("tempValue").textContent = $("temperature").value; saveConfig(); }));
  $("toggleKey").addEventListener("click", () => { $("apiKey").type = $("apiKey").type === "password" ? "text" : "password"; });
  $("clearKey").addEventListener("click", () => { $("apiKey").value = ""; sessionStorage.removeItem("zhilian_api_key"); updateModeBadge(); toast("已清空当前会话 API Key"); });
  $("clearAll").addEventListener("click", clearAll);
  if ($("openIdentity")) $("openIdentity").addEventListener("click", openIdentityModal);
  if ($("identityChip")) $("identityChip").addEventListener("click", openIdentityModal);
  if ($("closeIdentity")) $("closeIdentity").addEventListener("click", closeIdentityModal);
  if ($("identityModal")) {
    $("identityModal").addEventListener("click", (e) => { if (e.target.id === "identityModal") closeIdentityModal(); });
  }
  if ($("saveIdentity")) $("saveIdentity").addEventListener("click", () => { saveIdentity(); closeIdentityModal(); toast("已保存当前使用身份"); });
  if ($("resetIdentity")) $("resetIdentity").addEventListener("click", () => { localStorage.removeItem("zhilian_identity"); state.identity = { role: "企业用户" }; renderIdentity(); toast("已清除当前使用身份"); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeIdentityModal(); });
  if ($("openApiSettings")) {
    $("openApiSettings").addEventListener("click", () => {
      const panel = $("apiPanel");
      if (panel.classList.contains("collapsed")) {
        panel.classList.remove("collapsed");
        $("toggleApiPanel").textContent = "收起";
        $("toggleApiPanel").setAttribute("aria-expanded", "true");
        localStorage.setItem("zhilian_api_panel_collapsed", "0");
      }
      $("apiKey").focus();
      toast("请在左侧填写并测试模型 API。每个工具都需要 API 才能生成结果。");
    });
  }
  document.addEventListener("click", async (e) => {
    const exampleBtn = e.target.closest(".quick-fill-btn");
    if (exampleBtn) {
      applyExample(exampleBtn.dataset.example);
      return;
    }
    const gotoTarget = e.target.closest("[data-goto]");
    if (gotoTarget) {
      go(gotoTarget.dataset.goto);
    }
    const copyBtn = e.target.closest(".copy-result");
    const exportBtn = e.target.closest(".export-result");
    if (copyBtn) {
      const key = copyBtn.dataset.key;
      try {
        await copyText(state.results[key] || "");
        toast("已复制当前模块结果");
      } catch (err) {
        toast("复制失败，请手动选择结果文本复制。");
      }
    }
    if (exportBtn) {
      const key = exportBtn.dataset.key;
      const format = exportBtn.dataset.format;
      try {
        await downloadModuleFile(key, format);
        toast(`已开始下载${format.toUpperCase()}文件`);
      } catch (err) {
        toast(err.message || String(err));
      }
    }
  });
  $("testConnection").addEventListener("click", async () => {
    const btn = $("testConnection");
    try {
      setLoading(btn, true, "测试中...");
      const res = await apiPost("/api/test-connection", getConfig());
      $("connectionResult").textContent = res.ok ? `连接成功：${res.content || res.mode}` : `连接失败：${res.error}`;
      updateModeBadge();
    } catch (err) { $("connectionResult").textContent = `连接失败：${err.message}`; }
    finally { setLoading(btn, false); }
  });

  attachRun("runProfile", runProfile, "生成画像...");
  attachRun("runMeeting", runMeeting, "生成纪要...");
  attachRun("runContract", runContract, "识别风险...");
  attachRun("runPolicy", runPolicy, "匹配政策...");
  attachRun("runMatch", runMatch, "生成方案...");
  attachRun("runLanding", runLanding, "评估落地...");
  attachRun("runReport", runReport, "整合报告...");

  function attachDownload(id, url, filename, contentType) {
    $(id).addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      try {
        setLoading(btn, true, "导出中...");
        await downloadReportFile(url, filename, contentType);
        toast("报告已开始下载");
      } catch (err) {
        toast(err.message || String(err));
      } finally {
        setLoading(btn, false);
      }
    });
  }

  attachDownload("downloadMarkdown", "/api/report/markdown", "智链天河运营报告.md", "text/markdown;charset=utf-8");
  attachDownload("downloadTxt", "/api/report/txt", "智链天河运营报告.txt", "text/plain;charset=utf-8");
  attachDownload("downloadDocx", "/api/report/docx", "智链天河运营报告.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
}

async function main() {
  await initDefaults();
  bindEvents();
  loadIdentity();
  loadProfileFromState();
  loadFormState();
  if (localStorage.getItem("zhilian_api_panel_collapsed") === "1") {
    $("apiPanel").classList.add("collapsed");
    $("toggleApiPanel").textContent = "展开";
    $("toggleApiPanel").setAttribute("aria-expanded", "false");
  }
  loadResultsFromSession();
}

main().catch(err => toast(err.message || String(err)));
