/* Professional model configuration drawer for UI V4. */
(() => {
  const VERSION = "20260810.3";
  let observer = null;

  function ensureStyles() {
    if (document.querySelector("link[data-api-drawer-v4]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/api-drawer-v4.css?v=${VERSION}`;
    link.dataset.apiDrawerV4 = "true";
    document.head.appendChild(link);
  }
  function closeDrawer() {
    document.body.classList.remove("ui-v4-api-open");
    syncOpenState();
  }
  function syncOpenState() {
    const panel = document.getElementById("apiPanel");
    if (!panel) return;
    const open = document.body.classList.contains("ui-v4-api-open");
    panel.setAttribute("aria-hidden", String(!open));
    document.getElementById("uiV4ApiBackdrop")?.setAttribute("aria-hidden", String(!open));
    if (open) window.setTimeout(() => document.getElementById("apiKey")?.focus(), 30);
  }
  function ensureBackdrop() {
    if (document.getElementById("uiV4ApiBackdrop")) return;
    const backdrop = document.createElement("div");
    backdrop.id = "uiV4ApiBackdrop";
    backdrop.className = "ui-v4-api-backdrop";
    backdrop.setAttribute("aria-hidden", "true");
    backdrop.addEventListener("click", closeDrawer);
    document.body.appendChild(backdrop);
  }
  function makeField({ label, input, helper, action, valueNode = null }) {
    const field = document.createElement("section");
    field.className = "api-drawer-field";
    const head = document.createElement("div");
    head.className = "api-drawer-field-head";
    const labelElement = document.createElement("label");
    labelElement.textContent = label;
    if (input?.id) labelElement.htmlFor = input.id;
    head.appendChild(labelElement);
    if (valueNode) {
      valueNode.classList.add("api-temperature-value");
      head.appendChild(valueNode);
    }
    field.appendChild(head);
    if (input) field.appendChild(input);
    if (helper || action) {
      const footer = document.createElement("div");
      footer.className = "api-drawer-field-footer";
      if (helper) {
        const note = document.createElement("small");
        note.textContent = helper;
        footer.appendChild(note);
      }
      if (action) {
        action.classList.add("api-drawer-text-action");
        footer.appendChild(action);
      }
      field.appendChild(footer);
    }
    return field;
  }

  function suppressBaseSidebarHint(panel) {
    const trigger = document.getElementById("openApiSettings");
    if (!trigger || trigger.dataset.apiDrawerCapture === "true") return;
    trigger.dataset.apiDrawerCapture = "true";
    trigger.addEventListener("click", event => {
      if (!document.body.classList.contains("ui-v4-api-open")) return;
      event.stopImmediatePropagation();
      panel.classList.remove("collapsed");
      window.setTimeout(() => document.getElementById("apiKey")?.focus(), 30);
    }, true);
  }

  function decoratePanel() {
    const panel = document.getElementById("apiPanel");
    const body = document.getElementById("apiPanelBody");
    if (!panel || !body || panel.dataset.apiDrawerV4 === "true") return;
    panel.dataset.apiDrawerV4 = "true";
    panel.classList.add("api-drawer-v4");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-label", "模型配置");
    panel.setAttribute("aria-hidden", "true");
    if (panel.parentElement !== document.body) document.body.appendChild(panel);

    const title = panel.querySelector(".panel-title > span");
    if (title) title.textContent = "模型配置";
    const actions = panel.querySelector(".panel-actions");
    if (actions && !document.getElementById("uiV4ApiClose")) {
      const close = document.createElement("button");
      close.id = "uiV4ApiClose";
      close.className = "ui-v4-api-close";
      close.type = "button";
      close.setAttribute("aria-label", "关闭模型配置");
      close.innerHTML = '<span aria-hidden="true">×</span>';
      close.addEventListener("click", closeDrawer);
      actions.appendChild(close);
    }
    const collapse = document.getElementById("toggleApiPanel");
    if (collapse) collapse.hidden = true;

    const provider = document.getElementById("providerSelect");
    const keyRow = body.querySelector(".key-row");
    const baseUrl = document.getElementById("baseUrl");
    const modelName = document.getElementById("modelName");
    const temperature = document.getElementById("temperature");
    const temperatureValue = document.getElementById("tempValue");
    const testConnection = document.getElementById("testConnection");
    const clearKey = document.getElementById("clearKey");
    const connectionResult = document.getElementById("connectionResult");
    const oldButtonRow = body.querySelector(".button-row.two");

    body.querySelectorAll(":scope > label").forEach(label => label.remove());
    oldButtonRow?.remove();
    const intro = document.createElement("div");
    intro.className = "api-drawer-intro";
    intro.innerHTML = `
      <div class="api-drawer-intro-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d="M12 3v3M12 18v3M4.2 6.2l2.1 2.1M17.7 15.7l2.1 2.1M3 12h3M18 12h3M4.2 17.8l2.1-2.1M17.7 8.3l2.1-2.1"/><circle cx="12" cy="12" r="4"/></svg>
      </div>
      <div><strong>大模型连接</strong><p>配置生成服务所使用的模型接口。可使用部署方提供的公共模型，或企业批准的自定义兼容接口。</p></div>`;
    const tip = body.querySelector(":scope > .tip");
    if (tip) {
      tip.classList.add("api-drawer-security-note");
      tip.textContent = "API Key 仅保存在当前浏览器会话；Base URL、模型名称和温度保存在当前浏览器，不会写入业务报告。";
    }

    const fields = document.createElement("div");
    fields.className = "api-drawer-fields";
    fields.appendChild(makeField({ label: "接口类型", input: provider, helper: "选择与你的模型服务商匹配的接口预设。" }));
    fields.appendChild(makeField({ label: "API Key", input: keyRow, helper: "使用公共模型时可留空；自定义 Key 仅用于当前会话。", action: clearKey }));
    fields.appendChild(makeField({ label: "Base URL", input: baseUrl, helper: "自定义 API 时使用服务商提供的 OpenAI 兼容接口地址。" }));
    fields.appendChild(makeField({ label: "模型名称", input: modelName, helper: "自定义 API 时填写实际可调用的模型名称。" }));
    fields.appendChild(makeField({ label: "生成温度", input: temperature, helper: "值越低输出越稳定；企业材料建议保持在较低到中等范围。", valueNode: temperatureValue }));

    const footer = document.createElement("footer");
    footer.className = "api-drawer-footer";
    if (testConnection) {
      testConnection.classList.remove("primary");
      testConnection.classList.add("secondary", "api-drawer-test");
      footer.appendChild(testConnection);
    }
    let save = document.getElementById("saveApiConfig");
    if (!save) {
      save = document.createElement("button");
      save.id = "saveApiConfig";
      save.type = "button";
      save.className = "primary api-drawer-save";
      save.textContent = "保存配置";
    }
    footer.appendChild(save);

    body.prepend(intro);
    if (tip) intro.insertAdjacentElement("afterend", tip);
    body.appendChild(fields);
    if (connectionResult) body.appendChild(connectionResult);
    panel.appendChild(footer);
    ensureBackdrop();
    suppressBaseSidebarHint(panel);
    syncOpenState();
  }

  function installObserver() {
    if (observer || !document.body) return;
    observer = new MutationObserver(mutations => {
      if (mutations.some(item => item.type === "attributes" && item.attributeName === "class")) syncOpenState();
    });
    observer.observe(document.body, { attributes: true, attributeFilter: ["class"] });
  }
  function start() {
    ensureStyles();
    decoratePanel();
    installObserver();
    window.ZHILINK_API_DRAWER_V4_READY = true;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
