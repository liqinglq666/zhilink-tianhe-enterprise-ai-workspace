/* Generation cancellation and timeout controls. Appended to app.js by backend. */
(() => {
  const CONNECT_TIMEOUT_MS = 30000;
  const IDLE_TIMEOUT_MS = 120000;
  const HARD_TIMEOUT_MS = 600000;
  const activeGenerations = new Map();

  window.__activeGenerations = activeGenerations;

  if (!document.querySelector('link[data-generation-controls]')) {
    const stylesheet = document.createElement("link");
    stylesheet.rel = "stylesheet";
    stylesheet.href = "/assets/generation-controls.css";
    stylesheet.dataset.generationControls = "true";
    document.head.appendChild(stylesheet);
  }

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
    const partial = String(partialContent || "").trim();
    panel.className = "result-panel";
    panel.innerHTML = `
      <div class="result-header">
        <div>
          <p class="result-label">${escapeHtml(title)}</p>
          <h3>${escapeHtml(title)}已停止生成</h3>
        </div>
      </div>
      <div class="result-meta">
        <span class="meta-pill danger">${escapeHtml(message)}</span>
      </div>
      ${partial ? `<p class="partial-result-note">已保留本次已接收的临时内容，但未写入正式结果或报告归档。</p>${renderStructuredMarkdown(partial)}` : ""}
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
          <h3>${escapeHtml(title)}流式生成中</h3>
        </div>
        <div class="result-actions">
          <span class="streaming-badge stream-status" data-stream-status="${escapeHtml(key)}"><span class="streaming-dot"></span>正在连接</span>
          <button class="cancel-generation" data-cancel-generation="${escapeHtml(key)}" type="button" aria-label="停止当前生成">停止生成</button>
        </div>
      </div>
      <div class="result-meta">
        <span class="meta-pill">AI模型流式模式</span>
        <span class="meta-pill">连接超时 30 秒</span>
        <span class="meta-pill">空闲超时 120 秒</span>
      </div>
      <div id="${key}StreamContent" class="streaming-content" aria-live="polite">正在连接模型接口，请稍候...</div>
    `;
  };

  apiStream = async function apiStreamWithCancellation(url, payload, key) {
    saveConfig();
    if (activeGenerations.size) {
      throw createGenerationError("当前已有生成任务正在运行，请先等待完成或点击“停止生成”。", "GENERATION_ALREADY_RUNNING");
    }

    beginStreamingResult(key);
    const controller = new AbortController();
    const task = {
      controller,
      cancelledByUser: false,
      timeoutKind: "",
      full: "",
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
    const abortFor = (kind) => {
      if (controller.signal.aborted) return;
      task.timeoutKind = kind;
      controller.abort();
    };
    const resetIdleTimer = () => {
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => abortFor("idle"), IDLE_TIMEOUT_MS);
    };

    connectTimer = setTimeout(() => abortFor("connect"), CONNECT_TIMEOUT_MS);
    hardTimer = setTimeout(() => abortFor("hard"), HARD_TIMEOUT_MS);

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
        const error = createGenerationError(parsed.detail || text || "模型请求失败。", parsed.code || "GENERATION_HTTP_ERROR", Boolean(parsed.retryable));
        error.retryAfter = parsed.retry_after;
        throw error;
      }
      if (!resp.body) {
        throw createGenerationError("当前浏览器不支持流式读取，请更新浏览器后重试。", "STREAM_NOT_SUPPORTED");
      }

      setStreamStatus(key, "正在接收");
      resetIdleTimer();
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
            setStreamStatus(key, "请求已发送");
          } else if (event.type === "delta") {
            task.full += event.content || "";
            setStreamStatus(key, "正在生成");
            const now = Date.now();
            if (now - lastRender > 120 || task.full.length < 80) {
              updateStreamingResult(key, task.full);
              lastRender = now;
            }
          } else if (event.type === "done") {
            receivedDone = true;
            task.full = event.content || task.full;
            setStreamStatus(key, "正在整理");
            finishStreamingResult(key, task.full, event.mode || "AI模型流式模式");
            return { ok: true, content: task.full, mode: event.mode || "AI模型流式模式" };
          } else if (event.type === "error") {
            const error = createGenerationError(event.error || "模型流式生成失败。", event.code || "STREAM_ERROR", Boolean(event.retryable));
            error.retryAfter = event.retry_after;
            throw error;
          }
        }
        updateStreamingResult(key, task.full);
      }

      if (!receivedDone) {
        throw createGenerationError(
          "流式连接提前结束，收到的内容可能不完整，已保留为临时内容但不会写入正式结果。",
          "STREAM_INCOMPLETE",
          true,
        );
      }
      if (!task.full.trim()) {
        throw createGenerationError("模型连接已结束，但没有返回可用内容。", "MODEL_EMPTY_RESPONSE", true);
      }
      finishStreamingResult(key, task.full, "AI模型流式模式");
      return { ok: true, content: task.full, mode: "AI模型流式模式" };
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
          message = "连接模型超过 30 秒，请检查 Base URL、网络或模型服务状态。";
          failStreamingResult(key, message);
        } else if (task.timeoutKind === "idle") {
          code = "GENERATION_IDLE_TIMEOUT";
          message = "模型超过 120 秒没有返回新内容，请缩短输入或稍后重试。";
          showStoppedResult(key, message, task.full);
        } else {
          code = "GENERATION_HARD_TIMEOUT";
          message = "本次生成超过 10 分钟，系统已自动停止。";
          showStoppedResult(key, message, task.full);
        }
      } else if (code === "STREAM_INCOMPLETE") {
        showStoppedResult(key, message, task.full);
      } else {
        failStreamingResult(key, message);
      }

      throw createGenerationError(message, code, Boolean(err.retryable));
    } finally {
      clearTimers();
      if (activeGenerations.get(key) === task) activeGenerations.delete(key);
    }
  };

  document.addEventListener("click", (event) => {
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
    activeGenerations.forEach((task) => task.controller.abort());
    activeGenerations.clear();
  });
})();
