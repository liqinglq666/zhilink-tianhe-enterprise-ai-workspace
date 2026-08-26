import { execFileSync, spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const BASE_URL = process.env.ZHILINK_BROWSER_BASE_URL || "http://127.0.0.1:8000";
const DEBUG_PORT = Number(process.env.ZHILINK_BROWSER_DEBUG_PORT || 9222);
const DEBUG_ORIGIN = `http://127.0.0.1:${DEBUG_PORT}`;
const STEP_TIMEOUT_MS = Number(process.env.ZHILINK_BROWSER_TIMEOUT_MS || 20000);

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function which(binary) {
  try {
    return execFileSync("which", [binary], { encoding: "utf8" }).trim();
  } catch (_) {
    return "";
  }
}

function findChrome() {
  const candidates = [
    process.env.CHROME_BIN || "",
    which("google-chrome-stable"),
    which("google-chrome"),
    which("chromium"),
    which("chromium-browser"),
  ].filter(Boolean);
  if (!candidates.length) throw new Error("Headless Chrome/Chromium is not available on this runner.");
  return candidates[0];
}

async function waitFor(predicate, description, timeoutMs = STEP_TIMEOUT_MS) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const value = await predicate();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await sleep(100);
  }
  const suffix = lastError ? ` Last error: ${lastError.message || lastError}` : "";
  throw new Error(`Timed out waiting for ${description}.${suffix}`);
}

async function waitForDebugger() {
  return waitFor(async () => {
    const response = await fetch(`${DEBUG_ORIGIN}/json/version`);
    return response.ok ? response.json() : null;
  }, "Chrome DevTools endpoint");
}

class CdpClient {
  constructor(webSocketUrl) {
    this.socket = new WebSocket(webSocketUrl);
    this.sequence = 0;
    this.pending = new Map();
    this.listeners = new Map();
  }

  async open() {
    if (this.socket.readyState === WebSocket.OPEN) return;
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Timed out opening Chrome DevTools WebSocket.")), STEP_TIMEOUT_MS);
      this.socket.addEventListener("open", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
      this.socket.addEventListener("error", event => {
        clearTimeout(timer);
        reject(new Error(`Chrome DevTools WebSocket error: ${event.message || "unknown"}`));
      }, { once: true });
    });
    this.socket.addEventListener("message", event => this.handleMessage(event.data));
  }

  handleMessage(raw) {
    const message = JSON.parse(String(raw));
    if (message.id) {
      const entry = this.pending.get(message.id);
      if (!entry) return;
      this.pending.delete(message.id);
      if (message.error) entry.reject(new Error(`${entry.method}: ${message.error.message}`));
      else entry.resolve(message.result || {});
      return;
    }
    const listeners = this.listeners.get(message.method) || [];
    for (const listener of listeners) listener(message.params || {});
  }

  on(method, listener) {
    if (!this.listeners.has(method)) this.listeners.set(method, []);
    this.listeners.get(method).push(listener);
  }

  send(method, params = {}) {
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { method, resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    this.socket.close();
  }
}

