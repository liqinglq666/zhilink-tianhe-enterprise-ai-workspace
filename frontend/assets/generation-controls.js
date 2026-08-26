/* Generation cancellation, verified streaming and timeout transport for the workspace hook bridge. */
(() => {
  const CONNECT_TIMEOUT_MS = 30000;
  const DEFAULT_IDLE_TIMEOUT_MS = 135000;
  const DEFAULT_HARD_TIMEOUT_MS = 210000;
  const activeGenerations = new Map();
  const hooks = window.ZHILINK_WORKSPACE_HOOKS;
  const PREVIEW_INTERNAL_REF_RE = /\[(?:MT-\d{2}|MP-\d{2}|MT-C\d{2})\]/g;
  const PREVIEW_HIDDEN_SECTIONS = new Set(["自动一致性校验", "输入证据与待确认索引", "证据索引", "AI 建议补充动作"]);
  const PREVIEW_TECHNICAL_HEADERS = /(证据编号|原文证据|依据编号|证据引用|来源编号|输入摘录)/;

  if (!hooks) throw new Error("Workspace hooks must load before generation controls.");

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

  function setGenerationStep(key, step, state) {
    const target = document.querySelector(`[data-generation-step="${key}-${step}"]`);
    if (!target) return;
    target.classList.toggle("is-active", state === "active");
    target.classList.toggle("is-done", state === "done");
    target.setAttribute("aria-current", state === "active" ? "step" : "false");
  }

  function updateGenerationSteps(key, task) {
    if (!task) return;
    if (task.phase === "connecting") {
      setGenerationStep(key, 1, "active");
      setGenerationStep(key, 2, "pending");
      setGenerationStep(key, 3, "pending");
      return;
    }
    if (task.phase === "generating") {
      setGenerationStep(key, 1, "done");
      setGenerationStep(key, 2, "active");
      setGenerationStep(key, 3, "pending");
      return;
    }
    if (task.phase === "verifying") {
      setGenerationStep(key, 1, "done");
      setGenerationStep(key, 2, "done");
      setGenerationStep(key, 3, "active");
      return;
    }
    setGenerationStep(key, 1, "done");
    setGenerationStep(key, 2, "done");
    setGenerationStep(key, 3, "done");
  }

  function updateGenerationProgress(key, task) {
    const target = $(`${key}StreamProgress`);
    if (!target || !task) return;
    const chars = String(task.full || "").length;
    if (task.phase === "verifying") {
      target.textContent = `正文草稿已形成 · 正在核对关键事实与待确认项${chars ? ` · ${chars.toLocaleString()} 字` : ""}`;
    } else if (task.phase === "finishing") {
      target.textContent = "内容核对完成 · 正在生成正式业务版本";
    } else if (task.phase === "generating" && chars > 0) {
      target.textContent = `正在形成业务结果 · 已整理 ${chars.toLocaleString()} 字，内容持续更新`;
    } else if (task.phase === "generating") {
      target.textContent = "正在形成业务结果 · 首批内容即将生成";
    } else {
      target.textContent = "正在理解材料 · 提取关键事实、决策与任务上下文";
    }
    updateGenerationSteps(key, task);
  }

  function stripPreviewInlineMarkdown(value) {
    return String(value || "")
      .replace(PREVIEW_INTERNAL_REF_RE, "")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/__([^_]+)__/g, "$1")
      .replace(/^\s*>\s?/, "")
      .replace(/^\s*[-*+]\s+/, "• ")
      .replace(/[ \t]+([，。；：！？])/g, "$1")
      .replace(/[ \t]{2,}/g, " ")
      .trim();
  }

  function buildBusinessPreview(content) {
    const output = [];
    let hiddenSection = false;
    let tableHeaders = null;

    for (const rawLine of String(content || "").split(/\r?\n/)) {
      const trimmed = rawLine.trim();
      const heading = trimmed.match(/^#{1,6}\s+(.+?)\s*$/);
      if (heading) {
        const title = stripPreviewInlineMarkdown(heading[1]);
        hiddenSection = PREVIEW_HIDDEN_SECTIONS.has(title);
        tableHeaders = null;
        if (!hiddenSection && title) output.push(`\n${title}\n`);
        continue;
      }
      if (hiddenSection) continue;
      if (!trimmed) {
        tableHeaders = null;
        continue;
      }

      if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
        const cells = trimmed.slice(1, -1).split("|").map(cell => stripPreviewInlineMarkdown(cell));
        if (cells.every(cell => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")))) continue;
        if (!tableHeaders) {
          tableHeaders = cells;
          continue;
        }
        const visible = cells.filter((_, index) => !PREVIEW_TECHNICAL_HEADERS.test(tableHeaders[index] || ""));
        const primary = visible.shift();
        if (!primary) continue;
        const details = visible.filter(Boolean).slice(0, 3);
        output.push(`• ${primary}${details.length ? ` — ${details.join(" · ")}` : ""}`);
        continue;
      }

      tableHeaders = null;
      const line = stripPreviewInlineMarkdown(trimmed);
      if (line) output.push(line);
    }

    return output.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function updateLiveStreamPreview(key, content) {
    const target = $(`${key}StreamPreview`);
    if (!target) return;
    const text = buildBusinessPreview(content);
    target.textContent = text;
    target.toggleAttribute("data-empty", !text.trim());
    if (text.trim()) target.scrollTop = target.scrollHeight;
  }

  function showStoppedResult(key, message) {
    const panel = $(`${key}Result`);
    if (!panel) return;
    const title = resultTitles[key] || "生成结果";
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

  function beginStreamingResult(key) {
    const panel = $(`${key}Result`);
    if (!panel) return;
    const title = resultTitles[key] || "生成结果";
    panel.className = "result-panel streaming";
    panel.innerHTML = `
      <div class="result-header">
        <div>
          <p class="result-label">${escapeHtml(title)}</p>
          <h3>正在生成${escapeHtml(title)}</h3>
        </div>
        <div class="result-actions">
          <span class="streaming-badge stream-status" data-stream-status="${escapeHtml(key)}"><span class="streaming-dot"></span>正在准备</span>
          <button class="cancel-generation" data-cancel-generation="${escapeHtml(key)}" type="button" aria-label="停止当前生成">停止</button>
        </div>
      </div>
      <div class="streaming-stage">
        <ol class="generation-steps" aria-label="AI 处理进度">
          <li class="generation-step is-active" data-generation-step="${escapeHtml(key)}-1" aria-current="step"><span class="generation-step-index">1</span><span><strong>理解材料</strong><small>识别事实与上下文</small></span></li>
          <li class="generation-step" data-generation-step="${escapeHtml(key)}-2" aria-current="false"><span class="generation-step-index">2</span><span><strong>形成结果</strong><small>组织业务结论与行动项</small></span></li>
          <li class="generation-step" data-generation-step="${escapeHtml(key)}-3" aria-current="false"><span class="generation-step-index">3</span><span><strong>核对排版</strong><small>检查关键事实并生成正式版</small></span></li>
        </ol>
        <div id="${key}StreamProgress" class="streaming-progress" aria-live="polite">正在理解材料 · 提取关键事实、决策与任务上下文</div>
        <section class="streaming-preview-shell" aria-label="生成草稿预览">
          <div class="streaming-preview-head">
            <div><strong>业务草稿</strong><span class="streaming-preview-live"><i></i>实时更新</span></div>
            <span>完成后自动核对并排版</span>
          </div>
          <div id="${key}StreamPreview" class="streaming-preview" aria-live="off" data-empty></div>
        </section>
      </div>
    `;
  }

  async function runGeneration(request) {
    const { url, payload, key } = request;
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
      phase: "connecting",
      idleTimeoutMs: DEFAULT_IDLE_TIMEOUT_MS,
      hardTimeoutMs: DEFAULT_HARD_TIMEOUT_MS,
    };
    activeGenerations.set(key, task);

    let connectTimer = null;
    let idleTimer = null;
    let hardTimer = null;
    let buffer = "";
    updateGenerationProgress(key, task);

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

      task.phase = "generating";
      setStreamStatus(key, "正在生成");
      updateGenerationProgress(key, task);
      resetIdleTimer();
      resetHardTimer();
      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");

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
            task.phase = "generating";
            setStreamStatus(key, "正在生成");
          } else if (event.type === "delta") {
            task.full += event.content || "";
            task.phase = "generating";
            setStreamStatus(key, "正在生成");
          } else if (event.type === "verifying") {
            task.phase = "verifying";
            setStreamStatus(key, "正在核对");
          } else if (event.type === "verified") {
            if (!String(event.content || "").trim()) {
              throw createGenerationError("内容核对完成，但没有可用结果，请重新生成。", "STREAM_VERIFICATION_EMPTY", true);
            }
            task.full = event.content;
            task.verified = true;
            task.phase = "finishing";
            setStreamStatus(key, "正在排版");
          } else if (event.type === "done") {
            if (task.requiresVerification && !task.verified) {
              throw createGenerationError(
                "内容核对未完成，本次结果未保存，请重新生成。",
                "STREAM_VERIFICATION_MISSING",
                true,
              );
            }
            task.full = event.content || task.full;
            task.phase = "finishing";
            setStreamStatus(key, "已完成");
            updateGenerationProgress(key, task);
            finishStreamingResult(key, task.full, event.mode || (task.verified ? "AI模型模式（已校验）" : "AI模型流式模式"));
            return { ok: true, content: task.full, mode: event.mode || "AI模型流式模式" };
          } else if (event.type === "error") {
            const error = createGenerationError(event.error || "生成失败，请稍后重试。", event.code || "STREAM_ERROR", Boolean(event.retryable));
            error.retryAfter = event.retry_after;
            throw error;
          }
        }
        updateLiveStreamPreview(key, task.full);
        updateGenerationProgress(key, task);
      }

      throw createGenerationError(
        "连接提前结束，本次结果未保存，请重新生成。",
        "STREAM_INCOMPLETE",
        true,
      );
    } catch (err) {
      let message = err.message || String(err);
      let code = err.code || "GENERATION_FAILED";

      if (err.name === "AbortError") {
        if (task.cancelledByUser) {
          code = "GENERATION_CANCELLED";
          message = "已停止生成。";
          showStoppedResult(key, message);
        } else if (task.timeoutKind === "connect") {
          code = "GENERATION_CONNECT_TIMEOUT";
          message = "服务连接超时，请检查网络后重试。";
          failStreamingResult(key, message);
        } else if (task.timeoutKind === "idle") {
          code = "GENERATION_IDLE_TIMEOUT";
          message = "长时间未收到新内容，系统已停止本次生成，请稍后重试。";
          showStoppedResult(key, message);
        } else {
          code = "GENERATION_HARD_TIMEOUT";
          message = "本次处理时间较长，系统已自动停止，请精简输入后重试。";
          showStoppedResult(key, message);
        }
      } else if (code === "STREAM_INCOMPLETE" || code.startsWith("STREAM_VERIFICATION") || (task.requiresVerification && task.full.trim())) {
        showStoppedResult(key, message);
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