/* UI V4 model drawer controller for native markup and connection checks. */
(() => {
  const CONNECTION_TECHNICAL_DETAIL_RE = /(?:traceback|exception|internal server error|bad gateway|gateway timeout|nginx|cloudflare|uvicorn|fastapi|pydantic|sql(?:alchemy)?|stack trace|api[_ -]?key|bearer\s|authorization|request id|response body|<html|<!doctype)/i;

  function syncOpenState() {
    const panel = document.getElementById("apiPanel");
    const backdrop = document.getElementById("uiV4ApiBackdrop");
    if (!panel) return;
    const open = document.body.classList.contains("ui-v4-api-open");
    panel.setAttribute("aria-hidden", String(!open));
    backdrop?.setAttribute("aria-hidden", String(!open));
  }

  function openDrawer() {
    document.body.classList.add("ui-v4-api-open");
    syncOpenState();
  }

  function closeDrawer() {
    document.body.classList.remove("ui-v4-api-open");
    syncOpenState();
  }

  function cleanDetail(value) {
    if (typeof value !== "string") return "";
    return value.replace(/\s+/g, " ").trim();
  }

  function safeConnectionDetail(value, fallback) {
    const detail = cleanDetail(value);
    if (!detail || detail.length > 160 || CONNECTION_TECHNICAL_DETAIL_RE.test(detail)) return fallback;
    return detail;
  }

  function connectionHttpFailureMessage(status, detail) {
    const code = Number(status || 0);
    if (code === 400 || code === 422) return safeConnectionDetail(detail, "AI 服务配置未通过校验，请检查服务地址和模型名称。");
    if (code === 401 || code === 403) return "AI 服务授权未通过，请检查访问密钥。";
    if (code === 413) return "连接配置内容过大，请精简后重试。";
    if (code === 429) return "连接检查较频繁，请稍后重试。";
    if (code >= 500) return "AI 服务暂时不可用，请稍后重试。";
    return safeConnectionDetail(detail, "服务检查未完成，请稍后重试。");
  }

  function readConnectionDraft() {
    return {
      api_key: document.getElementById("apiKey")?.value.trim() || "",
      base_url: document.getElementById("baseUrl")?.value.trim() || "",
      model: document.getElementById("modelName")?.value.trim() || "",
      temperature: Number(document.getElementById("temperature")?.value || 0.35),
    };
  }

  function setConnectionLoading(button, loading) {
    if (!button) return;
    if (loading) {
      button.dataset.connectionOldText = button.textContent;
      button.textContent = "检查中...";
      button.disabled = true;
      return;
    }
    button.textContent = button.dataset.connectionOldText || "检查连接";
    delete button.dataset.connectionOldText;
    button.disabled = false;
  }

  async function requestConnectionTest(payload) {
    let response;
    try {
      response = await fetch("/api/test-connection", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      });
    } catch (_) {
      throw new Error("网络连接异常，请稍后重试。");
    }

    let data = {};
    try { data = await response.json(); } catch (_) { data = {}; }
    if (!response.ok) {
      throw new Error(connectionHttpFailureMessage(response.status, data.detail));
    }
    return data;
  }

  async function runConnectionTest() {
    const button = document.getElementById("testConnection");
    const result = document.getElementById("connectionResult");
    const draft = readConnectionDraft();

    if (draft.api_key && (!draft.base_url || !draft.model)) {
      if (result) result.textContent = "使用企业自有 AI 服务时，请填写服务地址和模型名称后再检查。";
      return;
    }

    try {
      setConnectionLoading(button, true);
      const response = await requestConnectionTest(draft);
      if (!result) return;
      if (response.ok) {
        const scope = draft.api_key ? "当前编辑设置，尚未保存" : "平台服务";
        result.textContent = `服务可用（${scope}）：${safeConnectionDetail(response.content || response.mode, "连接正常")}`;
        return;
      }
      result.textContent = `服务不可用：${safeConnectionDetail(response.error, "请检查连接设置")}`;
    } catch (error) {
      if (result) result.textContent = `服务不可用：${safeConnectionDetail(error?.message, "服务检查未完成，请稍后重试。")}`;
    } finally {
      setConnectionLoading(button, false);
    }
  }

  function interceptLegacyConnectionCheck(event) {
    const target = event.target instanceof Element ? event.target : null;
    if (!target?.closest("#testConnection")) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    runConnectionTest();
  }

  function bindControls() {
    document.getElementById("uiV4ApiClose")?.addEventListener("click", closeDrawer);
    document.getElementById("uiV4ApiBackdrop")?.addEventListener("click", closeDrawer);
    const source = document.getElementById("openApiSettings");
    source?.addEventListener("click", event => {
      event.preventDefault();
      event.stopImmediatePropagation();
      openDrawer();
    }, true);
  }

  function start() {
    if (!document.getElementById("apiPanel")) return;
    bindControls();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(syncOpenState, { immediate: false });
    syncOpenState();
    window.ZHILINK_API_DRAWER_V4_READY = true;
  }

  document.addEventListener("click", interceptLegacyConnectionCheck, true);
  window.ZHILINK_API_DRAWER_V4 = { open: openDrawer, close: closeDrawer };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