async function main() {
  const chrome = findChrome();
  const profileDir = await mkdtemp(path.join(os.tmpdir(), "zhilink-browser-"));
  const downloadDir = await mkdtemp(path.join(os.tmpdir(), "zhilink-downloads-"));
  const chromeProcess = spawn(chrome, [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-extensions",
    "--no-first-run",
    "--remote-allow-origins=*",
    "--remote-debugging-address=127.0.0.1",
    `--remote-debugging-port=${DEBUG_PORT}`,
    `--user-data-dir=${profileDir}`,
    "--window-size=1440,1200",
    "about:blank",
  ], { stdio: ["ignore", "pipe", "pipe"] });

  let client = null;
  const browserErrors = [];
  const responses = [];

  try {
    await waitForDebugger();
    const targetResponse = await fetch(`${DEBUG_ORIGIN}/json/new?${encodeURIComponent(BASE_URL)}`, { method: "PUT" });
    assert(targetResponse.ok, `Could not create Chrome target: HTTP ${targetResponse.status}`);
    const target = await targetResponse.json();
    client = new CdpClient(target.webSocketDebuggerUrl);
    await client.open();

    client.on("Runtime.exceptionThrown", ({ exceptionDetails }) => {
      const text = exceptionDetails?.exception?.description || exceptionDetails?.text || "Runtime exception";
      browserErrors.push(text);
    });
    client.on("Runtime.consoleAPICalled", ({ type, args }) => {
      if (type !== "error") return;
      const text = (args || []).map(item => item.value ?? item.description ?? "").join(" ").trim();
      browserErrors.push(text || "console.error");
    });
    client.on("Network.responseReceived", ({ response }) => {
      responses.push({ url: response?.url || "", status: response?.status || 0 });
    });
    client.on("Page.javascriptDialogOpening", () => {
      client.send("Page.handleJavaScriptDialog", { accept: true }).catch(() => {});
    });

    await Promise.all([
      client.send("Page.enable"),
      client.send("Runtime.enable"),
      client.send("Network.enable"),
    ]);
    await client.send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: downloadDir });
    await client.send("Page.navigate", { url: BASE_URL });

    async function evaluate(expression, { awaitPromise = true } = {}) {
      const result = await client.send("Runtime.evaluate", {
        expression,
        awaitPromise,
        returnByValue: true,
        userGesture: true,
      });
      if (result.exceptionDetails) {
        const description = result.exceptionDetails.exception?.description || result.exceptionDetails.text || expression;
        throw new Error(description);
      }
      return result.result?.value;
    }

    async function waitJs(expression, description, timeoutMs = STEP_TIMEOUT_MS) {
      return waitFor(() => evaluate(`Boolean(${expression})`), description, timeoutMs);
    }

    async function click(selector) {
      const encoded = JSON.stringify(selector);
      const clicked = await evaluate(`(() => { const node = document.querySelector(${encoded}); if (!node) return false; node.click(); return true; })()`);
      assert(clicked, `Missing clickable element: ${selector}`);
    }

    async function setValue(selector, value) {
      const encodedSelector = JSON.stringify(selector);
      const encodedValue = JSON.stringify(String(value));
      const updated = await evaluate(`(() => {
        const node = document.querySelector(${encodedSelector});
        if (!node) return false;
        node.value = ${encodedValue};
        node.dispatchEvent(new Event("input", { bubbles: true }));
        node.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      assert(updated, `Missing input element: ${selector}`);
    }

    await waitJs(
      "document.readyState === 'complete' && window.ZHILINK_UI_V4_RUNTIME_READY && window.ZHILINK_UI_V4_SHELL_READY && window.ZHILINK_UI_V4_RESULTS_READY && window.ZHILINK_API_DRAWER_V4_READY && window.ZHILINK_MODEL_CONFIG_SAVE_V4_READY && window.PROJECT_STORAGE_READY",
      "workspace runtime readiness",
      30000,
    );

    assert(await evaluate("document.documentElement.dataset.zhilinkUi") === "v4", "V4 shell marker is missing.");
    assert(await evaluate("document.querySelector('.page.active-page')?.id") === "home", "Home is not the initial active page.");

    for (const section of ["meeting", "contract", "policy", "match", "profile", "landing", "report", "home"]) {
      await click(`.nav button[data-section="${section}"]`);
      await waitJs(`document.querySelector('.page.active-page')?.id === ${JSON.stringify(section)}`, `${section} navigation`);
    }

    await click("#openApiSettings");
    await waitJs("document.body.classList.contains('ui-v4-api-open') && document.getElementById('apiPanel')?.getAttribute('aria-hidden') === 'false'", "AI service drawer open");
    const currentTemperature = Number(await evaluate("document.getElementById('temperature')?.value || 0.35"));
    const nextTemperature = Math.abs(currentTemperature - 0.42) < 0.001 ? 0.43 : 0.42;
    await setValue("#temperature", nextTemperature);
    await waitJs("document.getElementById('saveApiConfig')?.disabled === false && document.getElementById('modelConfigDraftStatus')?.dataset.state === 'dirty'", "model configuration dirty state");
    await click("#saveApiConfig");
    await waitJs(`localStorage.getItem('zhilian_temperature') === ${JSON.stringify(String(nextTemperature))} && !document.body.classList.contains('ui-v4-api-open')`, "explicit model configuration save");

    await click('.nav button[data-section="home"]');
    await waitJs("document.querySelector('.page.active-page')?.id === 'home'", "return to home");
    await click("#uiV4CreateProject");
    await waitJs("document.getElementById('projectManagerModal')?.classList.contains('show')", "project manager open");
    const projectName = `浏览器验收项目-${Date.now()}`;
    await setValue("#projectNameInput", projectName);
    await setValue("#projectDescriptionInput", "CI Headless Chrome 端到端验收项目，可自动删除。");
    await click("#createProjectButton");
    await waitJs(`JSON.parse(localStorage.getItem('zhilian_current_project_v1') || 'null')?.name === ${JSON.stringify(projectName)}`, "project v1 creation", 30000);
    await click("[data-close-project-manager]");

    await click('.nav button[data-section="meeting"]');
    await waitJs("document.querySelector('.page.active-page')?.id === 'meeting'", "meeting workspace open");
    await setValue("#meetingInput", "项目组确认本周完成浏览器验收，负责人和最终截止时间仍需人工确认。下一步保存项目版本并检查导出。 ");
    const syntheticResult = [
      "## 一句话结论",
      "浏览器验收已覆盖核心工作区主链。",
      "",
      "## 关键决策",
      "| 事项 | 状态 | 待确认信息 |",
      "|---|---|---|",
      "| 保存浏览器验收结果 | 已确认 | 无 |",
      "",
      "## 待办事项",
      "| 事项 | 负责人 | 截止时间 | 待确认信息 |",
      "|---|---|---|---|",
      "| 完成端到端验收 | 待确认 | 待确认 | 负责人和日期待确认 |",
      "",
      "## 待确认信息",
      "- 浏览器验收负责人和最终截止时间待确认。",
    ].join("\n");
    await evaluate(`setResult('meeting', { ok: true, content: ${JSON.stringify(syntheticResult)}, mode: '浏览器验收', error: '' })`);
    await waitJs("Boolean(state.results.meeting) && document.querySelector('#meetingResult .copy-result') && document.querySelector('#meetingResult .export-result')", "committed meeting result presentation");
    await waitJs("document.getElementById('openProjectManager')?.textContent.includes('未保存')", "project dirty state after committed result");
    await waitJs("Boolean(window.ZHILINK_STRUCTURED?.get?.('meeting'))", "structured meeting result", 30000);

    await click("#uiV4ProjectContext");
    await waitJs("document.getElementById('projectManagerModal')?.classList.contains('show')", "project manager reopen");
    await click("#saveProjectButton");
    await waitJs("JSON.parse(localStorage.getItem('zhilian_current_project_v1') || 'null')?.lock_version >= 2 && !document.getElementById('openProjectManager')?.textContent.includes('未保存')", "project v2 save", 30000);
    await click("#showProjectHistoryButton");
    await waitJs("document.querySelectorAll('#projectHistoryList .project-version-item').length >= 2", "project version history", 30000);
    await click("[data-close-project-manager]");

    await waitJs("Boolean(document.querySelector('#meetingResult [data-open-review=\"meeting\"]'))", "review action available", 30000);
    await click('#meetingResult [data-open-review="meeting"]');
    await waitJs("document.getElementById('reviewWorkflowModal')?.classList.contains('show') && !document.getElementById('reviewStatusCard')?.textContent.includes('正在读取')", "review workflow open", 30000);
    await click("[data-close-review]");

    await waitJs("Boolean(document.querySelector('#meetingResult [data-open-structured=\"meeting\"]'))", "structured result action available", 30000);
    await click('#meetingResult [data-open-structured="meeting"]');
    await waitJs("document.getElementById('structuredResultModal')?.classList.contains('show') && document.getElementById('structuredRawJson')?.textContent.length > 20", "structured JSON modal");
    await click("#downloadStructuredJson");
    await click("[data-close-structured]");

    const responseStart = responses.length;
    await evaluate("window.ZHILINK_RESULTS.downloadModuleFile('meeting', 'txt')");
    const exportResponse = responses.slice(responseStart).find(item => item.url.includes("/api/report/txt"));
    assert(exportResponse?.status === 200, `Meeting TXT export did not return HTTP 200: ${JSON.stringify(exportResponse || null)}`);

    const currentProject = await evaluate("JSON.parse(localStorage.getItem('zhilian_current_project_v1') || 'null')");
    assert(currentProject?.id && currentProject.lock_version >= 2, "Saved project state was not retained in localStorage.");

    await evaluate(`fetch('/api/projects/' + encodeURIComponent(${JSON.stringify(currentProject?.id || "")}), { method: 'DELETE' }).then(response => { if (!response.ok) throw new Error('cleanup HTTP ' + response.status); return response.json(); })`);

    await sleep(300);
    assert(browserErrors.length === 0, `Browser runtime errors detected:\n${browserErrors.join("\n---\n")}`);
    console.log("Browser acceptance smoke passed: navigation, model config save, project versions, result commit, structured JSON, review entry, and export.");
  } finally {
    try { client?.close(); } catch (_) {}
    if (!chromeProcess.killed) chromeProcess.kill("SIGTERM");
    await Promise.all([
      rm(profileDir, { recursive: true, force: true }),
      rm(downloadDir, { recursive: true, force: true }),
    ]);
  }
}

main().catch(error => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
