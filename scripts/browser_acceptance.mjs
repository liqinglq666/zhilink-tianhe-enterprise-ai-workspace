import { execFileSync, spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const BASE_URL = process.env.ZHILINK_BROWSER_BASE_URL || "http://127.0.0.1:8000";
const DEBUG_PORT = Number(process.env.ZHILINK_BROWSER_DEBUG_PORT || 9222);
const DEBUG_ORIGIN = `http://127.0.0.1:${DEBUG_PORT}`;
const STEP_TIMEOUT_MS = Number(process.env.ZHILINK_BROWSER_TIMEOUT_MS || 20000);

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const assert = (condition, message) => { if (!condition) throw new Error(message); };

function which(binary) {
  try { return execFileSync("which", [binary], { encoding: "utf8" }).trim(); }
  catch (_) { return ""; }
}

function findChrome() {
  const candidate = [
    process.env.CHROME_BIN || "",
    which("google-chrome-stable"),
    which("google-chrome"),
    which("chromium"),
    which("chromium-browser"),
  ].find(Boolean);
  if (!candidate) throw new Error("Headless Chrome/Chromium is not available on this runner.");
  return candidate;
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

class CdpClient {
  constructor(webSocketUrl) {
    this.socket = new WebSocket(webSocketUrl);
    this.sequence = 0;
    this.pending = new Map();
    this.listeners = new Map();
  }

  async open() {
    if (this.socket.readyState !== WebSocket.OPEN) {
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error("Timed out opening Chrome DevTools WebSocket.")), STEP_TIMEOUT_MS);
        this.socket.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
        this.socket.addEventListener("error", event => {
          clearTimeout(timer);
          reject(new Error(`Chrome DevTools WebSocket error: ${event.message || "unknown"}`));
        }, { once: true });
      });
    }
    this.socket.addEventListener("message", event => this.handleMessage(event.data));
  }

  handleMessage(raw) {
    const message = JSON.parse(String(raw));
    if (message.id) {
      const pending = this.pending.get(message.id);
      if (!pending) return;
      this.pending.delete(message.id);
      if (message.error) pending.reject(new Error(`${pending.method}: ${message.error.message}`));
      else pending.resolve(message.result || {});
      return;
    }
    for (const listener of this.listeners.get(message.method) || []) listener(message.params || {});
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
    try { this.socket.close(); } catch (_) {}
  }
}

async function stopProcess(child) {
  if (!child || child.exitCode !== null) return;
  child.kill("SIGTERM");
  await Promise.race([
    new Promise(resolve => child.once("exit", resolve)),
    sleep(3000),
  ]);
  if (child.exitCode === null) child.kill("SIGKILL");
}

