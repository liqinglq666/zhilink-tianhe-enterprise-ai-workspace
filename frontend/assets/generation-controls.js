/* Generation cancellation, verified streaming and timeout transport for the workspace hook bridge. */
(() => {
  const CONNECT_TIMEOUT_MS = 30000;
  const DEFAULT_IDLE_TIMEOUT_MS = 135000;
  const DEFAULT_HARD_TIMEOUT_MS = 210000;
  const activeGenerations = new Map();
  const hooks = window.ZHILINK_WORKSPACE_HOOKS;

  if (!hooks) throw new Error("Workspace hooks must load before generation controls.");
  window.__activeGenerations = activeGenerations;

  function createGenerationError(message, code, retryable = false) {
    const error = new Error(message);
    error.code = code;
    error.retryable = retryable;
    return error;
  }

  function setStreamStatus(key, message) {
    const target = document.querySelector(`[data-stream-status="${key}"]`);
    if (target) target.textContent = message;
  }

  function showStoppedResult(key, message, partialContent) {
    const panel = $(`${key}Result`);
    if (!panel) return;
    const title = resultTitles[key] || "生成结果";
    void partialContent;
    panel.className = "result-panel";
    panel.innerHTML = `
      <div class="result-header">
        <div>
          <p class="result-label">${escapeHtml(title)}</p>
          <h3>${escapeHtml(title)}生成已停止</h3>
        </div>
      </div>
      <div class="result-meta">
        <span class="meta-pill danger">${escapeHtml(message)}</span>
      </div>
      <p class="partial-result-note">本次未完成的内容未保存，可重新生成。</p>
    `;
  }

  beginStreamingResult = function beginStreamingResultWithCancel(key) {
    const panel = $(`${key}Result`);
    if (!panel) return;
    const title = resultTitles[key] || "生成结果";
    panel.className = "result-panel streaming";
    panel.innerHTML = `
      <div class="result-header">
        <div>
          <p class="result-label">${escapeHtml(title)}</p>
          <h3>${escapeHtml(title)}生成中</h3>
        </div>
        <div class="result-actions">
          <span class="streaming-badge stream-status" data-stream-status="${escapeHtml(key)}"><span class="streaming-dot"></span>正在处理</span>
          <button class="cancel-generation" data-cancel-generation="${escapeHtml(key)}" type="button" aria-label="停止当前生成">停止生成</button>
        </div>
      </div>
      <div id="${key}StreamContent" class="streaming-content" aria-live="polite">正在整理内容，请稍候...</div>
    `;
  };

  async function runGeneration(request) {
    const { url, payload, key } = request;
    saveConfig();
    if (activeGenerations.size) {
      throw createGenerationError("当前已有任务正在处理，请等待完成或停止当前任务后再试。", "GENERATION_ALREADY_RUNNING");
    }

    beginStreamingResult(key);
    const controller = new AbortController();
    const task = {
      controller,
      cancelledByUser: false,
      timeoutKind: "",
      full: "",
      requiresVerification: false,
      verified: false,
      idleTimeoutMs: DEFAULT_IDLE_TIMEOUT_MS,
      hardTimeoutMs: DEFAULT_HARD_TIMEOUT_MS,
    };
    activeGenerations.set(key, task);

    let connectTimer = null;
    let idleTimer = null;
    let hardTimer = null;
    let buffer = "";
    let receivedDone = false;

    const clearTimers = () => {
      clearTimeout(connectTimer);
      clearTimeout(idleTimer);
      clearTimeout(hardTimer);
    };
    const abortFor = kind => {
      if (controller.signal.aborted) return;
      task.timeoutKind = kind;
      controller.abort();
    };
    const resetIdleTimer = () => {
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => abortFor("idle"), task.idleTimeoutMs);
    };
    const resetHardTimer = () => {
      clearTimeout(hardTimer);
      hardTimer = setTimeout(() => abortFor("hard"), task.hardTimeoutMs);
    };
    const applyServerTimeouts = event => {
      const idle = Number(event?.idle_timeout_ms);
      const hard = Number(event?.hard_timeout_ms);
      if (Number.isFinite(idle) && idle >= 15000 && idle <= 900000) task.idleTimeoutMs = idle;
      if (Number.isFinite(hard) && hard >= 30000 && hard <= 1900000) task.hardTimeoutMs = hard;
      if (task.hardTimeoutMs <= task.idleTimeoutMs) task.hardTimeoutMs = task.idleTimeoutMs + 15000;
      resetIdleTimer();
      resetHardTimer();
    };

    connectTimer = setTimeout(() => abortFor("connect"), CONNECT_TIMEOUT_MS);

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      clearTimeout(connectTimer);

      if (!resp.ok) {
        const text = await resp.text();
        let parsed = {};
        try { parsed = JSON.parse(text); } catch (_) {}
        const error = createGenerationError(parsed.detail || text || "处理请求失败，请稍后重试。", parsed.code || "GENERATION_HTTP_ERROR", Boolean(parsed.retryable));
        error.retryAfter = parsed.retry_after;
        throw error;
      }
      if (!resp.body) {
        throw createGenerationError("当前浏览器无法接收实时结果，请更新浏览器后重试。", "STREAM_NOT_SUPPORTED");
      }

      setStreamStatus(key, "正在处理");
      resetIdleTimer();
      resetHardTimer();
      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let lastRender = 0;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        resetIdleTimer();

        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() || "";

        for (const frame of frames) {
          const line = frame.split("\n").find(item => item.startsWith("data:"));
          if (!line) continue;
          const raw = line.slice(5).trim();
          if (!raw) continue;

          let event;
          try { event = JSON.parse(raw); } catch (_) { continue; }

          if (event.type === "meta") {
            task.requiresVerification = event.provisional === true;
            applyServerTimeouts(event);
            setStreamStatus(key, "正在生成");
            const target = $(`${key}StreamContent`);
            if (target && !task.full.trim()) target.textContent = "正在生成内容，请稍候...";
          } else if (event.type === "delta") {
            task.full += event.content || "";
            setStreamStatus(key, "正在生成");
            const now = Date.now();
            if (now - lastRender > 120 || task.full.length < 80) {
              updateStreamingResult(key, task.full);
              lastRender = now;
            }
          } else if (event.type === "verifying") {
            setStreamStatus(key, "正在核对内容");
          } else if (event.type === "verified") {
            if (!String(event.content || "").trim()) {
              throw createGenerationError("内容核对完成，但没有可用结果，请重新生成。", "STREAM_VERIFICATION_EMPTY", true);
            }
            task.full = event.content;
            task.verified = true;
            setStreamStatus(key, "即将完成");
            updateStreamingResult(key, task.full);
          } else if (event.type === "done") {
            receivedDone = true;
            if (task.requiresVerification && !task.verified) {
              throw createGenerationError(
                "内容核对未完成，本次结果未保存，请重新生成。",
                "STREAM_VERIFICATION_MISSING",
                true,
              );
            }
            task.full = event.content || task.full;
            setStreamStatus(key, "已完成");
            finishStreamingResult(key, task.full, event.mode || (task.verified ? "AI模型模式（已校验）" : "AI模型流式模式"));
            return { ok: true, content: task.full, mode: event.mode || "AI模型流式模式" };
          } else if (event.type === "error") {
            const error = createGenerationError(event.error || "生成失败，请稍后重试。", event.code || "STREAM_ERROR", Boolean(event.retryable));
            error.retryAfter = event.retry_after;
            throw error;
          }
        }
        updateStreamingResult(key, task.full);
      }

      if (!receivedDone) {
        throw createGenerationError(
          "连接提前结束，本次结果未保存，请重新生成。",
          "STREAM_INCOMPLETE",
          true,
        );
      }
      if (!task.full.trim()) {
        throw createGenerationError("处理已结束，但没有生成可用内容，请重新生成。", "MODEL_EMPTY_RESPONSE", true);
      }
      if (task.requiresVerification && !task.verified) {
        throw createGenerationError("内容核对未完成，本次结果未保存。", "STREAM_VERIFICATION_MISSING", true);
      }
      finishStreamingResult(key, task.full, task.verified ? "AI模型模式（已校验）" : "AI模型流式模式");
      return { ok: true, content: task.full, mode: task.verified ? "AI模型模式（已校验）" : "AI模型流式模式" };
    } catch (err) {
      let message = err.message || String(err);
      let code = err.code || "GENERATION_FAILED";

      if (err.name === "AbortError") {
        if (task.cancelledByUser) {
          code = "GENERATION_CANCELLED";
          message = "已停止生成。";
          showStoppedResult(key, message, task.full);
        } else if (task.timeoutKind === "connect") {
          code = "GENERATION_CONNECT_TIMEOUT";
          message = "服务连接超时，请检查网络后重试。";
          failStreamingResult(key, message);
        } else if (task.timeoutKind === "idle") {
          code = "GENERATION_IDLE_TIMEOUT";
          message = "长时间未收到新内容，系统已停止本次生成，请稍后重试。";
          showStoppedResult(key, message, task.full);
        } else {
          code = "GENERATION_HARD_TIMEOUT";
          message = "本次处理时间较长，系统已自动停止，请精简输入后重试。";
          showStoppedResult(key, message, task.full);
        }
      } else if (code === "STREAM_INCOMPLETE" || code.startsWith("STREAM_VERIFICATION") || (task.requiresVerification && task.full.trim())) {
        showStoppedResult(key, message, task.full);
      } else {
        failStreamingResult(key, message);
      }

      throw createGenerationError(message, code, Boolean(err.retryable));
    } finally {
      clearTimers();
      if (activeGenerations.get(key) === task) activeGenerations.delete(key);
    }
  }

  hooks.setGenerationTransport(runGeneration);

  document.addEventListener("click", event => {
    const button = event.target.closest("[data-cancel-generation]");
    if (!button) return;
    const key = button.dataset.cancelGeneration;
    const task = activeGenerations.get(key);
    if (!task || task.controller.signal.aborted) return;
    button.disabled = true;
    button.textContent = "正在停止...";
    task.cancelledByUser = true;
    task.controller.abort();
  });

  window.addEventListener("pagehide", () => {
    activeGenerations.forEach(task => task.controller.abort());
    activeGenerations.clear();
  });

  window.ZHILINK_GENERATION_CONTROLS_READY = true;
})();
