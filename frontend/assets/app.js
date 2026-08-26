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

const exampleScenarios = {};
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

function requireModelConfig() {
  const controller = window.ZHILINK_MODEL_CONFIG;
  if (!controller || typeof controller.requireRequestConfig !== "function") {
    throw new Error("AI 服务设置仍在初始化，请刷新页面后重试。");
  }
  return controller.requireRequestConfig();
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
}

function closeIdentityModal() {
  const modal = $("identityModal");
  modal.classList.remove("show");
  modal.setAttribute("aria-hidden", "true");
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

function renderInlineMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/__([^_]+)__/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return html;
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
      cells.forEach(c => html += idx === 0 ? `<th>${renderInlineMarkdown(c)}</th>` : `<td>${renderInlineMarkdown(c)}</td>`);
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
    if (line.startsWith("### ")) { flushList(); html += `<h3>${renderInlineMarkdown(line.slice(4))}</h3>`; continue; }
    if (line.startsWith("## ")) { flushList(); html += `<h2>${renderInlineMarkdown(line.slice(3))}</h2>`; continue; }
    if (line.startsWith("# ")) { flushList(); html += `<h1>${renderInlineMarkdown(line.slice(2))}</h1>`; continue; }
    if (line.startsWith("- ")) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${renderInlineMarkdown(line.slice(2))}</li>`;
      continue;
    }
    if (/^\d+\.\s/.test(line)) {
      flushList();
      html += `<p>${renderInlineMarkdown(line)}</p>`;
      continue;
    }
    if (line.startsWith("> ")) { flushList(); html += `<blockquote>${renderInlineMarkdown(line.slice(2))}</blockquote>`; continue; }
    flushList();
    html += `<p>${renderInlineMarkdown(line)}</p>`;
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

function emitResultUpdated(key, result, source) {
  const eventName = window.ZHILINK_WORKSPACE_CONTRACTS?.events?.resultUpdated;
  if (!eventName) return;
  window.dispatchEvent(new CustomEvent(eventName, {
    detail: {
      key,
      result: result || {},
      content: String(result?.content || state.results?.[key] || ""),
      meta: state.meta?.[key] || {},
      source,
    },
  }));
}

function showResult(key, result, source = "render") {
  const panel = $(`${key}Result`);
  if (!panel) return;
  if (!result || !result.content) {
    panel.className = "result-panel empty";
    panel.textContent = `${resultTitles[key] || "结果"}会显示在这里。`;
    emitResultUpdated(key, result || {}, source);
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
  emitResultUpdated(key, result, source);
}

function setResult(key, result) {
  const time = new Date().toISOString();
  state.results[key] = result.content || "";
  state.meta[key] = { mode: result.mode || "AI模型模式", error: result.error || "", time };
  sessionStorage.setItem("zhilian_results", JSON.stringify(state.results));
  sessionStorage.setItem("zhilian_meta", JSON.stringify(state.meta));
  showResult(key, { ...result, time }, "commit");
  updateProgress();
}

function updateStreamingResult(key, content) {
  const target = $(`${key}StreamContent`);
  if (!target) return;
  if (!content.trim()) {
    target.textContent = "正在接收模型输出...";
    return;
  }
  target.innerHTML = renderStructuredMarkdown(content);
}

function finishStreamingResult(key, content, mode = "AI模型流式模式") {
  setResult(key, { ok: true, content, mode, error: "" });
}

function failStreamingResult(key, message) {
  const panel = $(`${key}Result`);
  if (!panel) return;
  const title = resultTitles[key] || "生成结果";
  panel.className = "result-panel";
  panel.innerHTML = `
    <div class="result-header">
      <div>
        <p class="result-label">${escapeHtml(title)}</p>
        <h3>${escapeHtml(title)}生成失败</h3>
      </div>
    </div>
    <div class="result-meta">
      <span class="meta-pill danger">${escapeHtml(message || "流式生成失败")}</span>
    </div>
  `;
}

async function apiStream(url, payload, key) {
  const hooks = window.ZHILINK_WORKSPACE_HOOKS;
  if (!hooks || typeof hooks.runGeneration !== "function") {
    throw new Error("生成控制器未就绪，请刷新页面后重试。");
  }
  return hooks.runGeneration({ url, payload, key });
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

  const eventName = window.ZHILINK_WORKSPACE_CONTRACTS?.events?.progressUpdated;
  if (eventName) {
    window.dispatchEvent(new CustomEvent(eventName, { detail: { done, total: resultKeys.length } }));
  }
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
  const results = includeAiSummary && state.results.report
    ? { "AI整合报告": state.results.report, ...base }
    : base;
  const hooks = window.ZHILINK_WORKSPACE_HOOKS;
  const context = hooks?.runSync?.("results:collect", {
    scope: "report",
    includeAiSummary: Boolean(includeAiSummary),
    results: { ...results },
  });
  return context?.results || results;
}

function collectSingleModuleResult(key) {
  const title = resultTitles[key] || "模块结果";
  const content = state.results[key] || "";
  const result = { title, results: { [title]: content }, content };
  const hooks = window.ZHILINK_WORKSPACE_HOOKS;
  const context = hooks?.runSync?.("results:collect", { scope: "single", key, result });
  return context?.result || result;
}

async function runProfile() {
  saveProfileToState();
  if (!state.profile.name && !state.profile.demands) throw new Error("请至少填写企业名称或当前需求。");
  await apiStream("/api/profile/stream", { config: requireModelConfig(), profile: state.profile }, "profile");
}

async function runMeeting() {
  const text = $("meetingInput").value.trim();
  if (text.length < 8) throw new Error("会议内容过短，请补充会议背景、决策或待办事项。");
  await apiStream("/api/meeting/stream", { config: requireModelConfig(), text, profile_summary: getProfileContext() }, "meeting");
}

async function runContract() {
  const text = $("contractInput").value.trim();
  if (text.length < 12) throw new Error("合同文本过短，请粘贴关键条款后再生成风险提示。");
  await apiStream("/api/contract/stream", { config: requireModelConfig(), text, profile_summary: getProfileContext() }, "contract");
}

async function runPolicy() {
  saveProfileToState();
  const demand = $("policyDemand").value.trim();
  const hasProfile = Object.values(state.profile || {}).some(v => String(v || "").trim());
  if (!demand && !hasProfile) throw new Error("请先填写企业档案或政策需求，系统才能给出更贴合的政策方向建议。");
  await apiStream("/api/policy/stream", { config: requireModelConfig(), profile: state.profile, demand }, "policy");
}

async function runMatch() {
  saveProfileToState();
  const payload = {
    config: requireModelConfig(), profile: state.profile,
    offer: $("offerInput").value.trim(),
    need: $("needInput").value.trim(),
    target: $("targetInput").value.trim(),
    scenario: $("scenarioInput").value.trim(),
  };
  if (![payload.offer, payload.need, payload.target, payload.scenario].some(Boolean)) throw new Error("请至少填写供给、需求、目标对象或业务场景中的一项。");
  await apiStream("/api/match/stream", payload, "match");
}

async function runLanding() {
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
  await apiStream("/api/landing/stream", { config: requireModelConfig(), profile: state.profile, landing_info: landingInfo, existing_results: existing }, "landing");
}

async function runReport() {
  const results = collectResultsForReport(false);
  if (!Object.values(results).some(Boolean)) throw new Error("还没有可整合的模块结果，请先完成至少一个模块。");
  await apiStream("/api/report/stream", { config: requireModelConfig(), results, use_ai_summary: true }, "report");
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
  const controller = window.ZHILINK_MODEL_CONFIG;
  if (!controller || typeof controller.initialize !== "function") {
    throw new Error("AI 服务设置控制器未加载，请刷新页面后重试。");
  }
  controller.initialize(state.defaults);
}

function clearAll() {
  if (!confirm("确认清空当前输入和生成结果吗？API Key 也会从当前会话清除。")) return;
  sessionStorage.removeItem("zhilian_api_key");
  sessionStorage.removeItem("zhilian_profile");
  sessionStorage.removeItem("zhilian_results");
  sessionStorage.removeItem("zhilian_meta");
  sessionStorage.removeItem("zhilian_form_inputs");
  location.reload();
}

function bindEvents() {
  qsa(".nav button").forEach(btn => btn.addEventListener("click", () => go(btn.dataset.section)));
  formInputIds.forEach(id => {
    const el = $(id);
    if (el) el.addEventListener("input", () => { saveFormState(); if (id.startsWith("profile")) saveProfileToState(); });
  });
  $("clearAll").addEventListener("click", clearAll);
  if ($("openIdentity")) $("openIdentity").addEventListener("click", openIdentityModal);
  if ($("identityChip")) $("identityChip").addEventListener("click", openIdentityModal);
  if ($("closeIdentity")) $("closeIdentity").addEventListener("click", closeIdentityModal);
  if ($("identityModal")) {
    $("identityModal").addEventListener("click", (e) => { if (e.target.id === "identityModal") closeIdentityModal(); });
  }
  if ($("saveIdentity")) $("saveIdentity").addEventListener("click", () => { saveIdentity(); closeIdentityModal(); toast("已保存当前使用身份"); });
  if ($("resetIdentity")) $("resetIdentity").addEventListener("click", () => { localStorage.removeItem("zhilian_identity"); state.identity = { role: "企业用户" }; renderIdentity(); toast("已清除当前使用身份"); });
  document.addEventListener("click", (e) => {
    const exampleBtn = e.target.closest(".quick-fill-btn");
    if (exampleBtn) {
      applyExample(exampleBtn.dataset.example);
      return;
    }
    const gotoTarget = e.target.closest("[data-goto]");
    if (gotoTarget) go(gotoTarget.dataset.goto);
  });

  attachRun("runProfile", runProfile, "流式生成中...");
  attachRun("runMeeting", runMeeting, "流式生成中...");
  attachRun("runContract", runContract, "流式生成中...");
  attachRun("runPolicy", runPolicy, "流式生成中...");
  attachRun("runMatch", runMatch, "流式生成中...");
  attachRun("runLanding", runLanding, "流式生成中...");
  attachRun("runReport", runReport, "流式整合中...");
}

async function main() {
  await initDefaults();
  bindEvents();
  loadIdentity();
  loadProfileFromState();
  loadFormState();
  loadResultsFromSession();
}

main().catch(err => toast(err.message || String(err)));
