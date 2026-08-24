/* SaaS product polish v3: presentation-only hierarchy and responsive semantics. */
(() => {
  const STYLE_URL = "/assets/saas-product-polish-v3.css?v=20260824.1";
  const runtime = window.ZHILINK_UI_V4_RUNTIME;
  let started = false;

  function ensureStyles() {
    if (document.querySelector('link[data-saas-product-polish-v3]')) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = STYLE_URL;
    link.dataset.saasProductPolishV3 = "true";
    document.head.appendChild(link);
  }

  function setText(element, value) {
    if (element && element.textContent !== value) element.textContent = value;
  }

  function markTaskHierarchy() {
    document.querySelectorAll("#home .module-card[data-tool-key]").forEach(card => {
      card.dataset.productTier = card.classList.contains("ui-v4-secondary-task") ? "utility" : "primary";
    });
  }

  function refineCustomerCopy() {
    setText(document.querySelector('[data-ui-v4-account="api"]'), "AI 服务设置");
    setText(document.getElementById("openApiSettings"), "AI 服务设置");

    const pending = document.querySelector("#uiV4PendingList .ui-v4-panel-empty");
    if (pending && /没有识别到待确认事项|没有待确认事项/.test(pending.textContent || "")) {
      setText(pending, "当前没有待你确认的事项。新结果需要复核时会显示在这里。");
    }

    const recent = document.getElementById("recentMaterials");
    if (recent?.classList.contains("empty") && /没有最近材料|暂无.*材料|暂无.*结果/.test(recent.textContent || "")) {
      setText(recent, "还没有最近结果。完成一次业务任务后，这里会显示你的最新材料。");
    }

    const safetyTitle = document.querySelector("#home .ui-v4-safety-strip h3");
    if (safetyTitle && safetyTitle.textContent.trim() === "使用原则") setText(safetyTitle, "使用与复核");

    const usageLabel = document.querySelector("#uiV4UsagePanel .ui-v4-panel-head > span");
    if (usageLabel && /正式材料|已生成材料/.test(usageLabel.textContent || "")) setText(usageLabel, "工作概览");
  }

  function syncNavigationSemantics() {
    document.querySelectorAll("#navList button[data-section]").forEach(button => {
      if (button.classList.contains("active")) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
  }

  function syncActionSemantics() {
    document.querySelectorAll(".sticky-actions, .ui-v4-form-actions").forEach(actions => {
      if (!actions.getAttribute("aria-label")) actions.setAttribute("aria-label", "当前页面操作");
    });
    const project = document.getElementById("uiV4ProjectContext");
    if (project && !project.getAttribute("aria-label")) project.setAttribute("aria-label", "打开当前项目与版本");
  }

  function apply() {
    if (!document.body) return;
    ensureStyles();
    document.body.classList.add("ui-v4-saas-polish");
    document.documentElement.dataset.zhilinkProductPolish = "v3";
    markTaskHierarchy();
    refineCustomerCopy();
    syncNavigationSemantics();
    syncActionSemantics();
    window.ZHILINK_SAAS_PRODUCT_POLISH_V3_READY = true;
  }

  function start() {
    if (started) return;
    started = true;
    apply();
    runtime?.subscribe?.(apply, { immediate: false });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
