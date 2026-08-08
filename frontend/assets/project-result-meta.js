/* Preserve generated-result trust metadata when explicit project snapshots are saved. */
(() => {
  const META_STORAGE = "zhilian_meta";
  const PROJECT_PATH = /^\/api\/projects(?:\/|\?|$)/;
  const WRITABLE_META_FIELDS = ["origin", "example_key", "result_schema_version"];
  const originalFetch = window.fetch.bind(window);

  function readJson(raw, fallback) {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  }

  function requestUrl(input) {
    if (typeof input === "string") return input;
    if (input && typeof input.url === "string") return input.url;
    return "";
  }

  function requestMethod(input, init) {
    const value = init?.method || (typeof input !== "string" ? input?.method : "") || "GET";
    return String(value).toUpperCase();
  }

  function enrichProjectPayload(input, init) {
    const url = requestUrl(input);
    const method = requestMethod(input, init);
    if (!PROJECT_PATH.test(url) || !["POST", "PUT"].includes(method) || typeof init?.body !== "string") {
      return init;
    }

    const payload = readJson(init.body, null);
    const snapshot = payload?.snapshot;
    if (!snapshot || typeof snapshot !== "object" || !snapshot.results || typeof snapshot.results !== "object") {
      return init;
    }

    const activeMeta = readJson(sessionStorage.getItem(META_STORAGE), {});
    snapshot.meta ||= {};
    Object.keys(snapshot.results).forEach(key => {
      if (!snapshot.results[key]) return;
      const currentMeta = activeMeta?.[key];
      if (!currentMeta || typeof currentMeta !== "object") return;
      const persisted = { ...(snapshot.meta[key] || {}) };
      WRITABLE_META_FIELDS.forEach(field => {
        const value = currentMeta[field];
        if (typeof value === "string" && value) persisted[field] = value;
      });
      snapshot.meta[key] = persisted;
    });

    return { ...init, body: JSON.stringify(payload) };
  }

  window.fetch = function projectResultMetaFetch(input, init = {}) {
    return originalFetch(input, enrichProjectPayload(input, init));
  };

  window.ZHILINK_PROJECT_RESULT_META_READY = true;
})();
