/* Human editing, confirmation, and organization review workflow. */
(() => {
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  if (!contracts) throw new Error("Workspace contracts must load before review workflow.");

  const CURRENT_PROJECT = contracts.storage.currentProject;
  const WORKSPACE_KEY = contracts.storage.workspaceKey;
  const MODULES = contracts.schemaResultKeys;
  const TITLES = contracts.resultTitles;
  const STATUS = {
    ai_draft: "AI 初稿",
    edited: "人工已编辑",
    pending_review: "待审核",
    changes_requested: "已退回修改",
    approved: "组织已批准",
    confirmed: "匿名空间已确认",
  };
  const ACTION = {
    save_edit: "保存人工编辑",
    submit_review: "提交审核",
    approve: "批准",
    request_changes: "退回修改",
    confirm: "本地确认",
    revert_ai: "恢复 AI 原始稿",
  };
  let cache = {};
  let activeModule = "";
  let activeDetail = null;

  const read = (raw, fallback) => { try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; } };
  const project = () => read(localStorage.getItem(CURRENT_PROJECT), null);
  const safe = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const context = () => {
    const organization = window.ZHILINK_ACCOUNT?.getActiveOrganization?.() || null;
    return { organization, role: organization?.role || "anonymous" };
  };

  async function request(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const key = localStorage.getItem(WORKSPACE_KEY) || "";
    if (key) headers.set("X-Workspace-Key", key);
    if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    const response = await fetch(path, { ...options, headers });
    const text = await response.text();
    const data = read(text, {});
    if (!response.ok) {
      const error = new Error(data.detail || text || "审核操作失败。");
      error.code = data.code || "REVIEW_REQUEST_FAILED";
      error.currentVersion = data.current_version;
      throw error;
    }
    return data;
  }

  async function hashText(text) {
    if (!window.crypto?.subtle) return "";
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(text || "")));
    return Array.from(new Uint8Array(digest), item => item.toString(16).padStart(2, "0")).join("");
  }

  function injectUi() {
    if (!document.querySelector("link[data-review-workflow]")) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "/assets/review-workflow.css";
      link.dataset.reviewWorkflow = "true";
      document.head.appendChild(link);
    }
    if (document.getElementById("reviewWorkflowModal")) return;
    const modal = document.createElement("div");
    modal.id = "reviewWorkflowModal";
    modal.className = "review-modal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div class="review-modal-backdrop" data-close-review></div>
      <section class="review-dialog" role="dialog" aria-modal="true" aria-labelledby="reviewDialogTitle">
        <header class="review-dialog-header">
          <div><span class="track">人工复核</span><h2 id="reviewDialogTitle">编辑、确认与审核</h2><p>审核动作会生成新的项目版本，并保留不可变操作记录。</p></div>
          <button class="icon-btn" type="button" data-close-review aria-label="关闭审核窗口">✕</button>
        </header>
        <div id="reviewWarning" class="review-warning" hidden></div>
        <div id="reviewStatusCard" class="review-status-card"></div>
        <label class="review-field"><span>当前工作稿</span><textarea id="reviewContentInput" rows="18" maxlength="80000"></textarea></label>
        <label class="review-field"><span>编辑说明 / 审核意见</span><textarea id="reviewNoteInput" rows="3" maxlength="2000" placeholder="说明修改原因、待补充信息或退回要求"></textarea></label>
        <details class="review-source-details"><summary>查看 AI 原始稿</summary><pre id="reviewSourceContent"></pre></details>
        <div id="reviewActionRow" class="review-action-row"></div>
        <section class="review-events-section"><div class="review-events-header"><h3>审核记录</h3><span>最近 100 条</span></div><div id="reviewEventList" class="review-event-list"></div></section>
      </section>`;
    document.body.appendChild(modal);
  }

  const statusClass = status => `review-status-${String(status || "ai_draft").replaceAll("_", "-")}`;

  async function decorate(module) {
    if (!MODULES.includes(module) || typeof state === "undefined" || !state.results[module]) return;
    const panel = document.getElementById(`${module}Result`);
    if (!panel) return;
    panel.querySelector(".review-workflow-bar")?.remove();
    const current = project();
    const summary = cache[module];
    let label = "保存项目后可人工复核";
    let mismatch = false;
    if (current && summary) {
      const localHash = await hashText(state.results[module] || "");
      mismatch = Boolean(localHash && summary.content_hash && localHash !== summary.content_hash);
      label = mismatch ? "新结果尚未保存，旧审核已失效" : (STATUS[summary.status] || summary.status);
    } else if (current) {
      label = "尚未建立审核状态";
    }
    const bar = document.createElement("div");
    bar.className = `review-workflow-bar ${summary ? statusClass(summary.status) : ""} ${mismatch ? "review-mismatch" : ""}`;
    bar.innerHTML = `<div class="review-workflow-state"><span class="review-state-dot"></span><div><strong>${safe(label)}</strong><small>${current ? `项目 v${current.lock_version}` : "当前仅为浏览器会话内容"}</small></div></div><button class="inline-action" data-open-review="${safe(module)}" type="button" ${current ? "" : "disabled"}>人工复核</button>`;
    const meta = panel.querySelector(".result-meta");
    if (meta) meta.insertAdjacentElement("afterend", bar); else panel.prepend(bar);
    window.dispatchEvent(new CustomEvent(contracts.events.reviewUpdated, { detail: { module } }));
  }

  async function decorateAll() {
    await Promise.all(MODULES.map(decorate));
  }

  async function loadSummaries() {
    const current = project();
    if (!current) { cache = {}; await decorateAll(); return; }
    try {
      const data = await request(`/api/projects/${encodeURIComponent(current.id)}/reviews`);
      cache = Object.fromEntries((data.items || []).map(item => [item.module, item]));
      if (data.project_lock_version && data.project_lock_version !== current.lock_version) {
        current.lock_version = data.project_lock_version;
        localStorage.setItem(CURRENT_PROJECT, JSON.stringify(current));
      }
    } catch (error) {
      cache = {};
      console.warn("review summaries unavailable", error);
    }
    await decorateAll();
  }

  function eventHtml(item) {
    const time = item.created_at ? new Date(item.created_at).toLocaleString() : "";
    return `<article class="review-event-item"><div><strong>${safe(ACTION[item.action] || item.action)}</strong><span>${safe(item.actor_name)} · ${safe(item.actor_role)} · ${safe(time)}</span></div><p>${safe(item.note || "无补充说明")}</p><small>${safe(STATUS[item.from_status] || item.from_status)} → ${safe(STATUS[item.to_status] || item.to_status)}</small></article>`;
  }

  function renderModal(detail, events, mismatch) {
    const review = detail.review;
    const role = context().role;
    const title = TITLES[activeModule] || "模块结果";
    document.getElementById("reviewDialogTitle").textContent = `${title} · 人工复核`;
    document.getElementById("reviewContentInput").value = detail.working_content || "";
    document.getElementById("reviewNoteInput").value = review.note || "";
    document.getElementById("reviewSourceContent").textContent = review.source_content || detail.working_content || "";
    const warning = document.getElementById("reviewWarning");
    warning.hidden = !mismatch;
    warning.textContent = mismatch ? "浏览器中的当前结果与项目已保存版本不同。请先在“项目”中保存当前结果，再开始审核。" : "";
    document.getElementById("reviewStatusCard").innerHTML = `<div><span class="review-status-pill ${statusClass(review.status)}">${safe(STATUS[review.status] || review.status)}</span><strong>修订 ${review.revision}</strong></div><p>最近更新：${safe(review.updated_by_name || "系统")} ${review.updated_at ? `· ${safe(new Date(review.updated_at).toLocaleString())}` : ""}</p>${review.submitted_by_name ? `<p>提交审核：${safe(review.submitted_by_name)} ${review.submitted_at ? `· ${safe(new Date(review.submitted_at).toLocaleString())}` : ""}</p>` : ""}${review.reviewed_by_name ? `<p>最近审核：${safe(review.reviewed_by_name)} ${review.reviewed_at ? `· ${safe(new Date(review.reviewed_at).toLocaleString())}` : ""}</p>` : ""}`;

    const canWrite = role !== "viewer";
    const canApprove = ["owner", "admin"].includes(role);
    const disabled = mismatch ? "disabled" : "";
    const actions = [];
    if (canWrite) {
      actions.push(`<button class="secondary" type="button" data-review-action="save_edit" ${disabled}>保存人工编辑</button>`);
      actions.push(`<button class="primary" type="button" data-review-action="submit_review" ${disabled}>提交审核</button>`);
      if (review.source_content) actions.push(`<button class="ghost" type="button" data-review-action="revert_ai" ${disabled}>恢复 AI 原始稿</button>`);
    }
    if (canApprove && review.status === "pending_review") {
      actions.push(`<button class="primary" type="button" data-review-action="approve" ${disabled}>批准</button>`);
      actions.push(`<button class="danger-light" type="button" data-review-action="request_changes" ${disabled}>退回修改</button>`);
    }
    if (role === "anonymous" && canWrite) actions.push(`<button class="primary" type="button" data-review-action="confirm" ${disabled}>本地确认</button>`);
    if (!canWrite) actions.push('<span class="review-readonly-note">当前为只读成员，只能查看审核状态和记录。</span>');
    document.getElementById("reviewActionRow").innerHTML = actions.join("");
    document.getElementById("reviewContentInput").readOnly = !canWrite || mismatch;
    document.getElementById("reviewNoteInput").readOnly = !canWrite || mismatch;
    document.getElementById("reviewEventList").innerHTML = events.items?.length ? events.items.map(eventHtml).join("") : '<p class="review-empty">暂无人工审核操作记录。</p>';
  }

  async function openReview(module) {
    const current = project();
    if (!current) { toast("请先保存当前项目，再开始人工复核。"); return; }
    activeModule = module;
    const modal = document.getElementById("reviewWorkflowModal");
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    document.getElementById("reviewStatusCard").innerHTML = "<p>正在读取审核状态...</p>";
    document.getElementById("reviewActionRow").innerHTML = "";
    try {
      const [detail, events] = await Promise.all([
        request(`/api/projects/${encodeURIComponent(current.id)}/reviews/${encodeURIComponent(module)}`),
        request(`/api/projects/${encodeURIComponent(current.id)}/reviews/${encodeURIComponent(module)}/events`),
      ]);
      activeDetail = detail;
      renderModal(detail, events, String(state.results[module] || "") !== String(detail.working_content || ""));
      setTimeout(() => document.getElementById("reviewContentInput")?.focus(), 30);
    } catch (error) {
      document.getElementById("reviewStatusCard").innerHTML = `<p class="review-error">${safe(error.message || String(error))}</p>`;
    }
  }

  function closeReview() {
    const modal = document.getElementById("reviewWorkflowModal");
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
    activeModule = "";
    activeDetail = null;
  }

  async function perform(action, button) {
    const current = project();
    if (!current || !activeModule || !activeDetail) return;
    const content = document.getElementById("reviewContentInput").value;
    const note = document.getElementById("reviewNoteInput").value.trim();
    if (action === "request_changes" && !note) { toast("退回修改时请填写明确的审核意见。"); return; }
    if (action === "revert_ai" && !confirm("确认恢复到 AI 原始稿吗？当前人工编辑会保留在历史中。")) return;
    const payload = { lock_version: current.lock_version, action, note };
    if (["save_edit", "submit_review"].includes(action)) payload.content = content;
    const original = button.textContent;
    button.disabled = true;
    button.textContent = "正在保存...";
    try {
      const data = await request(`/api/projects/${encodeURIComponent(current.id)}/reviews/${encodeURIComponent(activeModule)}/actions`, { method: "POST", body: JSON.stringify(payload) });
      const updated = data.project;
      localStorage.setItem(CURRENT_PROJECT, JSON.stringify({ id: updated.id, name: updated.name, description: updated.description || "", status: updated.status || "active", lock_version: updated.lock_version, updated_at: updated.updated_at || "" }));
      sessionStorage.setItem(contracts.storage.results, JSON.stringify(updated.snapshot?.results || {}));
      sessionStorage.setItem(contracts.storage.meta, JSON.stringify(updated.snapshot?.meta || {}));
      toast(`${ACTION[action] || "审核操作"}已保存为项目 v${updated.lock_version}。`);
      location.reload();
    } catch (error) {
      if (error.code === "PROJECT_VERSION_CONFLICT") {
        toast("项目已在其他页面更新，页面将重新载入最新版本。");
        setTimeout(() => location.reload(), 400);
      } else {
        toast(error.message || String(error));
        button.disabled = false;
        button.textContent = original;
      }
    }
  }

  window.addEventListener(contracts.events.resultUpdated, event => {
    const module = event.detail?.key;
    if (MODULES.includes(module)) Promise.resolve().then(() => decorate(module));
  });
  document.addEventListener("click", event => {
    const open = event.target.closest("[data-open-review]");
    if (open) { openReview(open.dataset.openReview); return; }
    if (event.target.closest("[data-close-review]")) { closeReview(); return; }
    const action = event.target.closest("[data-review-action]");
    if (action) perform(action.dataset.reviewAction, action);
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && document.getElementById("reviewWorkflowModal")?.classList.contains("show")) closeReview();
  });

  injectUi();
  document.addEventListener(contracts.events.accountReady, loadSummaries, { once: true });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", loadSummaries, { once: true });
  else loadSummaries();
  window.REVIEW_WORKFLOW_READY = true;
})();
