/* UI V4 forms: consistent business-input hierarchy, guidance and inline validation. */
(() => {
  const VERSION = "20260810.1";
  const PROFILE_FIELDS = ["profileName", "profileIndustry", "profileLocation", "profileScale", "profileStage", "profileRole", "profileDemands"];

  const MODULES = {
    profile: {
      title: "基础资料",
      copy: "不要求全部填写；企业名称或当前需求至少填写一项后即可生成档案。",
      badge: "至少填写 1 项",
      run: "runProfile",
      fields: ["profileName", "profileIndustry", "profileLocation", "profileScale", "profileStage", "profileRole", "profileDemands"],
      primaryFields: ["profileName", "profileDemands"],
    },
    meeting: {
      title: "会议原文",
      copy: "粘贴会议记录或录音转写文本，尽量保留明确决定、负责人和时间节点。",
      badge: "必填",
      run: "runMeeting",
      fields: ["meetingInput"],
      primaryFields: ["meetingInput"],
    },
    contract: {
      title: "审阅材料",
      copy: "建议先脱敏姓名、电话、账号等信息，再粘贴需要审阅的合同或协议关键条款。",
      badge: "必填",
      run: "runContract",
      fields: ["contractInput"],
      primaryFields: ["contractInput"],
    },
    policy: {
      title: "本次政策需求",
      copy: "可直接描述本次关注方向；如已维护企业档案，可只补充当前政策诉求。",
      badge: "需求或档案至少一项",
      run: "runPolicy",
      fields: ["policyDemand"],
      primaryFields: ["policyDemand"],
    },
    match: {
      title: "供需条件",
      copy: "供给、需求、目标对象和业务场景至少填写一项；信息越具体，协作建议越容易执行。",
      badge: "至少填写 1 项",
      run: "runMatch",
      fields: ["offerInput", "needInput", "targetInput", "scenarioInput"],
      primaryFields: ["offerInput", "needInput", "targetInput", "scenarioInput"],
    },
    landing: {
      title: "试点配置",
      copy: "按当前已知信息填写即可；尚未确定的内容可以留空，并在生成结果中继续人工补充。",
      badge: "按需填写",
      run: "runLanding",
      fields: ["pilotScene", "userRoles", "dataScope", "deployment", "pilotPeriod", "reviewMode"],
      primaryFields: [],
    },
  };

  const FIELD_HELP = {
    profileName: "用于档案标题和后续业务上下文识别。",
    profileDemands: "说明当前最需要解决的运营问题，便于后续模块理解业务背景。",
    meetingInput: "建议包含会议主题、参会人员、讨论事项、明确决定、负责人和时间节点。",
    contractInput: "只需粘贴需要判断的关键条款；本模块提供商务风险提示，不替代专业法律意见。",
    policyDemand: "例如政策方向、申报准备、适配条件、材料清单或时间节点。",
    offerInput: "填写可开放的场景、渠道、客户触点、产品或服务能力。",
    needInput: "描述本次希望解决的业务问题、资源缺口或采购需求。",
    targetInput: "填写希望对接的企业类型、服务机构或合作伙伴类型。",
    scenarioInput: "说明合作发生的具体业务场景和目标。",
    pilotScene: "说明本次试点要在哪个业务环节落地。",
    userRoles: "填写实际使用系统和负责人工复核的角色。",
    dataScope: "明确允许进入试点的数据类型和敏感信息边界。",
    deployment: "说明系统部署位置、模型接口和数据保存方式。",
    pilotPeriod: "填写计划验证周期，不确定时可先留空。",
    reviewMode: "说明谁负责复核 AI 输出，以及哪些结果必须人工确认。",
  };

  const FIELD_BADGES = {
    meetingInput: "必填",
    contractInput: "必填",
  };

  function byId(id) { return document.getElementById(id); }

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-forms]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-forms.css?v=${VERSION}`;
    link.dataset.uiV4Forms = "true";
    document.head.appendChild(link);
  }

  function value(id) {
    const field = byId(id);
    return String(field?.value || "").trim();
  }

  function extractLabelText(label, control) {
    const parts = [];
    Array.from(label.childNodes).forEach(node => {
      if (node === control) return;
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) parts.push(node.textContent.trim());
    });
    return parts.join(" ").trim();
  }

  function describedBy(field, id) {
    const current = String(field.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
    if (!current.includes(id)) current.push(id);
    field.setAttribute("aria-describedby", current.join(" "));
  }

  function decorateField(id) {
    const field = byId(id);
    const label = field?.closest("label");
    if (!(field instanceof HTMLElement) || !(label instanceof HTMLElement)) return;
    if (!label.closest(".ui-v4-workspace-page")) return;
    if (label.dataset.uiV4FieldReady === "true") return;

    label.dataset.uiV4FieldReady = "true";
    label.classList.add("ui-v4-field");
    field.classList.add("ui-v4-business-control");

    const title = extractLabelText(label, field) || field.getAttribute("aria-label") || id;
    Array.from(label.childNodes).forEach(node => {
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) node.textContent = "";
    });

    const head = document.createElement("span");
    head.className = "ui-v4-field-head";
    const titleEl = document.createElement("span");
    titleEl.className = "ui-v4-field-title";
    titleEl.textContent = title;
    head.appendChild(titleEl);

    const badgeText = FIELD_BADGES[id];
    if (badgeText) {
      const badge = document.createElement("span");
      badge.className = "ui-v4-field-badge required";
      badge.textContent = badgeText;
      head.appendChild(badge);
      field.setAttribute("aria-required", "true");
    }
    label.insertBefore(head, label.firstChild);

    const helper = document.createElement("span");
    helper.className = "ui-v4-field-helper";
    helper.id = `${id}UiV4Help`;
    helper.textContent = FIELD_HELP[id] || "按当前已知信息填写即可。";

    const footer = document.createElement("span");
    footer.className = "ui-v4-field-footer";
    footer.appendChild(helper);

    if (field instanceof HTMLTextAreaElement) {
      const count = document.createElement("span");
      count.className = "ui-v4-char-count";
      count.id = `${id}UiV4Count`;
      count.setAttribute("aria-hidden", "true");
      footer.appendChild(count);
    }
    label.appendChild(footer);

    const error = document.createElement("span");
    error.className = "ui-v4-field-error";
    error.id = `${id}UiV4Error`;
    error.hidden = true;
    label.appendChild(error);

    describedBy(field, helper.id);
    describedBy(field, error.id);
    updateFieldCount(id);
  }

  function updateFieldCount(id) {
    const field = byId(id);
    const counter = byId(`${id}UiV4Count`);
    if (!(field instanceof HTMLTextAreaElement) || !counter) return;
    const length = field.value.length;
    counter.textContent = length ? `${length.toLocaleString("zh-CN")} 字符` : "0 字符";
  }

  function setFieldError(id, message) {
    const field = byId(id);
    const error = byId(`${id}UiV4Error`);
    const label = field?.closest("label.ui-v4-field");
    if (!(field instanceof HTMLElement) || !(error instanceof HTMLElement) || !(label instanceof HTMLElement)) return;
    const active = Boolean(message);
    field.setAttribute("aria-invalid", active ? "true" : "false");
    label.classList.toggle("ui-v4-field-invalid", active);
    error.hidden = !active;
    error.textContent = active ? message : "";
  }

  function setGroupError(section, message) {
    const page = byId(section);
    const target = page?.querySelector(".ui-v4-form-message");
    if (!(target instanceof HTMLElement)) return;
    const active = Boolean(message);
    target.hidden = !active;
    target.textContent = active ? message : "";
    target.setAttribute("role", active ? "alert" : "status");
  }

  function hasProfileContext() {
    return PROFILE_FIELDS.some(id => Boolean(value(id)));
  }

  function validate(section, { showErrors = true } = {}) {
    const config = MODULES[section];
    if (!config) return { valid: true, first: null, message: "" };
    config.fields.forEach(id => setFieldError(id, ""));
    setGroupError(section, "");

    let valid = true;
    let first = null;
    let message = "";

    if (section === "meeting" && value("meetingInput").length < 8) {
      valid = false;
      first = byId("meetingInput");
      message = "会议内容较短，请补充会议背景、明确决定或待办事项。";
      if (showErrors) setFieldError("meetingInput", message);
    } else if (section === "contract" && value("contractInput").length < 12) {
      valid = false;
      first = byId("contractInput");
      message = "请粘贴更完整的合同或协议关键条款后再生成风险提示。";
      if (showErrors) setFieldError("contractInput", message);
    } else if (section === "profile" && !value("profileName") && !value("profileDemands")) {
      valid = false;
      first = byId("profileName");
      message = "企业名称或当前需求至少填写一项。";
      if (showErrors) setGroupError(section, message);
    } else if (section === "policy" && !value("policyDemand") && !hasProfileContext()) {
      valid = false;
      first = byId("policyDemand");
      message = "请填写本次政策需求，或先维护企业档案。";
      if (showErrors) setFieldError("policyDemand", message);
    } else if (section === "match" && !config.fields.some(id => Boolean(value(id)))) {
      valid = false;
      first = byId("offerInput");
      message = "供给、需求、目标对象或业务场景至少填写一项。";
      if (showErrors) setGroupError(section, message);
    }

    return { valid, first, message };
  }

  function readinessText(section) {
    const result = validate(section, { showErrors: false });
    if (section === "landing") {
      const filled = MODULES.landing.fields.filter(id => Boolean(value(id))).length;
      return filled ? `已填写 ${filled}/6 项，可生成后继续补充` : "可直接生成；建议补充试点场景与复核机制";
    }
    return result.valid ? "输入已准备，可开始生成" : result.message;
  }

  function updateReadiness(section) {
    const page = byId(section);
    const status = page?.querySelector(".ui-v4-form-readiness");
    if (!(status instanceof HTMLElement)) return;
    const result = validate(section, { showErrors: false });
    status.textContent = readinessText(section);
    status.dataset.state = result.valid || section === "landing" ? "ready" : "pending";
  }

  function insertSectionHeader(section) {
    const config = MODULES[section];
    const page = byId(section);
    const card = page?.querySelector(".content-card");
    if (!config || !(card instanceof HTMLElement) || card.querySelector(".ui-v4-form-section-head")) return;

    const fields = config.fields.map(id => byId(id)).filter(Boolean);
    if (!fields.length) return;
    const firstLabel = fields[0].closest("label");
    const group = firstLabel?.closest(".form-grid") || firstLabel;
    if (!(group instanceof HTMLElement)) return;

    const head = document.createElement("div");
    head.className = "ui-v4-form-section-head";
    const copyWrap = document.createElement("div");
    const title = document.createElement("h4");
    title.textContent = config.title;
    const copy = document.createElement("p");
    copy.textContent = config.copy;
    copyWrap.append(title, copy);
    const badge = document.createElement("span");
    badge.className = "ui-v4-form-section-badge";
    badge.textContent = config.badge;
    head.append(copyWrap, badge);
    group.parentElement?.insertBefore(head, group);

    const message = document.createElement("div");
    message.className = "ui-v4-form-message";
    message.hidden = true;
    message.setAttribute("aria-live", "polite");
    group.parentElement?.insertBefore(message, group.nextSibling);
  }

  function decorateActions(section) {
    const config = MODULES[section];
    const page = byId(section);
    const actions = page?.querySelector(".sticky-actions");
    if (!config || !(actions instanceof HTMLElement)) return;
    actions.classList.add("ui-v4-form-actions");
    if (!actions.querySelector(".ui-v4-form-readiness")) {
      const status = document.createElement("span");
      status.className = "ui-v4-form-readiness";
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      actions.insertBefore(status, actions.firstChild);
    }
    updateReadiness(section);
  }

  function decorateExamples(page) {
    page.querySelectorAll(".quick-fill-bar").forEach(bar => {
      bar.classList.add("ui-v4-example-bar");
      const label = bar.querySelector("span");
      if (label) label.textContent = "示例填充";
      bar.querySelectorAll(".quick-fill-btn").forEach(button => {
        button.setAttribute("title", "使用示例数据填充当前表单");
        button.setAttribute("aria-label", `使用示例：${button.textContent.trim()}`);
      });
    });
  }

  function decorateModule(section) {
    const page = byId(section);
    if (!(page instanceof HTMLElement)) return;
    page.classList.add("ui-v4-form-page");
    const config = MODULES[section];
    config.fields.forEach(decorateField);
    insertSectionHeader(section);
    decorateActions(section);
    decorateExamples(page);
  }

  function handleInput(event) {
    const field = event.target;
    if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement)) return;
    const page = field.closest(".ui-v4-form-page");
    if (!page?.id || !MODULES[page.id]) return;
    updateFieldCount(field.id);
    setFieldError(field.id, "");
    setGroupError(page.id, "");
    updateReadiness(page.id);
  }

  function handleRunClick(event) {
    const button = event.target.closest?.("button");
    if (!(button instanceof HTMLButtonElement)) return;
    const section = Object.keys(MODULES).find(key => MODULES[key].run === button.id);
    if (!section) return;
    const result = validate(section, { showErrors: true });
    updateReadiness(section);
    if (!result.valid && result.first instanceof HTMLElement) {
      window.setTimeout(() => result.first.focus({ preventScroll: false }), 0);
    }
  }

  function refreshExample(section) {
    const config = MODULES[section];
    if (!config) return;
    config.fields.forEach(id => updateFieldCount(id));
    config.fields.forEach(id => setFieldError(id, ""));
    setGroupError(section, "");
    updateReadiness(section);
  }

  function start() {
    ensureStyles();
    Object.keys(MODULES).forEach(decorateModule);
    document.addEventListener("input", handleInput, true);
    document.addEventListener("change", handleInput, true);
    document.addEventListener("click", event => {
      handleRunClick(event);
      const example = event.target.closest?.(".quick-fill-btn");
      const page = example?.closest?.(".ui-v4-form-page");
      if (example && page?.id) requestAnimationFrame(() => refreshExample(page.id));
    }, true);
    document.body.classList.add("ui-v4-forms");
    window.ZHILINK_UI_V4_FORMS_READY = true;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
