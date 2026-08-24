/* Enterprise customer presentation layer: global business copy and UI hygiene. */
(() => {
  const TOAST_REWRITES = [
    [/模型配置已保存/g, "AI 服务设置已保存"],
    [/已切换当前编辑内容为公共模型，保存后生效/g, "已选择平台 AI 服务，保存后生效"],
    [/已从当前编辑内容中清空 API Key，保存后生效/g, "已清除访问密钥，保存后生效"],
    [/已生成示例结果；不会计入正式工作台、待核对事项或运营报告/g, "示例内容仅供体验，不会加入当前项目、待处理事项或报告"],
    [/当前包含示例或旧会话材料。请先清除隔离材料，再保存正式项目/g, "当前包含示例或历史会话内容。请先清除这些内容，再保存项目"],
    [/已清除 (\d+) 项示例或旧会话材料/g, "已清除 $1 项示例或历史会话内容"],
  ];

  let queued = false;
  let advancedInitialized = false;

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

  function rewriteToastMessage(message) {
    let value = String(message || "");
    TOAST_REWRITES.forEach(([pattern, replacement]) => { value = value.replace(pattern, replacement); });
    return value;
  }

  function wrapToast() {
    const original = window.toast;
    if (typeof original !== "function" || original.__enterpriseWrapped) return;
    const wrapped = function enterpriseToast(message) {
      return original.call(this, rewriteToastMessage(message));
    };
    wrapped.__enterpriseWrapped = true;
    wrapped.__enterpriseOriginal = original;
    window.toast = wrapped;
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

  function decorateModelSettings() {
    const panel = byId("apiPanel");
    if (!panel) return;
    setText(byId("apiDrawerTitle"), "AI 服务设置");
    setText(panel.querySelector(".api-drawer-intro strong"), "AI 服务");
    setText(panel.querySelector(".api-drawer-intro p"), "使用平台服务时无需额外设置；企业如需接入自有服务，可在高级连接设置中维护。");
    setText(panel.querySelector(".api-drawer-security-note"), "敏感连接信息只用于当前浏览器中的服务设置，不会写入项目或导出的业务材料。");

    const fieldLabels = new Map([
      ["providerSelect", "服务方式"],
      ["apiKey", "访问密钥"],
      ["baseUrl", "服务地址"],
      ["modelName", "模型名称"],
      ["temperature", "生成稳定性"],
    ]);
    fieldLabels.forEach((label, id) => setText(panel.querySelector(`label[for="${id}"]`), label));
    setText(byId("testConnection"), "检查服务");
    setText(byId("saveApiConfig"), "保存设置");

    const clear = byId("clearKey");
    if (clear) {
      const value = clear.textContent.trim();
      if (value.includes("恢复公共模型")) setText(clear, "使用平台服务");
      else if (value.includes("API Key") || value.includes("访问密钥")) setText(clear, "清除访问密钥");
    }

    const notice = byId("publicModelModeNotice");
    if (notice) {
      const title = notice.querySelector("[data-public-model-title]");
      const detail = notice.querySelector("[data-public-model-detail]");
      const mode = document.body.dataset.modelMode || notice.dataset.mode || "";
      if (mode === "public") {
        setText(title, "平台 AI 服务已就绪");
        setText(detail, "当前服务可直接使用，无需额外设置。");
      } else if (mode === "custom") {
        setText(title, "正在使用企业自有 AI 服务");
        setText(detail, "连接信息仅用于企业自有服务，不会写入业务材料。");
      } else if (mode === "checking") {
        setText(title, "正在检查 AI 服务");
        setText(detail, "请稍候，系统正在确认服务状态。");
      } else if (mode === "unconfigured") {
        setText(title, "AI 服务未就绪");
        setText(detail, "请联系管理员，或在高级连接设置中配置企业自有 AI 服务。");
      }
    }

    const topStatus = byId("topApiStatus");
    if (topStatus) {
      const value = topStatus.textContent.trim();
      const map = {
        "公共模型可用": "AI 服务可用",
        "自定义 API": "企业 AI 服务",
        "需配置模型": "AI 服务未就绪",
        "正在检查模型": "正在检查服务",
      };
      if (map[value]) setText(topStatus, map[value]);
    }
    const badge = byId("modeBadge");
    if (badge) {
      const value = badge.textContent.trim();
      const map = { "公共模型": "平台服务", "自定义 API": "企业服务", "待配置": "未就绪", "检查中": "检查中" };
      if (map[value]) setText(badge, map[value]);
    }

    const fields = panel.querySelector(".api-drawer-fields");
    if (!fields || fields.closest("#enterpriseAdvancedAiSettings") || !notice) return;
    const details = document.createElement("details");
    details.id = "enterpriseAdvancedAiSettings";
    details.className = "enterprise-ai-advanced";
    const summary = document.createElement("summary");
    summary.id = "enterpriseAdvancedAiSettingsSummary";
    summary.textContent = "高级连接设置";
    const noteText = document.createElement("p");
    noteText.className = "enterprise-ai-advanced-note";
    noteText.textContent = "仅在接入企业自有 AI 服务时需要填写。普通用户无需修改。";
    fields.before(details);
    details.append(summary, noteText, fields);
    const mode = document.body.dataset.modelMode || "";
    details.open = mode === "custom" || mode === "unconfigured";
    advancedInitialized = true;
  }

  function decorateProvenance() {
    const notice = byId("dataIsolationNotice");
    if (notice) {
      const strong = notice.querySelector("strong");
      const count = strong?.textContent.match(/(\d+)\s*项/)?.[1] || "";
      if (strong) setText(strong, count ? `有 ${count} 项示例或历史会话内容未加入当前项目` : "有示例或历史会话内容未加入当前项目");
      const paragraph = notice.querySelector("p");
      if (paragraph) setText(paragraph, "示例和历史会话内容不会加入项目、待处理事项或报告；如需正式使用，请换成真实业务输入后重新生成。");
      setText(byId("clearIsolatedResults"), "清除这些内容");
    }
    document.querySelectorAll(".data-origin-pill").forEach(badge => {
      const value = badge.textContent;
      if (value.includes("示例")) setText(badge, "示例内容");
      else if (value.includes("旧会话") || value.includes("历史会话")) setText(badge, "历史会话内容");
    });
    const recent = byId("recentMaterials");
    if (recent?.classList.contains("empty") && /已隔离|旧会话|示例/.test(recent.textContent)) {
      setText(recent, "暂无已加入项目的正式材料。示例和历史会话内容不会显示在这里。");
    }
  }

  function syncAdvancedState() {
    const details = byId("enterpriseAdvancedAiSettings");
    if (!details || !advancedInitialized) return;
    const mode = document.body.dataset.modelMode || "";
    if ((mode === "custom" || mode === "unconfigured") && !details.open) details.open = true;
  }

  function apply() {
    queued = false;
    wrapToast();
    decorateStaticShell();
    decorateModelSettings();
    decorateProvenance();
    syncAdvancedState();
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
