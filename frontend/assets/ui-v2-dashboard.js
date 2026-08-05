/* UI V2: scalable icon system, real AI status card, and context-aware recommendations. */
(() => {
  const READY_EVENT = "zhilink:ui-v2-ready";
  const MODULES = {
    home: { label: "运营总览", tone: "blue", icon: "home" },
    meeting: { label: "会议纪要", tone: "blue", icon: "meeting" },
    contract: { label: "合同审阅", tone: "violet", icon: "contract" },
    policy: { label: "政策助手", tone: "amber", icon: "policy" },
    match: { label: "供需协作", tone: "green", icon: "match" },
    profile: { label: "企业档案", tone: "indigo", icon: "profile" },
    landing: { label: "实施计划", tone: "cyan", icon: "plan" },
    report: { label: "报告归档", tone: "slate", icon: "report" },
  };

  const ICONS = {
    home: '<svg viewBox="0 0 24 24"><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5M9 20v-6h6v6"/></svg>',
    meeting: '<svg viewBox="0 0 24 24"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 12h6M9 16h4"/><path d="M4 9.5a3 3 0 0 1 6 0v1a3 3 0 0 1-6 0z"/><path d="M7 13.5v2M5 15.5h4"/></svg>',
    contract: '<svg viewBox="0 0 24 24"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 11h5M9 15h3"/><circle cx="15.5" cy="15.5" r="4"/><path d="m18.5 18.5 2 2M14.2 15.5l1 1 1.8-2"/></svg>',
    policy: '<svg viewBox="0 0 24 24"><path d="M4 9h16M6 9V7l6-3 6 3v2M7 9v8M11 9v8M15 9v8M19 17H5v3h14z"/><path d="m18.5 4.5.5 1 .9.4-.9.4-.5 1-.4-1-.9-.4.9-.4z"/></svg>',
    match: '<svg viewBox="0 0 24 24"><path d="M8.5 12.5 11 15a2.4 2.4 0 0 0 3.4 0l4.1-4.1"/><path d="m9.5 8.5 2-2a2.8 2.8 0 0 1 4 0l4 4-3 3"/><path d="m14.5 8.5-2-2a2.8 2.8 0 0 0-4 0l-4 4 4 4"/><path d="M3 9h3M18 9h3M6 18h12"/></svg>',
    profile: '<svg viewBox="0 0 24 24"><path d="M4 20V8h8v12M12 20V4h8v16"/><path d="M7 11h2M7 14h2M15 7h2M15 10h2M15 13h2"/><circle cx="8" cy="5" r="2.5"/></svg>',
    plan: '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M7 3v4M17 3v4M3.5 9h17"/><path d="m7 14 2 2 4-4 4 4"/></svg>',
    report: '<svg viewBox="0 0 24 24"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 17v-3M12 17v-6M15 17v-4"/><path d="M8.5 9h3"/></svg>',
    project: '<svg viewBox="0 0 24 24"><path d="M3.5 6.5h6l2 2h9v11h-17z"/><path d="M8 13h8M8 16h5"/></svg>',
    knowledge: '<svg viewBox="0 0 24 24"><path d="M4.5 4.5h6A3.5 3.5 0 0 1 14 8v12a3.5 3.5 0 0 0-3.5-3.5h-6z"/><path d="M19.5 4.5h-2A3.5 3.5 0 0 0 14 8v12a3.5 3.5 0 0 1 3.5-3.5h2z"/></svg>',
    account: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>',
    ai: '<svg viewBox="0 0 24 24"><rect x="5" y="5" width="14" height="14" rx="4"/><path d="M9 10h.01M15 10h.01M9 15c1.8 1.3 4.2 1.3 6 0M8 2v3M16 2v3M8 19v3M16 19v3M2 8h3M19 8h3M2 16h3M19 16h3"/></svg>',
    sparkles: '<svg viewBox="0 0 24 24"><path d="m12 3 1.2 3.2L16.5 8l-3.3 1.8L12 13l-1.2-3.2L7.5 8l3.3-1.8zM18 13l.8 2.2L21 16l-2.2.8L18 19l-.8-2.2L15 16l2.2-.8zM6 14l.8 2.2L9 17l-2.2.8L6 20l-.8-2.2L3 17l2.2-.8z"/></svg>',
    pending: '<svg viewBox="0 0 24 24"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 11h5M9 15h3"/><circle cx="17" cy="17" r="4"/><path d="M17 15v2l1.3 1"/></svg>',
    security: '<svg viewBox="0 0 24 24"><path d="M12 3 19 6v5c0 4.7-2.8 8-7 10-4.2-2-7-5.3-7-10V6z"/><path d="m9 12 2 2 4-4"/></svg>',
    configure: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"/></svg>',
    arrow: '<svg viewBox="0 0 24 24"><path d="M5 12h14M14 7l5 5-5 5"/></svg>',
    check: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/></svg>',
  };

  let queued = false;
  let observer = null;

  function icon(name, className = "") {
    const source = ICONS[name] || ICONS.sparkles;
    return source.replace("<svg ", `<svg class="${className}" aria-hidden="true" focusable="false" `);
  }

  function injectStyles() {
    if (document.querySelector("link[data-ui-v2-dashboard]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/assets/ui-v2-dashboard.css";
    link.dataset.uiV2Dashboard = "true";
    document.head.appendChild(link);
  }

  function text(id) {
    return document.getElementById(id)?.textContent?.trim() || "";
  }

  function isPendingModel() {
    const value = `${text("homeApiStatus")} ${text("topApiStatus")} ${text("modeBadge")}`;
    return !value || /待|未|配置|不可用|失败/.test(value);
  }

  function generatedCount() {
    const match = `${text("homeGeneratedCount")} ${text("generatedCount")}`.match(/\d+/);
    return match ? Number(match[0]) : 0;
  }

  function profileComplete() {
    const required = ["profileName", "profileIndustry", "profileLocation", "profileDemands"];
    return required.filter(id => document.getElementById(id)?.value?.trim()).length >= 3;
  }

  function pendingCount() {
    const direct = text("livePendingCount").match(/\d+/);
    if (direct) return Number(direct[0]);
    const candidates = document.querySelectorAll("[data-review-status='pending'], .review-status-pending, .pending-confirmation-item");
    return candidates.length;
  }

  function trigger(id) {
    const target = document.getElementById(id);
    if (target) target.click();
  }

  function goSection(section) {
    if (typeof window.go === "function") window.go(section);
    else document.querySelector(`[data-section="${section}"]`)?.click();
  }

  function decorateSidebar() {
    document.querySelectorAll(".nav button[data-section]").forEach(button => {
      const section = button.dataset.section;
      const config = MODULES[section];
      if (!config) return;
      button.dataset.v2Tone = config.tone;
      const holder = button.querySelector("span");
      if (!holder) return;
      holder.className = "ui-v2-nav-icon";
      holder.innerHTML = icon(config.icon);
    });
  }

  function decorateTopNavigation() {
    const mappings = [
      ["liveProjectNav", "project"],
      ["liveKnowledgeNav", "knowledge"],
      ["liveReportNav", "report"],
    ];
    mappings.forEach(([id, name]) => {
      const button = document.getElementById(id);
      if (!button || button.dataset.uiV2Icon === "true") return;
      const existing = button.querySelector("svg");
      if (existing) existing.outerHTML = icon(name, "ui-v2-top-icon");
      else button.insertAdjacentHTML("afterbegin", icon(name, "ui-v2-top-icon"));
      button.dataset.uiV2Icon = "true";
    });
    const avatar = document.querySelector(".live-account-avatar");
    if (avatar && avatar.dataset.uiV2Icon !== "true") {
      avatar.innerHTML = icon("account");
      avatar.dataset.uiV2Icon = "true";
    }
  }

  function decorateModuleCards() {
    document.querySelectorAll("#home .module-card[data-tool-key]").forEach(card => {
      const key = card.dataset.toolKey;
      const config = MODULES[key];
      if (!config) return;
      card.dataset.v2Tone = config.tone;
      card.classList.add("ui-v2-module-card");
      const holder = card.querySelector(".module-icon");
      if (holder) {
        holder.className = "module-icon ui-v2-module-icon";
        holder.innerHTML = icon(config.icon);
      }
      const button = card.querySelector(".module-footer button");
      if (button && !button.querySelector("svg")) button.insertAdjacentHTML("beforeend", icon("arrow"));
    });
  }

  function buildStatusCard() {
    const card = document.querySelector("#home .readiness-card");
    if (!card) return;
    if (!document.getElementById("uiV2StatusCard")) {
      Array.from(card.children).forEach(child => child.classList.add("ui-v2-status-source"));
      const panel = document.createElement("div");
      panel.id = "uiV2StatusCard";
      panel.className = "ui-v2-status-card";
      panel.innerHTML = `
        <div class="ui-v2-status-title">
          <span class="ui-v2-status-title-icon">${icon("ai")}</span>
          <div><span>AI 工作状态</span><small>实时读取当前工作台</small></div>
          <span id="uiV2ModelBadge" class="ui-v2-model-badge">待配置</span>
        </div>
        <button id="uiV2ModelAction" class="ui-v2-model-action" type="button">
          <span class="ui-v2-model-orb">${icon("sparkles")}</span>
          <span><strong id="uiV2ModelTitle">配置 AI 模型</strong><small id="uiV2ModelHint">完成连接测试后即可开始生成</small></span>
          ${icon("arrow")}
        </button>
        <div class="ui-v2-status-grid">
          <div><span>${icon("account")}使用身份</span><strong id="uiV2Identity">企业用户</strong></div>
          <div><span>${icon("report")}生成材料</span><strong id="uiV2Generated">0 项</strong></div>
          <div><span>${icon("security")}数据边界</span><strong>会话级保存</strong></div>
        </div>
        <p class="ui-v2-status-note" id="uiV2StatusNote">模型未配置，先完成 API 设置。</p>`;
      card.appendChild(panel);
      panel.querySelector("#uiV2ModelAction")?.addEventListener("click", () => {
        const live = document.querySelector("[data-live-account='api']");
        if (live) live.click();
        else trigger("openApiSettings");
      });
    }
    syncStatusCard();
  }

  function syncStatusCard() {
    const pending = isPendingModel();
    const badge = document.getElementById("uiV2ModelBadge");
    const action = document.getElementById("uiV2ModelAction");
    if (!badge || !action) return;
    badge.textContent = pending ? "待配置" : "运行正常";
    badge.dataset.state = pending ? "pending" : "ready";
    action.dataset.state = pending ? "pending" : "ready";
    document.getElementById("uiV2ModelTitle").textContent = pending ? "配置 AI 模型" : "AI 模型已连接";
    document.getElementById("uiV2ModelHint").textContent = pending ? "完成连接测试后即可开始生成" : "点击可查看或调整模型配置";
    document.getElementById("uiV2Identity").textContent = text("homeIdentityStatus") || text("identityDisplay") || "企业用户";
    document.getElementById("uiV2Generated").textContent = `${generatedCount()} 项`;
    document.getElementById("uiV2StatusNote").textContent = pending
      ? "模型未配置，先完成 API 设置后再处理业务材料。"
      : "AI 服务可用，生成结果仍需由业务负责人复核。";
  }

  function recommendationData() {
    const items = [];
    const modelPending = isPendingModel();
    const generated = generatedCount();
    const pending = pendingCount();

    if (modelPending) {
      items.push({ icon: "configure", tone: "amber", eyebrow: "开始前准备", title: "先连接 AI 模型", text: "完成 API 配置和连接测试，才能生成真实业务材料。", action: "配置模型", run: () => trigger("openApiSettings") });
    }
    if (!profileComplete()) {
      items.push({ icon: "profile", tone: "blue", eyebrow: "提升生成质量", title: "完善企业档案", text: "补充行业、所在场景和当前需求，让政策与实施建议更贴合。", action: "完善档案", run: () => goSection("profile") });
    }
    if (pending > 0) {
      items.push({ icon: "pending", tone: "violet", eyebrow: "人工复核", title: `处理 ${pending} 项待确认内容`, text: "核对 AI 推断、责任人、时间和政策适用条件后再归档。", action: "查看项目", run: () => trigger("openProjectManager") });
    }
    if (!modelPending && generated === 0) {
      items.push({ icon: "meeting", tone: "green", eyebrow: "推荐首个任务", title: "从会议纪要开始", text: "粘贴一段真实会议记录，快速体验摘要、决策和待办整理。", action: "开始处理", run: () => goSection("meeting") });
    }
    if (generated > 0) {
      items.push({ icon: "report", tone: "cyan", eyebrow: "成果归档", title: `汇总当前 ${generated} 份材料`, text: "进入报告归档，复核后导出 Markdown、TXT 或 Word。", action: "查看报告", run: () => goSection("report") });
    }
    if (items.length < 3 && !modelPending) {
      items.push({ icon: "policy", tone: "amber", eyebrow: "天河企业服务", title: "检索官方政策依据", text: "使用企业画像定位政策方向，并查看官方来源和原文摘录。", action: "政策助手", run: () => goSection("policy") });
    }
    return items.slice(0, 3);
  }

  function buildRecommendations() {
    const home = document.getElementById("home");
    const toolbar = home?.querySelector(".section-toolbar");
    if (!home || !toolbar) return;
    let section = document.getElementById("uiV2Recommendations");
    if (!section) {
      section = document.createElement("section");
      section.id = "uiV2Recommendations";
      section.className = "ui-v2-recommendations";
      section.innerHTML = `
        <div class="ui-v2-recommend-head">
          <div class="ui-v2-recommend-heading"><span>${icon("sparkles")}</span><div><h3>AI 智能推荐</h3><p>根据当前工作台状态给出下一步建议，不使用虚构业务数据。</p></div></div>
          <span class="ui-v2-recommend-badge">实时建议</span>
        </div>
        <div id="uiV2RecommendGrid" class="ui-v2-recommend-grid"></div>`;
      toolbar.parentNode.insertBefore(section, toolbar);
    }
    const grid = document.getElementById("uiV2RecommendGrid");
    if (!grid) return;
    const data = recommendationData();
    const signature = JSON.stringify(data.map(item => [item.title, item.text, item.action]));
    if (grid.dataset.signature === signature) return;
    grid.dataset.signature = signature;
    grid.innerHTML = "";
    data.forEach(item => {
      const article = document.createElement("article");
      article.className = "ui-v2-recommend-card";
      article.dataset.tone = item.tone;
      article.innerHTML = `
        <span class="ui-v2-recommend-icon">${icon(item.icon)}</span>
        <div class="ui-v2-recommend-copy"><small>${item.eyebrow}</small><h4>${item.title}</h4><p>${item.text}</p></div>
        <button type="button"><span>${item.action}</span>${icon("arrow")}</button>`;
      article.querySelector("button")?.addEventListener("click", item.run);
      grid.appendChild(article);
    });
  }

  function enhanceHero() {
    const visual = document.querySelector("#home .hero-visual");
    if (!visual || document.getElementById("uiV2HeroBadge")) return;
    const badge = document.createElement("div");
    badge.id = "uiV2HeroBadge";
    badge.className = "ui-v2-hero-badge";
    badge.innerHTML = `<span>${icon("sparkles")}</span><div><strong>企业运营智能中枢</strong><small>生成 · 审核 · 归档</small></div>`;
    visual.appendChild(badge);
  }

  function apply() {
    injectStyles();
    document.body.classList.add("ui-v2-dashboard");
    decorateSidebar();
    decorateTopNavigation();
    decorateModuleCards();
    buildStatusCard();
    buildRecommendations();
    enhanceHero();
    syncStatusCard();
  }

  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      apply();
    });
  }

  function init() {
    apply();
    observer = new MutationObserver(schedule);
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "hidden"] });
    ["input", "change", "click"].forEach(name => document.addEventListener(name, schedule, true));
    window.addEventListener("storage", schedule);
    window.addEventListener("zhilink:account-ready", schedule);
    window.addEventListener("beforeunload", () => observer?.disconnect(), { once: true });
    window.dispatchEvent(new CustomEvent(READY_EVENT));
  }

  window.ZHILINK_UI_V2_READY = true;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else window.setTimeout(init, 0);
})();
