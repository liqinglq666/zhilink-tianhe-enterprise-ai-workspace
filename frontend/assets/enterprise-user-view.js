/* Enterprise customer presentation layer: remaining global shell copy. */
(() => {
  let queued = false;

  function byId(id) {
    return document.getElementById(id);
  }

  function setText(element, value) {
    if (element && element.textContent !== String(value)) element.textContent = String(value);
  }

  function setPlaceholder(id, value) {
    const element = byId(id);
    if (element && element.getAttribute("placeholder") !== value) element.setAttribute("placeholder", value);
  }

  function replaceTextNodes(root, replacements) {
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent || parent.closest("script,style,textarea,input,option")) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      let next = node.nodeValue || "";
      replacements.forEach(([from, to]) => { next = next.replace(from, to); });
      if (next !== node.nodeValue) node.nodeValue = next;
    });
  }

  function decorateStaticShell() {
    setText(document.querySelector('[data-ui-v4-account="api"]'), "AI 服务设置");
    setText(byId("openApiSettings"), "AI 服务设置");

    const identityIntro = document.querySelector("#identityModal .modal-head p");
    if (identityIntro) setText(identityIntro, "用于调整报告抬头、首页状态和生成内容中的业务视角。");

    setPlaceholder("deployment", "如：企业网页工作台，按组织权限使用，敏感业务原文按需脱敏");
    setPlaceholder("reviewMode", "如：生成结果由业务负责人或专业人员复核确认");

    const reportCards = document.querySelectorAll("#report .report-card");
    reportCards.forEach(card => {
      const label = card.querySelector("b")?.textContent?.trim();
      if (label === "导出格式") setText(card.querySelector("strong"), "Word / Markdown / 文本");
      if (label === "安全边界" || label === "导出范围") {
        setText(card.querySelector("b"), "导出范围");
        setText(card.querySelector("strong"), "仅导出业务内容");
        setText(card.querySelector("p"), "导出文件仅包含业务材料，不包含 AI 服务设置。");
      }
    });

    document.querySelectorAll("#home .principle-grid > div").forEach(item => {
      const title = item.querySelector("b")?.textContent?.trim();
      if (title === "模型调用" || title === "AI 服务") {
        setText(item.querySelector("b"), "AI 服务");
        setText(item.querySelector("span"), "默认使用平台提供的 AI 服务；如企业有专属模型，可由管理员在设置中接入。");
      }
    });

    replaceTextNodes(byId("uiV4Metrics"), [
      ["正式材料", "已生成材料"],
      ["可访问项目", "项目"],
      ["已确认 / 批准", "已复核"],
      ["待复核状态", "待复核"],
    ]);
    const usageNote = byId("uiV4UsageNote");
    if (usageNote?.textContent.includes("当前未打开持久化项目")) {
      setText(usageNote, "当前未打开项目。新建或打开项目后可持续保存工作进度。");
    }
    document.querySelectorAll(".ui-v4-module-meta span").forEach(item => {
      const value = item.textContent.trim();
      const map = {
        "不导出 API Key": "敏感设置不会导出",
        "可选上下文": "补充企业背景",
        "AI 辅助生成": "智能辅助整理",
        "支持快速示例": "支持快速填写",
      };
      if (map[value]) setText(item, map[value]);
    });
  }

  function apply() {
    queued = false;
    decorateStaticShell();
    window.ZHILINK_ENTERPRISE_USER_VIEW_READY = true;
  }

  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(apply);
  }

  function start() {
    apply();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(schedule, { immediate: false });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