async function safeRemove(directory) {
  for (let attempt = 0; attempt < 8; attempt += 1) {
    try {
      await rm(directory, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
      return;
    } catch (error) {
      if (attempt === 7) {
        console.warn(`[browser] cleanup warning for ${directory}: ${error.message || error}`);
        return;
      }
      await sleep(150);
    }
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
    await waitFor(async () => {
      const response = await fetch(`${DEBUG_ORIGIN}/json/version`);
      return response.ok;
    }, "Chrome DevTools endpoint");

    const targetsResponse = await fetch(`${DEBUG_ORIGIN}/json/list`);
    assert(targetsResponse.ok, `Could not list Chrome targets: HTTP ${targetsResponse.status}`);
    const targets = await targetsResponse.json();
    const target = targets.find(item => item.type === "page");
    assert(target?.webSocketDebuggerUrl, "Chrome did not expose a page target.");

    client = new CdpClient(target.webSocketDebuggerUrl);
    await client.open();
    client.on("Runtime.exceptionThrown", ({ exceptionDetails }) => {
      browserErrors.push(exceptionDetails?.exception?.description || exceptionDetails?.text || "Runtime exception");
    });
    client.on("Runtime.consoleAPICalled", ({ type, args }) => {
      if (type !== "error") return;
      browserErrors.push((args || []).map(item => item.value ?? item.description ?? "").join(" ").trim() || "console.error");
    });
    client.on("Network.responseReceived", ({ response }) => {
      responses.push({ url: response?.url || "", status: response?.status || 0 });
    });
    client.on("Page.javascriptDialogOpening", () => {
      client.send("Page.handleJavaScriptDialog", { accept: true }).catch(() => {});
    });

    await Promise.all([client.send("Page.enable"), client.send("Runtime.enable"), client.send("Network.enable")]);
    await client.send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: downloadDir });

    async function evaluate(expression) {
      const result = await client.send("Runtime.evaluate", {
        expression,
        awaitPromise: true,
        returnByValue: true,
        userGesture: true,
      });
      if (result.exceptionDetails) {
        throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text || expression);
      }
      return result.result?.value;
    }

    async function waitJs(expression, description, timeoutMs = STEP_TIMEOUT_MS) {
      return waitFor(() => evaluate(`Boolean(${expression})`), description, timeoutMs);
    }

    async function click(selector) {
      const ok = await evaluate(`(() => { const node = document.querySelector(${JSON.stringify(selector)}); if (!node) return false; node.click(); return true; })()`);
      assert(ok, `Missing clickable element: ${selector}`);
    }

    async function setValue(selector, value) {
      const ok = await evaluate(`(() => {
        const node = document.querySelector(${JSON.stringify(selector)});
        if (!node) return false;
        node.value = ${JSON.stringify(String(value))};
        node.dispatchEvent(new Event("input", { bubbles: true }));
        node.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      assert(ok, `Missing input element: ${selector}`);
    }

    console.log(`[browser] opening ${BASE_URL}`);
    await client.send("Page.navigate", { url: BASE_URL });
    await waitJs("document.readyState === 'complete'", "document load", 30000);

    const readinessExpression = `(() => ({
      runtime: Boolean(window.ZHILINK_UI_V4_RUNTIME_READY),
      shell: Boolean(window.ZHILINK_UI_V4_SHELL_READY),
      results: Boolean(window.ZHILINK_UI_V4_RESULTS_READY),
      drawer: Boolean(window.ZHILINK_API_DRAWER_V4_READY),
      modelConfig: Boolean(window.ZHILINK_MODEL_CONFIG_SAVE_V4_READY),
      projects: Boolean(window.PROJECT_STORAGE_READY),
      dashboard: Boolean(window.ZHILINK_UI_V4_DASHBOARD_READY),
      structured: Boolean(window.ZHILINK_STRUCTURED_READY),
      review: Boolean(window.REVIEW_WORKFLOW_READY)
    }))()`;
    await waitFor(async () => {
      const flags = await evaluate(readinessExpression);
      return Object.values(flags || {}).every(Boolean) ? flags : false;
    }, "workspace runtime readiness", 30000).catch(async error => {
      const flags = await evaluate(readinessExpression).catch(() => ({}));
      const pageState = await evaluate("({ readyState: document.readyState, title: document.title, bodyClass: document.body?.className || '' })").catch(() => ({}));
      throw new Error(`${error.message}\nReadiness: ${JSON.stringify(flags)}\nPage: ${JSON.stringify(pageState)}\nBrowser errors: ${browserErrors.join(" | ") || "none"}`);
    });
    console.log("[browser] runtime ready");

    assert(await evaluate("document.documentElement.dataset.zhilinkUi") === "v4", "V4 shell marker is missing.");
    assert(await evaluate("document.querySelector('.page.active-page')?.id") === "home", "Home is not the initial active page.");

    for (const section of ["meeting", "contract", "policy", "match", "profile", "landing", "report", "home"]) {
      await click(`.nav button[data-section="${section}"]`);
      await waitJs(`document.querySelector('.page.active-page')?.id === ${JSON.stringify(section)}`, `${section} navigation`);
    }
    console.log("[browser] navigation passed");

    await click("#openApiSettings");
    await waitJs("document.body.classList.contains('ui-v4-api-open') && document.getElementById('apiPanel')?.getAttribute('aria-hidden') === 'false'", "AI service drawer open");
    const currentTemperature = Number(await evaluate("document.getElementById('temperature')?.value || 0.35"));
    const nextTemperature = Number((currentTemperature >= 0.95 ? currentTemperature - 0.05 : currentTemperature + 0.05).toFixed(2));
    await setValue("#temperature", nextTemperature);
    const acceptedTemperature = String(await evaluate("document.getElementById('temperature')?.value || ''"));
    assert(acceptedTemperature && Number(acceptedTemperature) !== currentTemperature, "Temperature control did not accept a different valid step value.");
    await waitJs("document.getElementById('saveApiConfig')?.disabled === false && document.getElementById('modelConfigDraftStatus')?.dataset.state === 'dirty'", "model configuration dirty state");
    await click("#saveApiConfig");
    await waitJs(`localStorage.getItem('zhilian_temperature') === ${JSON.stringify(acceptedTemperature)}`, "model configuration persistence").catch(async error => {
      const saved = await evaluate("({ stored: localStorage.getItem('zhilian_temperature'), active: window.ZHILINK_MODEL_CONFIG?.getActiveConfig?.().temperature, input: document.getElementById('temperature')?.value, indicator: document.getElementById('modelConfigDraftStatus')?.dataset.state, saveDisabled: document.getElementById('saveApiConfig')?.disabled })").catch(() => ({}));
      throw new Error(`${error.message}\nModel config state: ${JSON.stringify(saved)}`);
    });
    await waitJs("!document.body.classList.contains('ui-v4-api-open') && document.getElementById('apiPanel')?.getAttribute('aria-hidden') === 'true'", "AI service drawer close after save").catch(async error => {
      const drawer = await evaluate("({ bodyOpen: document.body.classList.contains('ui-v4-api-open'), ariaHidden: document.getElementById('apiPanel')?.getAttribute('aria-hidden') })").catch(() => ({}));
      throw new Error(`${error.message}\nDrawer state: ${JSON.stringify(drawer)}`);
    });
    console.log("[browser] model configuration save passed");

    await click('.nav button[data-section="home"]');
    await waitJs("Boolean(document.getElementById('uiV4CreateProject'))", "create project action");
    await click("#uiV4CreateProject");
    await waitJs("document.getElementById('projectManagerModal')?.classList.contains('show')", "project manager open");
    const projectName = `浏览器验收项目-${Date.now()}`;
    await setValue("#projectNameInput", projectName);
    await setValue("#projectDescriptionInput", "CI Headless Chrome 端到端验收项目，可自动删除。");
    await click("#createProjectButton");
    await waitJs(`JSON.parse(localStorage.getItem('zhilian_current_project_v1') || 'null')?.name === ${JSON.stringify(projectName)}`, "project v1 creation", 30000);
    await click("[data-close-project-manager]");
    console.log("[browser] project v1 passed");

    await click('.nav button[data-section="meeting"]');
    await setValue("#meetingInput", "项目组确认本周完成浏览器验收，负责人和最终截止时间仍需人工确认。下一步保存项目版本并检查导出。");
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
    console.log("[browser] result commit and structured conversion passed");

    await click("#uiV4ProjectContext");
    await waitJs("document.getElementById('projectManagerModal')?.classList.contains('show')", "project manager reopen");
    await click("#saveProjectButton");
    await waitJs("JSON.parse(localStorage.getItem('zhilian_current_project_v1') || 'null')?.lock_version >= 2 && !document.getElementById('openProjectManager')?.textContent.includes('未保存')", "project v2 save", 30000);
    await click("#showProjectHistoryButton");
    await waitJs("document.querySelectorAll('#projectHistoryList .project-version-item').length >= 2", "project version history", 30000);
    await click("[data-close-project-manager]");
    console.log("[browser] project v2 and history passed");

    await waitJs("Boolean(document.querySelector('#meetingResult [data-open-review=\"meeting\"]'))", "review action available", 30000);
    await click('#meetingResult [data-open-review="meeting"]');
    await waitJs("document.getElementById('reviewWorkflowModal')?.classList.contains('show') && !document.getElementById('reviewStatusCard')?.textContent.includes('正在读取')", "review workflow open", 30000);
    await click("[data-close-review]");
    console.log("[browser] review entry passed");

    await waitJs("Boolean(document.querySelector('#meetingResult [data-open-structured=\"meeting\"]'))", "structured result action available", 30000);
    await click('#meetingResult [data-open-structured="meeting"]');
    await waitJs("document.getElementById('structuredResultModal')?.classList.contains('show') && document.getElementById('structuredRawJson')?.textContent.length > 20", "structured JSON modal");
    await click("#downloadStructuredJson");
    await click("[data-close-structured]");

    const responseStart = responses.length;
    await evaluate("window.ZHILINK_RESULTS.downloadModuleFile('meeting', 'txt')");
    const exportResponse = responses.slice(responseStart).find(item => item.url.includes("/api/report/txt"));
    assert(exportResponse?.status === 200, `Meeting TXT export did not return HTTP 200: ${JSON.stringify(exportResponse || null)}`);
    console.log("[browser] structured JSON and TXT export passed");

    const currentProject = await evaluate("JSON.parse(localStorage.getItem('zhilian_current_project_v1') || 'null')");
    assert(currentProject?.id && currentProject.lock_version >= 2, "Saved project state was not retained in localStorage.");
    await evaluate(`fetch('/api/projects/' + encodeURIComponent(${JSON.stringify(currentProject?.id || "")}), {
      method: 'DELETE',
      headers: { 'X-Workspace-Key': localStorage.getItem('zhilian_workspace_key_v1') || '' },
      credentials: 'same-origin'
    }).then(response => { if (!response.ok) throw new Error('cleanup HTTP ' + response.status); return response.json(); })`);

    await sleep(250);
    assert(browserErrors.length === 0, `Browser runtime errors detected:\n${browserErrors.join("\n---\n")}`);
    console.log("Browser acceptance smoke passed: navigation, model config save, project versions, result commit, structured JSON, review entry, and export.");
  } finally {
    client?.close();
    await stopProcess(chromeProcess);
    await safeRemove(profileDir);
    await safeRemove(downloadDir);
  }
}

main().catch(error => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
