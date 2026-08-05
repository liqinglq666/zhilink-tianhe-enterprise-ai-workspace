/* Official-policy retrieval, source viewer, and grounded policy route switch. */
(() => {
  const STORAGE_KEY = "zhilian_official_policy_sources_v1";
  const SEARCH_TIMEOUT_MS = 20000;
  let cached = read(sessionStorage.getItem(STORAGE_KEY), null);
  let activeSearch = null;

  function read(raw, fallback) {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  }
  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
  async function digest(value) {
    if (!window.crypto?.subtle) return String(value || "");
    const bytes = new TextEncoder().encode(String(value || ""));
    const hash = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(hash), item => item.toString(16).padStart(2, "0")).join("");
  }
  function currentInput() {
    if (typeof saveProfileToState === "function") saveProfileToState();
    return {
      profile: { ...(state.profile || {}) },
      demand: document.getElementById("policyDemand")?.value?.trim() || "",
    };
  }
  function isOfficialUrl(raw) {
    try {
      const url = new URL(raw, location.origin);
      const host = url.hostname.toLowerCase();
      return ["gov.cn", "gd.gov.cn", "gz.gov.cn", "thnet.gov.cn"].some(
        suffix => host === suffix || host.endsWith(`.${suffix}`)
      ) && url.protocol === "https:";
    } catch (_) {
      return false;
    }
  }
  function statusLabel(status) {
    return {
      ok: "官方检索成功",
      partial: "官方检索部分成功",
      no_results: "未找到明显匹配来源",
      unavailable: "官方检索暂不可用",
      disabled: "官方检索已关闭",
    }[status] || "官方检索状态未知";
  }

  function injectUi() {
    if (!document.querySelector("link[data-policy-sources]")) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "/assets/policy-sources.css";
      link.dataset.policySources = "true";
      document.head.appendChild(link);
    }
    const runButton = document.getElementById("runPolicy");
    if (runButton && !document.getElementById("searchOfficialPolicy")) {
      const button = document.createElement("button");
      button.id = "searchOfficialPolicy";
      button.type = "button";
      button.className = "secondary policy-source-search";
      button.textContent = "先查官方政策";
      button.addEventListener("click", async () => {
        const original = button.textContent;
        button.disabled = true;
        button.textContent = "检索中...";
        try {
          await searchSources(true);
          openViewer();
        } catch (error) {
          toast(error.message || String(error));
        } finally {
          button.disabled = false;
          button.textContent = original;
        }
      });
      runButton.insertAdjacentElement("beforebegin", button);
    }
    if (document.getElementById("officialPolicyModal")) return;
    const modal = document.createElement("div");
    modal.id = "officialPolicyModal";
    modal.className = "policy-source-modal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div class="policy-source-backdrop" data-close-policy-sources></div>
      <section class="policy-source-dialog" role="dialog" aria-modal="true" aria-labelledby="officialPolicyTitle">
        <header>
          <div><span class="track">官方来源</span><h2 id="officialPolicyTitle">政策检索与原文引用</h2><p>只展示服务端从 allowlist 政府域名读取的页面。正式申报前仍需打开原文核验。</p></div>
          <button class="icon-btn" type="button" data-close-policy-sources aria-label="关闭官方政策来源">✕</button>
        </header>
        <div id="officialPolicyStatus" class="policy-source-status"></div>
        <div id="officialPolicyList" class="policy-source-list"></div>
        <footer><button id="refreshOfficialPolicy" class="secondary" type="button">重新检索</button></footer>
      </section>`;
    document.body.appendChild(modal);
    modal.addEventListener("click", event => {
      if (event.target.closest("[data-close-policy-sources]")) closeViewer();
    });
    document.getElementById("refreshOfficialPolicy").addEventListener("click", async event => {
      const button = event.currentTarget;
      button.disabled = true;
      button.textContent = "检索中...";
      try {
        await searchSources(true);
        renderViewer();
      } catch (error) {
        toast(error.message || String(error));
      } finally {
        button.disabled = false;
        button.textContent = "重新检索";
      }
    });
  }

  async function searchSources(force = false) {
    const input = currentInput();
    const inputHash = await digest(JSON.stringify(input));
    if (!force && cached?.input_sha256 === inputHash && cached?.retrieval) {
      decorate();
      return cached.retrieval;
    }
    if (activeSearch) return activeSearch;
    activeSearch = (async () => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), SEARCH_TIMEOUT_MS);
      try {
        const response = await fetch("/api/policy/official/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...input, query: "", limit: 6 }),
          signal: controller.signal,
        });
        const text = await response.text();
        const data = read(text, {});
        if (!response.ok) throw new Error(data.detail || text || "官方政策检索失败。");
        cached = { input_sha256: inputHash, retrieval: data };
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(cached));
        decorate();
        return data;
      } catch (error) {
        if (error.name === "AbortError") throw new Error("官方政策检索超过 20 秒，请稍后重试。");
        throw error;
      } finally {
        clearTimeout(timer);
      }
    })().finally(() => { activeSearch = null; });
    return activeSearch;
  }

  function decorate() {
    const panel = document.getElementById("policyResult");
    if (!panel || !state.results.policy) return;
    panel.querySelector(".policy-source-bar")?.remove();
    const retrieval = cached?.retrieval;
    const bar = document.createElement("div");
    bar.className = `policy-source-bar policy-source-${safe(retrieval?.status || "unknown")}`;
    const count = retrieval?.sources?.length || 0;
    bar.innerHTML = `
      <div><strong>${safe(retrieval ? statusLabel(retrieval.status) : "正在准备官方来源")}</strong>
      <small>${retrieval ? `${count} 个来源 · ${safe(retrieval.retrieved_at || "")} · 来源状态需人工复核` : "生成政策报告前会自动检索"}</small></div>
      <button class="inline-action" type="button" data-open-policy-sources ${retrieval ? "" : "disabled"}>查看官方来源</button>`;
    const structured = panel.querySelector(".structured-result-bar");
    const review = panel.querySelector(".review-workflow-bar");
    if (structured) structured.insertAdjacentElement("afterend", bar);
    else if (review) review.insertAdjacentElement("afterend", bar);
    else panel.querySelector(".result-meta")?.insertAdjacentElement("afterend", bar);
  }

  function renderViewer() {
    const retrieval = cached?.retrieval;
    const status = document.getElementById("officialPolicyStatus");
    const list = document.getElementById("officialPolicyList");
    if (!retrieval) {
      status.innerHTML = "<strong>尚未执行检索</strong><p>点击重新检索读取当前企业档案和政策需求。</p>";
      list.innerHTML = "";
      return;
    }
    status.innerHTML = `<div><strong>${safe(statusLabel(retrieval.status))}</strong><span>${safe(retrieval.retrieved_at || "")}</span></div>
      <p>检索词：${safe(retrieval.query || "未提供")}</p>
      ${(retrieval.warnings || []).length ? `<ul>${retrieval.warnings.map(item => `<li>${safe(item)}</li>`).join("")}</ul>` : ""}`;
    if (!retrieval.sources?.length) {
      list.innerHTML = '<p class="policy-source-empty">没有获得可验证官方原文。AI 结果不得输出具体政策、金额、期限或资格结论。</p>';
      return;
    }
    list.innerHTML = retrieval.sources.map(source => {
      const href = isOfficialUrl(source.official_url) ? source.official_url : "";
      const dates = [
        source.published_at ? `发布 ${source.published_at}` : "",
        source.effective_at ? `实施 ${source.effective_at}` : "",
        source.expires_at ? `失效 ${source.expires_at}` : "",
      ].filter(Boolean).join(" · ");
      return `<article class="policy-source-card">
        <header><span>${safe(source.citation_id)}</span><strong>${safe(source.status)}</strong></header>
        <h3>${safe(source.title)}</h3>
        <dl>
          <div><dt>发布机关</dt><dd>${safe(source.issuer || "未稳定识别")}</dd></div>
          <div><dt>文号</dt><dd>${safe(source.document_number || "未稳定识别")}</dd></div>
          <div><dt>日期</dt><dd>${safe(dates || "待打开原文核验")}</dd></div>
          <div><dt>官方域名</dt><dd>${safe(source.official_domain)}</dd></div>
        </dl>
        <blockquote>${safe(source.excerpt || "未提取到稳定摘录，请打开官方原文核对。")}</blockquote>
        ${href ? `<a href="${safe(href)}" target="_blank" rel="noopener noreferrer">打开官方原文</a>` : '<span class="policy-source-invalid">链接未通过前端 HTTPS 官方域名校验</span>'}
      </article>`;
    }).join("");
  }

  function openViewer() {
    renderViewer();
    const modal = document.getElementById("officialPolicyModal");
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
  }
  function closeViewer() {
    const modal = document.getElementById("officialPolicyModal");
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
  }

  const previousApiStream = apiStream;
  apiStream = async function officialPolicyAwareStream(url, payload, key) {
    if (url === "/api/policy/stream" && key === "policy") {
      await searchSources(false).catch(error => console.warn("official policy pre-search unavailable", error));
      return previousApiStream("/api/policy/official/stream", payload, key);
    }
    return previousApiStream(url, payload, key);
  };

  const previousShowResult = showResult;
  showResult = function officialPolicyAwareShowResult(key, result) {
    previousShowResult(key, result);
    if (key === "policy") Promise.resolve().then(decorate);
  };

  injectUi();
  document.addEventListener("click", event => {
    if (event.target.closest("[data-open-policy-sources]")) openViewer();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && document.getElementById("officialPolicyModal")?.classList.contains("show")) closeViewer();
  });
  setTimeout(() => {
    if (state.results.policy) decorate();
  }, 600);

  window.ZHILINK_POLICY_SOURCES = {
    get: () => cached?.retrieval || null,
    refresh: () => searchSources(true),
  };
  window.ZHILINK_POLICY_SOURCES_READY = true;
})();
