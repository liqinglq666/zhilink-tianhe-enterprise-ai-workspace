(() => {
  "use strict";

  const phase = document.currentScript?.dataset.phase || "post";
  const JSON_STORAGE_KEYS = {
    session: [
      "zhilian_profile",
      "zhilian_results",
      "zhilian_meta",
      "zhilian_form_inputs",
    ],
    local: ["zhilian_identity"],
  };

  function removeInvalidJson(storage, keys) {
    keys.forEach((key) => {
      const raw = storage.getItem(key);
      if (raw === null) return;
      try {
        JSON.parse(raw);
      } catch (_) {
        storage.removeItem(key);
      }
    });
  }

  if (phase === "pre") {
    removeInvalidJson(sessionStorage, JSON_STORAGE_KEYS.session);
    removeInvalidJson(localStorage, JSON_STORAGE_KEYS.local);
    return;
  }

  const REQUEST_TIMEOUT_MS = 180000;

  function parseSseFrame(frame) {
    const payload = frame
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n")
      .trim();

    if (!payload) return null;
    try {
      return JSON.parse(payload);
    } catch (_) {
      return null;
    }
  }

  window.apiStream = async function apiStream(url, payload, key) {
    window.saveConfig();

    // A new request invalidates the previous result so failed retries cannot be
    // silently exported as if they belonged to the latest input.
    window.setResult(key, { ok: false, content: "", mode: "", error: "" });
    window.beginStreamingResult(key);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    let full = "";
    let buffer = "";
    let receivedDone = false;
    let reachedCleanEof = false;

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const text = await resp.text();
        let detail = text;
        try {
          detail = JSON.parse(text).detail || text;
        } catch (_) {}
        throw new Error(detail);
      }
      if (!resp.body) {
        throw new Error("当前浏览器不支持流式读取，请更新浏览器后重试。");
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let lastRender = 0;

      const handleEvent = (event) => {
        if (!event) return;

        if (event.type === "delta") {
          full += event.content || "";
          const now = Date.now();
          if (now - lastRender > 120 || full.length < 80) {
            window.updateStreamingResult(key, full);
            lastRender = now;
          }
          return;
        }

        if (event.type === "done") {
          full = event.content || full;
          if (!full.trim()) {
            throw new Error("模型接口未返回有效文本，请检查模型名称或接口兼容性。");
          }
          receivedDone = true;
          return;
        }

        if (event.type === "error") {
          throw new Error(event.error || "模型流式生成失败。");
        }
      };

      while (!receivedDone) {
        const { value, done } = await reader.read();
        if (done) {
          reachedCleanEof = true;
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split(/\r?\n\r?\n/);
        buffer = frames.pop() || "";

        for (const frame of frames) {
          handleEvent(parseSseFrame(frame));
          if (receivedDone) break;
        }

        window.updateStreamingResult(key, full);
      }

      buffer += decoder.decode();
      if (!receivedDone && buffer.trim()) {
        handleEvent(parseSseFrame(buffer));
      }

      if (!full.trim()) {
        throw new Error("模型接口未返回有效文本，请检查模型名称或接口兼容性。");
      }

      // Some OpenAI-compatible gateways and reverse proxies close a valid SSE
      // response without forwarding the final `done` frame. A clean browser EOF
      // with usable text is accepted; actual network failures make reader.read()
      // reject and are handled by the catch block below.
      const completionMode = receivedDone
        ? "AI模型流式模式"
        : (reachedCleanEof ? "AI模型兼容流式模式" : "AI模型流式模式");

      try {
        await reader.cancel();
      } catch (_) {}

      window.finishStreamingResult(key, full, completionMode);
      return { ok: true, content: full, mode: completionMode };
    } catch (err) {
      let message;
      if (err.name === "AbortError") {
        message = "请求超时，请缩短输入内容或检查模型接口后重试。";
      } else if (err.name === "TypeError" && /fetch|network|load/i.test(err.message || "")) {
        message = "模型流式连接异常中断，请检查网络或模型网关后重新生成。";
      } else {
        message = err.message || String(err);
      }
      window.failStreamingResult(key, message);
      throw new Error(message);
    } finally {
      clearTimeout(timer);
    }
  };

  window.downloadReportFile = async function downloadReportFile(url, filename, contentType) {
    const results = window.collectResultsForReport(true);
    await window.requestDownload(
      url,
      { results },
      filename,
      contentType,
      "还没有可导出的结果。",
      "报告导出超时，请精简结果内容后重试。",
    );
  };

  window.downloadModuleFile = async function downloadModuleFile(key, format) {
    const single = window.collectSingleModuleResult(key);
    if (!single.content) throw new Error("当前模块还没有生成结果，请先点击生成。");

    const safeTitle = single.title.replace(/[\\/:*?"<>|]/g, "_");
    const formats = {
      md: {
        url: "/api/report/markdown",
        filename: `${safeTitle}.md`,
        contentType: "text/markdown;charset=utf-8",
      },
      txt: {
        url: "/api/report/txt",
        filename: `${safeTitle}.txt`,
        contentType: "text/plain;charset=utf-8",
      },
      docx: {
        url: "/api/report/docx",
        filename: `${safeTitle}.docx`,
        contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      },
    };

    const selected = formats[format];
    if (!selected) throw new Error("不支持的导出格式。");

    await window.requestDownload(
      selected.url,
      { results: single.results },
      selected.filename,
      selected.contentType,
      "当前模块还没有可导出的结果。",
      "模块导出超时，请稍后重试。",
    );
  };

  window.updateModeBadge = function updateModeBadge() {
    const badge = document.getElementById("modeBadge");
    const homeStatus = document.getElementById("homeApiStatus");
    const topStatus = document.getElementById("topApiStatus");
    if (!badge) return;

    const cfg = window.getConfig();
    const values = [cfg.api_key, cfg.base_url, cfg.model].map((value) => String(value || "").trim());
    const hasAny = values.some(Boolean);
    const complete = values.every(Boolean);

    if (complete) {
      badge.textContent = "已配置";
      badge.className = "status-badge ai";
      if (homeStatus) homeStatus.textContent = "已配置";
      if (topStatus) {
        topStatus.textContent = "API 已配置";
        topStatus.className = "top-status ready";
      }
      return;
    }

    const label = hasAny ? "配置不完整" : "待配置";
    badge.textContent = label;
    badge.className = "status-badge local";
    if (homeStatus) homeStatus.textContent = label;
    if (topStatus) {
      topStatus.textContent = hasAny ? "API 配置不完整" : "API 待配置";
      topStatus.className = "top-status pending";
    }
  };

  window.updateModeBadge();
})();
