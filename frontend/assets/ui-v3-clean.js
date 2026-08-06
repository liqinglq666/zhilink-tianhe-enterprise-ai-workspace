/* UI V3: replace the legacy visual shell while preserving all existing business ids/events. */
(() => {
  const VERSION = "20260806.2";
  const READY_EVENT = "zhilink:ui-v3-ready";
  const MODULES = {
    profile: {
      label: "企业档案",
      result: "企业档案 · 生成结果",
      tone: "indigo",
      icon: '<svg viewBox="0 0 24 24"><path d="M4 20V8h8v12M12 20V4h8v16"/><path d="M7 11h2M7 14h2M15 7h2M15 10h2M15 13h2"/><circle cx="8" cy="5" r="2.5"/></svg>',
    },
    meeting: {
      label: "会议纪要",
      result: "会议纪要 · AI 生成结果",
      tone: "blue",
      icon: '<svg viewBox="0 0 24 24"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 12h6M9 16h4"/><path d="M4 9.5a3 3 0 0 1 6 0v1a3 3 0 0 1-6 0z"/><path d="M7 13.5v2M5 15.5h4"/></svg>',
    },
    contract: {
      label: "合同审阅",
      result: "合同风险 · AI 审阅结果",
      tone: "violet",
      icon: '<svg viewBox="0 0 24 24"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 11h5M9 15h3"/><circle cx="15.5" cy="15.5" r="4"/><path d="m18.5 18.5 2 2M14.2 15.5l1 1 1.8-2"/></svg>',
    },
    policy: {
      label: "政策助手",
      result: "政策方向 · AI 建议结果",
      tone: "amber",
      icon: '<svg viewBox="0 0 24 24"><path d="M4 9h16M6 9V7l6-3 6 3v2M7 9v8M11 9v8M15 9v8M19 17H5v3h14z"/><path d="m18.5 4.5.5 1 .9.4-.9.4-.5 1-.4-1-.9-.4.9-.4z"/></svg>',
    },
    match: {
      label: "供需协作",
      result: "供需协作 · AI 方案结果",
      tone: "green",
      icon: '<svg viewBox="0 0 24 24"><path d="M8.5 12.5 11 15a2.4 2.4 0 0 0 3.4 0l4.1-4.1"/><path d="m9.5 8.5 2-2a2.8 2.8 0 0 1 4 0l4 4-3 3"/><path d="m14.5 8.5-2-2a2.8 2.8 0 0 0-4 0l-4 4 4 4"/><path d="M3 9h3M18 9h3M6 18h12"/></svg>',
    },
    landing: {
      label: "实施计划",
      result: "实施计划 · AI 生成结果",
      tone: "cyan",
      icon: '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M7 3v4M17 3v4M3.5 9h17"/><path d="m7 14 2 2 4-4 4 4"/></svg>',
    },
    report: {
      label: "报告归档",
      result: "运营报告 · 汇总与导出",
      tone: "slate",
      icon: '<svg viewBox="0 0 24 24"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 17v-3M12 17v-6M15 17v-4"/><path d="M8.5 9h3"/></svg>',
    },
  };

  let observer = null;
  let queued = false;

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v3-clean]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v3-clean.css?v=${VERSION}`;
    link.dataset.uiV3Clean = "true";
    document.head.appendChild(link);
  }

  function decorateBusinessPage(id, config) {
    const page = document.getElementById(id);
    if (!page) return;

    page.classList.add("ui-v3-business-page");
    page.dataset.uiV3Tone = config.tone;
    page.dataset.uiV3Module = id;

    const content = page.querySelector(":scope > .content-card") || page.querySelector(".content-card");
    const result = page.querySelector(":scope > .result-panel") || page.querySelector(".result-panel");
    const head = content?.querySelector(".section-head");
    const iconHolder = head?.querySelector(":scope > span");

    if (iconHolder && iconHolder.dataset.uiV3Icon !== "true") {
      iconHolder.innerHTML = config.icon;
      iconHolder.dataset.uiV3Icon = "true";
      iconHolder.setAttribute("aria-hidden", "true");
    }

    if (head && !content.querySelector(".ui-v3-module-meta")) {
      const meta = document.createElement("div");
      meta.className = "ui-v3-module-meta";
      const labels = id === "report"
        ? ["汇总已有结果", "支持多格式导出", "不导出 API Key"]
        : id === "profile"
          ? ["可选上下文", "支持快速示例", "结果可归档"]
          : ["AI 辅助生成", "人工复核后使用", "结果可归档"];
      meta.innerHTML = labels.map(label => `<span>${label}</span>`).join("");
      head.insertAdjacentElement("afterend", meta);
    }

    if (result) {
      result.dataset.uiV3Title = config.result;
      result.setAttribute("aria-label", config.result);
    }

    content?.querySelectorAll("textarea").forEach(textarea => {
      textarea.setAttribute("spellcheck", "false");
    });

    content?.querySelectorAll(".sticky-actions button.primary").forEach(button => {
      if (!button.dataset.uiV3Arrow) {
        button.insertAdjacentHTML(
          "beforeend",
          '<svg viewBox="0 0 24 24" aria-hidden="true" style="width:15px;height:15px"><path d="M5 12h14M14 7l5 5-5 5"/></svg>'
        );
        button.dataset.uiV3Arrow = "true";
      }
    });
  }

  function decorateHome() {
    const home = document.getElementById("home");
    if (!home) return;
    home.dataset.uiV3Home = "true";

    const heroTitle = home.querySelector(".hero-content h3");
    const heroText = home.querySelector(".hero-content > p");
    if (heroTitle && !heroTitle.dataset.uiV3Copy) {
      heroTitle.textContent = "让企业运营材料从输入到归档一步完成";
      heroTitle.dataset.uiV3Copy = "true";
    }
    if (heroText && !heroText.dataset.uiV3Copy) {
      heroText.textContent = "会议、合同、政策、供需和实施计划统一进入一个 AI 工作流；保留人工复核、项目版本与报告导出边界。";
      heroText.dataset.uiV3Copy = "true";
    }

    const governance = home.querySelector(".governance-card");
    if (governance) governance.setAttribute("aria-label", "安全与使用边界");
  }

  function decorateModalAccessibility() {
    const apiPanel = document.getElementById("apiPanel");
    if (apiPanel) {
      apiPanel.setAttribute("role", "dialog");
      apiPanel.setAttribute("aria-modal", "true");
      apiPanel.setAttribute("aria-label", "模型与 API 配置");
    }
  }

  function removeLegacyInlineArtifacts() {
    document.querySelectorAll(".section-head > span").forEach(holder => {
      if (holder.querySelector("svg")) holder.classList.add("ui-v3-icon-holder");
    });

    const oldStatus = document.querySelector(".tool-status-card");
    if (oldStatus) oldStatus.setAttribute("aria-hidden", "true");
  }

  function syncResultState() {
    Object.keys(MODULES).forEach(id => {
      const result = document.querySelector(`#${id} > .result-panel`) || document.querySelector(`#${id} .result-panel`);
      if (!result) return;
      const isEmpty = result.classList.contains("empty");
      result.dataset.uiV3State = isEmpty ? "empty" : "ready";
    });
  }

  function apply() {
    ensureStyles();
    // V1 used a fixed sidebar and left margin. Keeping both body classes makes the
    // V3 grid place the main workspace inside the narrow first column. Remove only
    // the legacy visual scope; its business/navigation JavaScript continues running.
    document.body.classList.remove("ui-redesign-live");
    document.body.classList.add("ui-v3-clean-shell");
    document.documentElement.dataset.zhilinkUi = "v3";
    Object.entries(MODULES).forEach(([id, config]) => decorateBusinessPage(id, config));
    decorateHome();
    decorateModalAccessibility();
    removeLegacyInlineArtifacts();
    syncResultState();

    if (!window.ZHILINK_UI_V3_READY) {
      window.ZHILINK_UI_V3_READY = true;
      window.dispatchEvent(new CustomEvent(READY_EVENT, { detail: { version: VERSION } }));
    }
  }

  function queueApply() {
    if (queued) return;
    queued = true;
    window.requestAnimationFrame(() => {
      queued = false;
      apply();
    });
  }

  function installObserver() {
    if (observer || !document.body) return;
    observer = new MutationObserver(mutations => {
      const relevant = mutations.some(mutation => {
        if (mutation.type === "attributes") {
          return mutation.attributeName === "class" || mutation.attributeName === "hidden";
        }
        return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
      });
      if (relevant) queueApply();
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["class", "hidden"],
    });
  }

  const start = () => {
    apply();
    installObserver();
    window.addEventListener("zhilink:model-mode-change", queueApply);
    window.addEventListener("zhilink:ui-v2-ready", queueApply);
    window.addEventListener("zhilink:workspace-state-change", queueApply);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
