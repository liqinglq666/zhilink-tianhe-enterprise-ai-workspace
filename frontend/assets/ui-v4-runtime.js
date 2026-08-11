/* UI V4 runtime: one DOM observer and one animation-frame scheduler for presentation layers. */
(() => {
  const subscribers = new Set();
  const EVENT_NAMES = [
    "zhilink:account-ready",
    "zhilink:workspace-state-change",
    "zhilink:data-provenance-ready",
    "zhilink:result-schema-stamped",
    "zhilink:model-mode-change",
  ];
  let observer = null;
  let queued = false;
  let started = false;
  let lastReason = "startup";

  function runSubscribers() {
    queued = false;
    const reason = lastReason;
    lastReason = "runtime";
    subscribers.forEach(callback => {
      try { callback(reason); }
      catch (error) { console.error("UI V4 runtime subscriber failed", error); }
    });
  }

  function schedule(reason = "runtime") {
    lastReason = reason;
    if (queued) return;
    queued = true;
    requestAnimationFrame(runSubscribers);
  }

  function subscribe(callback, { immediate = true } = {}) {
    if (typeof callback !== "function") return () => {};
    subscribers.add(callback);
    if (immediate) {
      try { callback("subscribe"); }
      catch (error) { console.error("UI V4 runtime subscriber failed", error); }
    }
    return () => subscribers.delete(callback);
  }

  function emit(name, detail = {}) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
    schedule(name);
  }

  function installObserver() {
    if (observer || !document.body) return;
    observer = new MutationObserver(mutations => {
      const relevant = mutations.some(mutation => {
        if (mutation.type === "characterData") return true;
        if (mutation.type === "childList") return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
        return mutation.type === "attributes" && ["class", "hidden", "aria-hidden", "aria-expanded", "disabled"].includes(mutation.attributeName);
      });
      if (relevant) schedule("dom");
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["class", "hidden", "aria-hidden", "aria-expanded", "disabled"],
    });
  }

  function start() {
    if (started) return;
    started = true;
    installObserver();
    EVENT_NAMES.forEach(name => window.addEventListener(name, () => schedule(name)));
    window.addEventListener("storage", () => schedule("storage"));
    window.addEventListener("resize", () => schedule("resize"), { passive: true });
    window.addEventListener("orientationchange", () => schedule("orientationchange"), { passive: true });
    schedule("startup");
    window.ZHILINK_UI_V4_RUNTIME_READY = true;
  }

  window.ZHILINK_UI_V4_RUNTIME = {
    subscribe,
    schedule,
    emit,
    refresh: () => schedule("manual"),
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
