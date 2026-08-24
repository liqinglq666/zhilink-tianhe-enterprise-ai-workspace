/* Recover known workspace JSON keys before feature modules start. */
(() => {
  const targets = [
    [localStorage, "zhilian_identity"],
    [localStorage, "zhilian_current_project_v1"],
    [sessionStorage, "zhilian_profile"],
    [sessionStorage, "zhilian_form_inputs"],
    [sessionStorage, "zhilian_results"],
    [sessionStorage, "zhilian_meta"],
  ];
  const recovered = [];

  for (const [storage, key] of targets) {
    const raw = storage.getItem(key);
    if (!raw) continue;
    try {
      JSON.parse(raw);
    } catch (_) {
      storage.removeItem(key);
      recovered.push(key);
    }
  }

  window.ZHILINK_STORAGE_RECOVERY = Object.freeze({ recovered: Object.freeze(recovered) });
  if (recovered.length) console.warn("Recovered invalid workspace storage", recovered);
})();
