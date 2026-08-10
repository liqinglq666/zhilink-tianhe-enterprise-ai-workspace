/* Result schema migration wrapper for the data provenance guard. */
(() => {
  const BASE_RESULT_SCHEMA_VERSION = "20260806-grounded-output-v2";
  const RESULT_SCHEMA_VERSIONS = {
    contract: "20260807-contract-grounded-v3",
    policy: "20260807-policy-grounded-v3",
  };
  const RESULT_KEYS = ["profile", "meeting", "contract", "policy", "match", "landing", "report"];
  const RESULT_TITLES = {
    profile: "企业档案",
    meeting: "会议纪要",
    contract: "合同审阅",
    policy: "政策准备",
    match: "供需协作",
    landing: "实施计划",
    report: "运营报告",
  };
  const RESULTS_STORAGE = "zhilian_results";
  const META_STORAGE = "zhilian_meta";
  const STRUCTURED_STORAGE = "zhilian_structured_results_v1";
  const QUARANTINE_STORAGE = "zhilian_legacy_result_quarantine_v1";
  const CORE_SCRIPT = "/assets/data-provenance-guard.js?v=20260806.1";
  const CORE_STYLE = "/assets/data-provenance-guard.css?v=20260806.1";
  let setResultGuardInstalled = false;

  function readJson(raw, fallback) {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  }
  function expectedVersion(key) {
    return RESULT_SCHEMA_VERSIONS[key] || BASE_RESULT_SCHEMA_VERSION;
  }
  function currentState() {
    return typeof state !== "undefined" ? state : null;
  }
  function ensureStyles() {
    if (document.querySelector("link[data-zhilink-data-provenance]")) return;
    const style = document.createElement("link");
    style.rel = "stylesheet";
    style.href = CORE_STYLE;
    style.dataset.zhilinkDataProvenance = "true";
    document.head.appendChild(style);
  }
  function persistActiveResults(results, meta) {
    sessionStorage.setItem(RESULTS_STORAGE, JSON.stringify(results || {}));
    sessionStorage.setItem(META_STORAGE, JSON.stringify(meta || {}));
  }
  function quarantineLegacyResults() {
    const results = readJson(sessionStorage.getItem(RESULTS_STORAGE), {});
    const meta = readJson(sessionStorage.getItem(META_STORAGE), {});
    const keys = RESULT_KEYS.filter(key => Boolean(results?.[key]) && String(meta?.[key]?.result_schema_version || "") !== expectedVersion(key));
    if (!keys.length) return [];
    const snapshot = {
      quarantined_at: new Date().toISOString(),
      expected_versions: Object.fromEntries(keys.map(key => [key, expectedVersion(key)])),
      keys,
      results: Object.fromEntries(keys.map(key => [key, results[key]])),
      meta: Object.fromEntries(keys.map(key => [key, meta?.[key] || {}])),
    };
    const history = readJson(sessionStorage.getItem(QUARANTINE_STORAGE), []);
    sessionStorage.setItem(QUARANTINE_STORAGE, JSON.stringify([snapshot, ...(Array.isArray(history) ? history : [])].slice(0, 3)));
    keys.forEach(key => {
      delete results[key];
      delete meta[key];
    });
    persistActiveResults(results, meta);
    sessionStorage.removeItem(STRUCTURED_STORAGE);
    const active = currentState();
    if (active) {
      active.results = results;
      active.meta = meta;
      keys.forEach(key => {
        if (typeof window.showResult === "function") window.showResult(key, {});
      });
      if (typeof window.updateProgress === "function") window.updateProgress();
    }
    return keys;
  }
  function stampCurrentResult(key) {
    const active = currentState();
    if (!active?.results?.[key]) return;
    active.meta ||= {};
    active.meta[key] ||= {};
    active.meta[key].result_schema_version = expectedVersion(key);
    sessionStorage.setItem(META_STORAGE, JSON.stringify(active.meta));
  }
  function installSetResultGuard() {
    if (setResultGuardInstalled) return;
    if (typeof window.setResult !== "function") {
      window.setTimeout(installSetResultGuard, 40);
      return;
    }
    setResultGuardInstalled = true;
    const original = window.setResult;
    window.setResult = function resultSchemaAwareSetResult(key, result) {
      const value = original.apply(this, arguments);
      stampCurrentResult(key);
      window.dispatchEvent(new CustomEvent("zhilink:result-schema-stamped", { detail: { key, version: expectedVersion(key) } }));
      return value;
    };
  }
  function loadCoreGuard() {
    if (window.ZHILINK_DATA_PROVENANCE_READY || document.querySelector("script[data-zhilink-data-provenance-core]")) return;
    const script = document.createElement("script");
    script.src = CORE_SCRIPT;
    script.async = false;
    script.dataset.zhilinkDataProvenanceCore = "true";
    script.addEventListener("error", () => console.error("数据来源隔离核心加载失败，请强制刷新后重试。"), { once: true });
    document.head.appendChild(script);
  }
  function notifyMigration(keys) {
    if (!keys.length) return;
    const labels = keys.map(key => RESULT_TITLES[key] || key).join("、");
    const message = `检测到旧版本生成结果，已隔离 ${keys.length} 项（${labels}）。输入内容已保留，请重新生成。`;
    window.setTimeout(() => {
      if (typeof window.toast === "function") window.toast(message);
      else console.info(message);
    }, 120);
  }
  function start() {
    ensureStyles();
    const migrated = quarantineLegacyResults();
    installSetResultGuard();
    loadCoreGuard();
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
    window.ZHILINK_DATA_PROVENANCE_V2_READY = true;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else window.setTimeout(start, 0);
})();
