/* Keep example and legacy session data out of the formal enterprise workspace. */
(() => {
  const BUSINESS_KEYS = ["profile", "meeting", "contract", "policy", "match", "landing"];
  const SCHEMA_KEYS = [...BUSINESS_KEYS, "report"];
  const RESULT_TITLES = {
    profile: "企业档案", meeting: "会议纪要", contract: "合同审阅", policy: "政策准备",
    match: "供需协作", landing: "实施计划", report: "运营报告",
  };
  const INPUT_MODULES = {
    profileName: "profile", profileIndustry: "profile", profileLocation: "profile", profileScale: "profile",
    profileStage: "profile", profileRole: "profile", profileDemands: "profile",
    meetingInput: "meeting", contractInput: "contract", policyDemand: "policy",
    offerInput: "match", needInput: "match", targetInput: "match", scenarioInput: "match",
    pilotScene: "landing", userRoles: "landing", dataScope: "landing", deployment: "landing",
    pilotPeriod: "landing", reviewMode: "landing",
  };

  const BASE_RESULT_SCHEMA_VERSION = "20260806-grounded-output-v2";
  const RESULT_SCHEMA_VERSIONS = {
    contract: "20260807-contract-grounded-v3",
    policy: "20260807-policy-grounded-v3",
  };
  const EXAMPLE_CONTEXT_STORAGE = "zhilian_example_contexts_v1";
  const RESULTS_STORAGE = "zhilian_results";
  const META_STORAGE = "zhilian_meta";
  const STRUCTURED_STORAGE = "zhilian_structured_results_v1";
  const QUARANTINE_STORAGE = "zhilian_legacy_result_quarantine_v1";
  const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1";
  const FORMAL_ORIGINS = new Set(["user", "project", "imported"]);
  const STYLE_URL = "/assets/data-provenance-guard.css?v=20260806.1";
  let started = false;
  let eventsBound = false;

  function readJson(raw, fallback) {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  }
  function appState() {
    return typeof state !== "undefined" ? state : null;
  }
  function examples() {
    return typeof exampleScenarios !== "undefined" ? exampleScenarios : {};
  }
  function expectedVersion(key) {
    return RESULT_SCHEMA_VERSIONS[key] || BASE_RESULT_SCHEMA_VERSION;
  }
  function contexts() {
    return readJson(sessionStorage.getItem(EXAMPLE_CONTEXT_STORAGE), {});
  }
  function saveContexts(value) {
    sessionStorage.setItem(EXAMPLE_CONTEXT_STORAGE, JSON.stringify(value || {}));
  }
  function persistMeta() {
    const current = appState();
    if (current) sessionStorage.setItem(META_STORAGE, JSON.stringify(current.meta || {}));
  }
  function persistActiveResults(results, meta) {
    sessionStorage.setItem(RESULTS_STORAGE, JSON.stringify(results || {}));
    sessionStorage.setItem(META_STORAGE, JSON.stringify(meta || {}));
  }
  function ensureStyles() {
    if (document.querySelector("link[data-zhilink-data-provenance]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = STYLE_URL;
    link.dataset.zhilinkDataProvenance = "true";
    document.head.appendChild(link);
  }

  function moduleFromExampleKey(key) {
    const module = String(key || "").split("-", 1)[0];
    return BUSINESS_KEYS.includes(module) ? module : "";
  }
  function exampleMatchesCurrentInput(exampleKey) {
    const example = examples()[exampleKey];
    if (!example) return false;
    return Object.entries(example.fields || {}).every(([id, value]) => {
      const element = document.getElementById(id);
      return Boolean(element) && String(element.value || "") === String(value || "");
    });
  }
  function inferLegacyOrigin(key) {
    const marked = contexts()[key];
    if (marked?.exampleKey && exampleMatchesCurrentInput(marked.exampleKey)) return "example";
    const matchedKey = Object.keys(examples()).find(exampleKey => (
      moduleFromExampleKey(exampleKey) === key && exampleMatchesCurrentInput(exampleKey)
    ));
    if (matchedKey) {
      const next = contexts();
      next[key] = { exampleKey: matchedKey, markedAt: new Date().toISOString() };
      saveContexts(next);
      return "example";
    }
    return localStorage.getItem(CURRENT_PROJECT_STORAGE) ? "project" : "legacy";
  }
  function originFor(key) {
    return String(appState()?.meta?.[key]?.origin || "") || inferLegacyOrigin(key);
  }
  function isFormalResult(key) {
    return Boolean(appState()?.results?.[key]) && FORMAL_ORIGINS.has(originFor(key));
  }
  function isolatedKeys() {
    const current = appState();
    return current
      ? Object.keys(current.results || {}).filter(key => current.results[key] && !isFormalResult(key))
      : [];
  }
  function formalCount() {
    return BUSINESS_KEYS.filter(isFormalResult).length;
  }
  function markExample(exampleKey) {
    const module = moduleFromExampleKey(exampleKey);
    if (!module) return;
    const next = contexts();
    next[module] = { exampleKey, markedAt: new Date().toISOString() };
    saveContexts(next);
  }
  function clearExampleMarker(module) {
    const next = contexts();
    if (!module || !next[module]) return;
    delete next[module];
    saveContexts(next);
  }
  function generationOrigin(key) {
    const marker = contexts()[key];
    return marker?.exampleKey && exampleMatchesCurrentInput(marker.exampleKey) ? "example" : "user";
  }

  function quarantineLegacyResults() {
    const results = readJson(sessionStorage.getItem(RESULTS_STORAGE), {});
    const meta = readJson(sessionStorage.getItem(META_STORAGE), {});
    const keys = SCHEMA_KEYS.filter(key => (
      Boolean(results?.[key]) && String(meta?.[key]?.result_schema_version || "") !== expectedVersion(key)
    ));
    if (!keys.length) return [];

    const snapshot = {
      quarantined_at: new Date().toISOString(),
      expected_versions: Object.fromEntries(keys.map(key => [key, expectedVersion(key)])),
      keys,
      results: Object.fromEntries(keys.map(key => [key, results[key]])),
      meta: Object.fromEntries(keys.map(key => [key, meta?.[key] || {}])),
    };
    const history = readJson(sessionStorage.getItem(QUARANTINE_STORAGE), []);
    sessionStorage.setItem(
      QUARANTINE_STORAGE,
      JSON.stringify([snapshot, ...(Array.isArray(history) ? history : [])].slice(0, 3)),
    );
    keys.forEach(key => {
      delete results[key];
      delete meta[key];
    });
    persistActiveResults(results, meta);
    sessionStorage.removeItem(STRUCTURED_STORAGE);

    const current = appState();
    if (current) {
      current.results = results;
      current.meta = meta;
      keys.forEach(key => window.showResult?.(key, {}));
      window.updateProgress?.();
    }
    return keys;
  }

  function migrateExistingOrigins() {
    const current = appState();
    if (!current) return;
    current.meta ||= {};
    Object.keys(current.results || {}).forEach(key => {
      if (!current.results[key]) return;
      current.meta[key] ||= {};
      if (!current.meta[key].origin) current.meta[key].origin = inferLegacyOrigin(key);
    });
    persistMeta();
  }

  function stampCommittedResult(key) {
    const current = appState();
    if (!SCHEMA_KEYS.includes(key) || !current?.results?.[key]) return;
    current.meta ||= {};
    current.meta[key] ||= {};
    current.meta[key].result_schema_version = expectedVersion(key);

    const origin = generationOrigin(key);
    current.meta[key].origin = origin;
    const marker = contexts()[key];
    if (origin === "example" && marker?.exampleKey) current.meta[key].example_key = marker.exampleKey;
    else delete current.meta[key].example_key;
    persistMeta();

    window.dispatchEvent(new CustomEvent("zhilink:result-schema-stamped", {
      detail: { key, version: expectedVersion(key) },
    }));
    if (origin === "example" && typeof toast === "function") {
      toast("已生成示例结果；不会计入正式工作台、待核对事项或运营报告。");
    }
  }

  function installFormalCollectors() {
    window.collectBaseResults = function collectFormalBaseResults() {
      const current = appState();
      return {
        "企业档案": isFormalResult("profile") ? current?.results?.profile || "" : "",
        "会议纪要": isFormalResult("meeting") ? current?.results?.meeting || "" : "",
        "合同审阅": isFormalResult("contract") ? current?.results?.contract || "" : "",
        "政策准备": isFormalResult("policy") ? current?.results?.policy || "" : "",
        "供需协作": isFormalResult("match") ? current?.results?.match || "" : "",
        "实施计划": isFormalResult("landing") ? current?.results?.landing || "" : "",
      };
    };
    window.collectResultsForReport = function collectFormalResultsForReport(includeAiSummary = false) {
      const base = window.collectBaseResults();
      if (includeAiSummary && isFormalResult("report")) {
        return { "AI整合报告": appState()?.results?.report || "", ...base };
      }
      return base;
    };
  }

  function renderFormalRecentMaterials() {
    const current = appState();
    const container = document.getElementById("recentMaterials");
    if (!current || !container) return;
    const items = Object.keys(current.results || {})
      .filter(key => isFormalResult(key) && RESULT_TITLES[key])
      .map(key => ({ key, title: RESULT_TITLES[key], time: current.meta?.[key]?.time || "", content: current.results[key] || "" }))
      .sort((a, b) => String(b.time).localeCompare(String(a.time)))
      .slice(0, 5);
    if (!items.length) {
      const isolated = isolatedKeys().length;
      container.className = "recent-list empty";
      container.textContent = isolated
        ? `暂无正式材料。已隔离 ${isolated} 项示例或旧会话材料，可在下方清除。`
        : "暂无正式材料。输入真实业务内容并生成后，这里会显示最近材料。";
      return;
    }
    const safe = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
    const html = items.map(item => {
      const timeText = item.time ? new Date(item.time).toLocaleString() : "当前会话";
      const summary = item.content.replace(/[#*_`|>-]/g, "").replace(/\s+/g, " ").trim().slice(0, 90) || "已生成业务材料";
      return `<article class="recent-item"><div class="recent-item-icon">${safe(item.title.slice(0, 1))}</div><div><h4>${safe(item.title)}</h4><p>${safe(timeText)} · ${safe(summary)}</p></div><button class="secondary small" data-goto="${safe(item.key)}" type="button">查看</button></article>`;
    }).join("");
    container.className = "recent-list";
    if (container.innerHTML !== html) container.innerHTML = html;
  }

  function renderIsolationNotice() {
    const home = document.getElementById("home");
    if (!home) return;
    const keys = isolatedKeys();
    let notice = document.getElementById("dataIsolationNotice");
    if (!keys.length) {
      notice?.remove();
      return;
    }
    if (!notice) {
      notice = document.createElement("section");
      notice.id = "dataIsolationNotice";
      notice.className = "data-isolation-notice";
      const anchor = document.getElementById("uiV4HomeGrid") || home.querySelector(".governance-card");
      if (anchor?.parentNode) anchor.parentNode.insertBefore(notice, anchor);
      else home.appendChild(notice);
    }
    const labels = keys.map(key => RESULT_TITLES[key] || key).join("、");
    const html = `<div><strong>已隔离 ${keys.length} 项示例或旧会话材料</strong><p>${labels} 不计入待核对、统计和正式报告。需要正式使用时，请替换为真实业务输入并重新生成。</p></div><button id="clearIsolatedResults" type="button">清除隔离材料</button>`;
    if (notice.innerHTML !== html) notice.innerHTML = html;
  }

  function decorateResultOrigins() {
    const current = appState();
    if (!current) return;
    SCHEMA_KEYS.forEach(key => {
      const panel = document.getElementById(`${key}Result`);
      if (!panel) return;
      const existing = panel.querySelector(".data-origin-pill");
      if (!current.results?.[key]) {
        delete panel.dataset.resultOrigin;
        existing?.remove();
        return;
      }
      const origin = originFor(key);
      panel.dataset.resultOrigin = origin;
      if (FORMAL_ORIGINS.has(origin)) {
        existing?.remove();
        return;
      }
      const text = origin === "example" ? "示例生成 · 不计入正式工作台" : "旧会话材料 · 已隔离";
      const className = `meta-pill data-origin-pill ${origin === "example" ? "example" : "legacy"}`;
      if (existing && existing.textContent === text && existing.className === className) return;
      existing?.remove();
      const meta = panel.querySelector(".result-meta");
      if (!meta) return;
      const badge = document.createElement("span");
      badge.className = className;
      badge.textContent = text;
      meta.prepend(badge);
    });
  }

  function refreshFormalWorkspace() {
    decorateResultOrigins();
    renderIsolationNotice();
    window.ZHILINK_UI_V4_SHELL?.refresh?.();
  }

  function renderFormalProgress() {
    const current = appState();
    if (!current) return;
    const count = formalCount();
    const setText = (id, value) => {
      const element = document.getElementById(id);
      if (element && element.textContent !== value) element.textContent = value;
    };
    setText("generatedCount", `${count} 项`);
    setText("homeGeneratedCount", `${count} 项`);
    setText("reportDoneCount", `${count}/${BUSINESS_KEYS.length}`);
    document.querySelectorAll(".nav button").forEach(button => {
      const key = button.dataset.section;
      button.classList.toggle("done", key === "report" ? isFormalResult("report") : isFormalResult(key));
    });
    document.querySelectorAll("[data-tool-key]").forEach(card => {
      card.classList.toggle("done", isFormalResult(card.dataset.toolKey));
    });
    renderFormalRecentMaterials();
    refreshFormalWorkspace();
  }

  function clearIsolatedResults() {
    const current = appState();
    if (!current) return;
    const keys = isolatedKeys();
    keys.forEach(key => {
      delete current.results[key];
      delete current.meta[key];
      window.showResult?.(key, {});
    });
    persistActiveResults(current.results, current.meta);
    saveContexts({});
    if (typeof toast === "function") toast(`已清除 ${keys.length} 项示例或旧会话材料。`);
    window.updateProgress?.();
  }

  function bindEvents() {
    if (eventsBound) return;
    eventsBound = true;
    document.addEventListener("input", event => {
      const module = INPUT_MODULES[event.target?.id];
      if (module && event.isTrusted) clearExampleMarker(module);
    }, true);
    document.addEventListener("click", event => {
      const exampleButton = event.target.closest?.("[data-example]");
      if (exampleButton?.dataset.example) markExample(exampleButton.dataset.example);
      if (event.target.closest?.("#clearIsolatedResults")) clearIsolatedResults();
      const projectSave = event.target.closest?.("#createProjectButton, #saveProjectButton");
      if (projectSave && isolatedKeys().length) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (typeof toast === "function") toast("当前包含示例或旧会话材料。请先清除隔离材料，再保存正式项目。");
      }
    }, true);
    window.addEventListener("zhilink:result-updated", event => {
      const key = event.detail?.key;
      if (event.detail?.source === "commit" && key) stampCommittedResult(key);
      refreshFormalWorkspace();
    });
    window.addEventListener("zhilink:progress-updated", renderFormalProgress);
    ["zhilink:account-ready", "zhilink:workspace-state-change"].forEach(name => {
      window.addEventListener(name, refreshFormalWorkspace);
      document.addEventListener(name, refreshFormalWorkspace);
    });
    window.addEventListener("storage", refreshFormalWorkspace);
  }

  function notifyMigration(keys) {
    if (!keys.length) return;
    const labels = keys.map(key => RESULT_TITLES[key] || key).join("、");
    const message = `检测到旧版本生成结果，已隔离 ${keys.length} 项（${labels}）。输入内容已保留，请重新生成。`;
    window.setTimeout(() => {
      if (typeof toast === "function") toast(message);
      else console.info(message);
    }, 120);
  }

  function start() {
    if (started) return;
    started = true;
    ensureStyles();
    const migrated = quarantineLegacyResults();
    migrateExistingOrigins();
    installFormalCollectors();
    renderFormalProgress();
    notifyMigration(migrated);

    window.ZHILINK_RESULT_SCHEMA_VERSION = BASE_RESULT_SCHEMA_VERSION;
    window.ZHILINK_RESULT_SCHEMA_VERSIONS = { base: BASE_RESULT_SCHEMA_VERSION, ...RESULT_SCHEMA_VERSIONS };
    window.ZHILINK_RESULT_CACHE_GUARD = {
      version: BASE_RESULT_SCHEMA_VERSION,
      versions: window.ZHILINK_RESULT_SCHEMA_VERSIONS,
      quarantineKey: QUARANTINE_STORAGE,
      getQuarantine: () => readJson(sessionStorage.getItem(QUARANTINE_STORAGE), []),
      rerunMigration: quarantineLegacyResults,
    };
    window.ZHILINK_DATA_PROVENANCE = {
      originFor,
      isFormalResult,
      isolatedKeys,
      formalCount,
      refresh: refreshFormalWorkspace,
    };
    window.ZHILINK_DATA_PROVENANCE_READY = true;
    window.dispatchEvent(new CustomEvent("zhilink:data-provenance-ready"));
  }

  bindEvents();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
