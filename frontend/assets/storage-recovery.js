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
  const USER_SESSION_KEYS = [
    "zhilian_api_key",
    "zhilian_profile",
    "zhilian_form_inputs",
    "zhilian_results",
    "zhilian_meta",
  ];
  const USER_LOCAL_KEYS = [
    "zhilian_identity",
    "zhilian_provider",
    "zhilian_base_url",
    "zhilian_model",
    "zhilian_temperature",
  ];
  let logoutPending = false;

  for (const [storage, key] of targets) {
    const raw = storage.getItem(key);
    if (!raw) continue;
    try {
      JSON.parse(raw);
    } catch (_) {
      storage.removeItem(key);
    }
  }

  function clearUserScopedBrowserState() {
    USER_SESSION_KEYS.forEach(key => sessionStorage.removeItem(key));
    USER_LOCAL_KEYS.forEach(key => localStorage.removeItem(key));
  }

  document.addEventListener("click", event => {
    const target = event.target instanceof Element ? event.target : null;
    if (target?.closest("#logoutButton")) logoutPending = true;
  }, true);

  window.addEventListener("beforeunload", () => {
    if (logoutPending) clearUserScopedBrowserState();
  });
})();
