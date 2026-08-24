/* Enterprise service workflow: customer-facing progress, responsibility and review. */
(() => {
  const ACCOUNT_READY_EVENT = "zhilink:account-ready";
  const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1";
  const REQUEST_TIMEOUT_MS = 20000;

  const CASE_LABELS = {
    draft: "草稿",
    active: "处理中",
    on_hold: "已暂停",
    pending_review: "待结项审核",
    completed: "已结项",
    cancelled: "已取消",
  };
  const NODE_LABELS = {
    pending: "未开始",
    in_progress: "处理中",
    blocked: "受阻",
    pending_review: "待审核",
    completed: "已完成",
    skipped: "已跳过",
  };
  const REVIEW_LABELS = {
    ai_draft: "AI 初稿",
    edited: "人工已编辑",
    pending_review: "待审核",
    changes_requested: "已退回修改",
    approved: "已批准",
    confirmed: "已确认",
  };
  const ACTION_LABELS = {
    create: "创建流程",
    activate: "启动流程",
    hold: "暂停流程",
    resume: "恢复流程",
    submit_review: "提交结项审核",
    complete: "批准结项",
    cancel: "取消流程",
    reopen: "重新打开流程",
    context_refresh: "更新办理依据",
    refresh_context: "更新办理依据",
    node_start: "开始处理节点",
    node_submit: "提交节点审核",
    node_approve: "批准节点",
    node_return: "退回节点",
    node_block: "标记节点受阻",
    node_resume: "恢复节点",
    node_skip: "跳过节点",
    node_reopen: "重新打开节点",
    assign: "调整责任人",
    update_assignment: "调整责任人",
  };
  const ROLE_LABELS = {
    owner: "所有者",
    admin: "管理员",
    editor: "编辑者",
    viewer: "只读成员",
    anonymous: "本机用户",
  };
  const PRIORITY_LABELS = {
    low: "低",
    normal: "普通",
    high: "高",
    urgent: "紧急",
  };
  const MODULE_LABELS = {
    meeting: "会议纪要",
    contract: "合同审阅",
    policy: "政策助手",
    match: "供需协作",
    profile: "企业档案",
    landing: "实施计划",
    report: "报告归档",
  };

  let activeCase = null;
  let members = [];
  let events = [];

  const escapeHtml = value => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  function parseJson(raw, fallback = null) {
    try { return raw ? JSON.parse(raw) : fallback; }
    catch (_) { return fallback; }
  }

  function account() {
    return window.ZHILINK_ACCOUNT?.getSession?.() || { authenticated: false, csrf_token: "" };
  }

  function organization() {
    return window.ZHILINK_ACCOUNT?.getActiveOrganization?.() || null;
  }

  function role() {
    return organization()?.role || "";
  }

  function canEdit() {
    return ["owner", "admin", "editor"].includes(role());
  }

  function canReview() {
    return ["owner", "admin"].includes(role());
  }

  function notify(message) {
    if (typeof toast === "function") toast(message);
    else console.info(message);
  }

  function currentProject() {
    return parseJson(localStorage.getItem(CURRENT_PROJECT_STORAGE), null);
  }

  function uniqueCitations(values) {
    return Array.from(new Set((values || []).map(value => String(value || "").trim()).filter(Boolean))).slice(0, 20);
  }

  function recentKnowledgeCitations() {
    return uniqueCitations(
      (window.ZHILINK_KNOWLEDGE?.getLastSearch?.()?.items || []).map(item => item.citation_id),
    );
  }

  function existingKnowledgeCitations() {
    return uniqueCitations(
      (activeCase?.context?.knowledge_references || []).map(item => item.citation_id),
    );
  }

  function caseLabel(status) {
    return CASE_LABELS[status] || String(status || "");
  }

  function nodeLabel(status) {
    return NODE_LABELS[status] || String(status || "");
  }

  function reviewLabel(status) {
    return REVIEW_LABELS[status] || caseLabel(status) || String(status || "");
  }

  function actionLabel(action) {
    return ACTION_LABELS[action] || String(action || "操作");
  }

  function roleLabel(value) {
    return ROLE_LABELS[value] || String(value || "");
  }

  async function request(path, options = {}) {
    const org = organization();
    const session = account();
    if (!org || !session.authenticated) throw new Error("请先登录并选择组织空间。");

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    const method = options.method || "GET";
    const headers = { "X-Organization-Id": org.id, ...(options.headers || {}) };
    if (options.body) headers["Content-Type"] = "application/json";
    if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
      headers["X-CSRF-Token"] = session.csrf_token || "";
    }

    try {
      const response = await fetch(path, {
        ...options,
        method,
        headers,
        credentials: "same-origin",
        signal: controller.signal,
      });
      const text = await response.text();
      const data = parseJson(text, {});
      if (!response.ok) throw new Error(data.detail || text || "服务跟进操作失败。");
      return data;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("服务跟进请求超时，请稍后重试。");
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  function injectUi() {
    const topActions = document.querySelector(".top-actions");
    if (topActions && !document.getElementById("openServiceWorkflow")) {
      const button = document.createElement("button");
      button.id = "openServiceWorkflow";
      button.className = "secondary";
      button.type = "button";
      button.textContent = "服务跟进";
      button.hidden = true;
      button.addEventListener("click", openWorkflow);
      const reportButton = topActions.querySelector('[data-goto="report"]');
      topActions.insertBefore(button, reportButton || topActions.firstChild);
    }

    if (document.getElementById("serviceWorkflowModal")) return;
    const modal = document.createElement("div");
    modal.id = "serviceWorkflowModal";
    modal.className = "service-workflow-modal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div class="service-workflow-backdrop" data-sw-close></div>
      <section class="service-workflow-dialog" role="dialog" aria-modal="true" aria-labelledby="swDialogTitle">
        <header>
          <div>
            <span class="track">服务跟进</span>
            <h2 id="swDialogTitle">事项进度与责任协作</h2>
            <p>围绕当前项目推进负责人、关键节点、复核和结项。项目内容更新后请同步更新办理依据。</p>
          </div>
          <button class="icon-btn" data-sw-close type="button" aria-label="关闭服务跟进">✕</button>
        </header>
        <div class="service-workflow-toolbar">
          <div>
            <button id="swNew" class="primary" type="button">从当前项目新建</button>
            <button id="swRefresh" class="secondary" type="button">刷新</button>
          </div>
          <select id="swFilter" aria-label="按状态筛选服务事项">
            <option value="">全部状态</option>
            <option value="draft">草稿</option>
            <option value="active">处理中</option>
            <option value="on_hold">已暂停</option>
            <option value="pending_review">待结项审核</option>
            <option value="completed">已结项</option>
            <option value="cancelled">已取消</option>
          </select>
        </div>
        <div class="service-workflow-layout">
          <aside><div id="swList"></div></aside>
          <main id="swDetail"><p class="sw-empty">选择一个事项，或从当前已保存项目新建。</p></main>
        </div>
      </section>`;
    document.body.appendChild(modal);
    modal.addEventListener("click", handleClick);
    document.getElementById("swNew").addEventListener("click", renderCreateForm);
    document.getElementById("swRefresh").addEventListener("click", listCases);
    document.getElementById("swFilter").addEventListener("change", listCases);
  }

  function updateVisibility() {
    const openButton = document.getElementById("openServiceWorkflow");
    if (openButton) openButton.hidden = !organization();
    const newButton = document.getElementById("swNew");
    if (newButton) newButton.hidden = !canEdit();
  }

  function openWorkflow() {
    if (!organization()) {
      notify("请先登录并选择组织空间。");
      return;
    }
    const modal = document.getElementById("serviceWorkflowModal");
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    Promise.all([loadMembers(), listCases()]).catch(error => notify(error.message));
  }

  function closeWorkflow() {
    const modal = document.getElementById("serviceWorkflowModal");
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
  }

  async function loadMembers() {
    try {
      const data = await request(`/api/organizations/${encodeURIComponent(organization().id)}/members`);
      members = (data.items || []).filter(item => ["owner", "admin", "editor"].includes(item.role));
    } catch (_) {
      members = [];
    }
  }

  function memberOptions(selectedId = "") {
    return members.map(member => `
      <option value="${escapeHtml(member.user_id)}" ${member.user_id === selectedId ? "selected" : ""}>
        ${escapeHtml(member.display_name)} · ${escapeHtml(roleLabel(member.role))}
      </option>`).join("");
  }

  async function listCases() {
    const list = document.getElementById("swList");
    const status = document.getElementById("swFilter")?.value || "";
    if (!list) return;
    list.innerHTML = '<p class="sw-empty">读取中...</p>';
    try {
      const data = await request(`/api/service-cases?limit=100&status=${encodeURIComponent(status)}`);
      const items = data.items || [];
      list.innerHTML = items.length ? items.map(item => `
        <button class="sw-list-item ${activeCase?.id === item.id ? "active" : ""}" data-sw-id="${escapeHtml(item.id)}" type="button">
          <span>
            <strong>${escapeHtml(item.title)}</strong>
            <small>${escapeHtml(item.case_number)} · ${escapeHtml(item.owner_name)} · ${item.completed_nodes}/${item.total_nodes}</small>
          </span>
          <em>${escapeHtml(caseLabel(item.status))}</em>
        </button>`).join("") : '<p class="sw-empty">暂无服务事项。</p>';
    } catch (error) {
      list.innerHTML = `<p class="sw-error">${escapeHtml(error.message)}</p>`;
    }
  }

  function renderCreateForm() {
    const project = currentProject();
    const detail = document.getElementById("swDetail");
    if (!project?.id) {
      detail.innerHTML = '<p class="sw-empty">请先打开并保存一个组织项目。</p>';
      return;
    }
    detail.innerHTML = `
      <section class="sw-card">
        <h3>新建服务事项</h3>
        <p>绑定项目：${escapeHtml(project.name)}</p>
        <div class="sw-grid">
          <label>事项名称<input id="swTitle" value="${escapeHtml((project.name || "企业") + "服务跟进")}"></label>
          <label>优先级
            <select id="swPriority">
              <option value="normal">普通</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
              <option value="low">低</option>
            </select>
          </label>
          <label>负责人<select id="swOwner">${memberOptions(account().user?.id || "")}</select></label>
          <label>目标日期<input id="swDue" type="date"></label>
          <label class="wide">服务目标<textarea id="swObjective" rows="4"></textarea></label>
        </div>
        <p class="sw-empty">办理依据会自动使用当前项目内容及最近可用的组织知识。</p>
        <button class="primary" data-sw-create type="button">创建事项与默认节点</button>
      </section>`;
  }

  async function createCase() {
    const project = currentProject();
    if (!project?.id) return;
    try {
      activeCase = await request("/api/service-cases", {
        method: "POST",
        body: JSON.stringify({
          project_id: project.id,
          title: document.getElementById("swTitle").value.trim(),
          objective: document.getElementById("swObjective").value.trim(),
          priority: document.getElementById("swPriority").value,
          owner_user_id: document.getElementById("swOwner").value || null,
          due_date: document.getElementById("swDue").value || null,
          knowledge_citations: recentKnowledgeCitations(),
        }),
      });
      notify("服务事项已创建。");
      await Promise.all([loadEvents(), listCases()]);
      renderCase();
    } catch (error) {
      notify(error.message);
    }
  }

  async function loadCase(id) {
    const detail = document.getElementById("swDetail");
    detail.innerHTML = '<p class="sw-empty">读取中...</p>';
    try {
      activeCase = await request(`/api/service-cases/${encodeURIComponent(id)}`);
      await loadEvents();
      renderCase();
      listCases();
    } catch (error) {
      detail.innerHTML = `<p class="sw-error">${escapeHtml(error.message)}</p>`;
    }
  }

  function contextSection(context) {
    const modules = context.modules || [];
    const policies = context.official_policy_references || [];
    const knowledge = context.knowledge_references || [];
    const pending = context.pending_items || [];
    return `
      <section class="sw-card">
        <div class="sw-heading">
          <div>
            <h4>当前办理依据</h4>
            <p>项目材料、官方政策、组织知识和待确认事项。</p>
          </div>
          ${canEdit() ? '<button class="secondary" data-sw-context type="button">更新办理依据</button>' : ""}
        </div>
        <div class="sw-context">
          <article>
            <strong>项目材料 ${modules.length}</strong>
            ${modules.map(item => `<p><b>${escapeHtml(MODULE_LABELS[item.module] || item.module)}</b> · ${escapeHtml(reviewLabel(item.review_status))}<br>${escapeHtml(item.excerpt)}</p>`).join("") || "<p>无</p>"}
          </article>
          <article>
            <strong>官方政策 ${policies.length}</strong>
            ${policies.map(item => `<p><b>${escapeHtml(item.title || "政策材料")}</b>${item.official_url ? ` <a href="${escapeHtml(item.official_url)}" target="_blank" rel="noopener noreferrer">查看原文</a>` : ""}</p>`).join("") || "<p>无</p>"}
          </article>
          <article>
            <strong>组织知识 ${knowledge.length}</strong>
            ${knowledge.map(item => `<p><b>${escapeHtml(item.title || "组织材料")}</b></p>`).join("") || "<p>无</p>"}
          </article>
          <article>
            <strong>待确认 ${pending.length}</strong>
            ${pending.map(item => `<p><b>${escapeHtml(MODULE_LABELS[item.module] || item.module)}</b> ${escapeHtml(item.text)}</p>`).join("") || "<p>无</p>"}
          </article>
        </div>
      </section>`;
  }

  function eventHtml(item) {
    return `
      <div class="sw-event">
        <strong>${escapeHtml(actionLabel(item.action))}</strong>
        <span>${escapeHtml(item.actor_name)} · ${escapeHtml(roleLabel(item.actor_role))}</span>
        <p>${escapeHtml(caseLabel(item.before_status) || nodeLabel(item.before_status))} → ${escapeHtml(caseLabel(item.after_status) || nodeLabel(item.after_status))}${item.note ? ` · ${escapeHtml(item.note)}` : ""}</p>
      </div>`;
  }

  function renderCase() {
    if (!activeCase) return;
    const context = activeCase.context || {};
    const detail = document.getElementById("swDetail");
    detail.innerHTML = `
      <section class="sw-card">
        <div class="sw-heading">
          <div>
            <span class="track">${escapeHtml(activeCase.case_number)}</span>
            <h3>${escapeHtml(activeCase.title)}</h3>
            <p>${escapeHtml(activeCase.objective)}</p>
          </div>
          <div class="sw-actions">${caseActions()}</div>
        </div>
        <div class="sw-metrics">
          <span>状态<strong>${escapeHtml(caseLabel(activeCase.status))}</strong></span>
          <span>负责人<strong>${escapeHtml(activeCase.owner_name)}</strong></span>
          <span>优先级<strong>${escapeHtml(PRIORITY_LABELS[activeCase.priority] || activeCase.priority)}</strong></span>
          <span>进度<strong>${activeCase.completed_nodes}/${activeCase.total_nodes}</strong></span>
        </div>
      </section>
      ${contextSection(context)}
      <section class="sw-card">
        <h4>处理节点</h4>
        <div class="sw-nodes">${(activeCase.nodes || []).map(renderNode).join("")}</div>
      </section>
      <section class="sw-card">
        <h4>操作记录</h4>
        ${events.length ? events.map(eventHtml).join("") : '<p class="sw-empty">暂无记录。</p>'}
      </section>`;
  }

  function caseActions() {
    if (!canEdit()) return "";
    const actions = [];
    if (activeCase.status === "draft") actions.push(["activate", "启动"]);
    if (["active", "pending_review"].includes(activeCase.status)) actions.push(["hold", "暂停"]);
    if (activeCase.status === "on_hold") actions.push(["resume", "恢复"]);
    if (["active", "draft"].includes(activeCase.status) && activeCase.completed_nodes === activeCase.total_nodes) {
      actions.push(["submit_review", "提交结项审核"]);
    }
    if (activeCase.status === "pending_review" && canReview()) actions.push(["complete", "批准结项"]);
    if (!["completed", "cancelled"].includes(activeCase.status) && canReview()) actions.push(["cancel", "取消"]);
    if (["completed", "cancelled"].includes(activeCase.status) && canReview()) actions.push(["reopen", "重新打开"]);
    return actions.map(([action, label]) => `<button class="secondary" data-sw-case="${action}" type="button">${label}</button>`).join("");
  }

  function renderNode(node) {
    const isMine = !node.assignee_user_id || node.assignee_user_id === account().user?.id;
    const editable = canReview() || (canEdit() && isMine);
    return `
      <article class="sw-node sw-node-${escapeHtml(node.status)}">
        <header>
          <div>
            <span>节点 ${node.sequence}</span>
            <h5>${escapeHtml(node.title)}</h5>
            <p>${escapeHtml(node.description)}</p>
          </div>
          <em>${escapeHtml(nodeLabel(node.status))}</em>
        </header>
        <small>责任人：${escapeHtml(node.assignee_name || "未分配")} · 期限：${escapeHtml(node.due_date || "未设置")}</small>
        ${node.output_summary ? `<blockquote>${escapeHtml(node.output_summary)}</blockquote>` : ""}
        ${editable ? `<textarea data-sw-output="${escapeHtml(node.id)}" rows="3" placeholder="节点处理结果">${escapeHtml(node.output_summary || "")}</textarea>` : ""}
        <div class="sw-actions">${nodeActions(node, editable)}</div>
        ${canReview() ? `
          <details>
            <summary>责任人和期限</summary>
            <div class="sw-assign">
              <select data-sw-assignee="${escapeHtml(node.id)}">${memberOptions(node.assignee_user_id)}</select>
              <input data-sw-due="${escapeHtml(node.id)}" type="date" value="${escapeHtml(node.due_date || "")}">
              <button data-sw-assign="${escapeHtml(node.id)}" type="button">保存</button>
            </div>
          </details>` : ""}
      </article>`;
  }

  function nodeActions(node, editable) {
    if (!editable || ["completed", "cancelled"].includes(activeCase.status)) return "";
    const actions = [];
    if (node.status === "pending") actions.push(["start", "开始"]);
    if (node.status === "in_progress") actions.push(["submit", "提交审核"], ["block", "受阻"]);
    if (node.status === "blocked") actions.push(["resume", "恢复"], ["submit", "提交审核"]);
    if (node.status === "pending_review" && canReview()) actions.push(["approve", "批准"], ["return", "退回"]);
    if (!["completed", "skipped"].includes(node.status) && canReview()) actions.push(["skip", "跳过"]);
    if (["completed", "skipped"].includes(node.status) && canReview()) actions.push(["reopen", "重新打开"]);
    return actions.map(([action, label]) => `
      <button class="secondary" data-sw-node="${action}" data-sw-node-id="${escapeHtml(node.id)}" type="button">${label}</button>`).join("");
  }

  async function refreshContext() {
    const citations = recentKnowledgeCitations();
    const knowledgeCitations = citations.length ? citations : existingKnowledgeCitations();
    try {
      activeCase = await request(`/api/service-cases/${activeCase.id}/context/refresh`, {
        method: "POST",
        body: JSON.stringify({
          lock_version: activeCase.lock_version,
          knowledge_citations: knowledgeCitations,
          note: "更新项目、政策与组织知识依据",
        }),
      });
      await loadEvents();
      renderCase();
      listCases();
      notify("办理依据已更新。");
    } catch (error) {
      notify(error.message);
    }
  }

  async function performCaseAction(action) {
    let note = "";
    let acknowledgeOpenItems = false;
    if (["hold", "cancel", "complete"].includes(action)) {
      note = prompt(
        action === "complete" ? "结项总结：" : action === "hold" ? "暂停原因：" : "取消原因：",
      ) || "";
      if (!note) return;
    }
    if (action === "complete" && (activeCase.context?.pending_items || []).length) {
      acknowledgeOpenItems = confirm("仍有待确认事项。确认已在结项总结中处理或转入后续跟踪吗？");
      if (!acknowledgeOpenItems) return;
    }
    try {
      activeCase = await request(`/api/service-cases/${activeCase.id}/actions`, {
        method: "POST",
        body: JSON.stringify({
          action,
          lock_version: activeCase.lock_version,
          note,
          acknowledge_open_items: acknowledgeOpenItems,
        }),
      });
      await loadEvents();
      renderCase();
      listCases();
    } catch (error) {
      notify(error.message);
    }
  }

  async function performNodeAction(id, action) {
    let note = "";
    const outputSummary = document.querySelector(`[data-sw-output="${CSS.escape(id)}"]`)?.value.trim() || "";
    if (["block", "return", "skip"].includes(action)) {
      note = prompt("请填写原因：") || "";
      if (!note) return;
    }
    try {
      activeCase = await request(`/api/service-cases/${activeCase.id}/nodes/${id}/actions`, {
        method: "POST",
        body: JSON.stringify({
          action,
          lock_version: activeCase.lock_version,
          note,
          output_summary: outputSummary,
        }),
      });
      await loadEvents();
      renderCase();
      listCases();
    } catch (error) {
      notify(error.message);
    }
  }

  async function saveAssignment(id) {
    const assignee = document.querySelector(`[data-sw-assignee="${CSS.escape(id)}"]`)?.value || null;
    const dueDate = document.querySelector(`[data-sw-due="${CSS.escape(id)}"]`)?.value || null;
    try {
      activeCase = await request(`/api/service-cases/${activeCase.id}/nodes/${id}`, {
        method: "PUT",
        body: JSON.stringify({
          lock_version: activeCase.lock_version,
          assignee_user_id: assignee,
          due_date: dueDate,
          clear_due_date: !dueDate,
          description: null,
        }),
      });
      await loadEvents();
      renderCase();
      listCases();
    } catch (error) {
      notify(error.message);
    }
  }

  async function loadEvents() {
    if (!activeCase?.id) {
      events = [];
      return;
    }
    try {
      events = (await request(`/api/service-cases/${activeCase.id}/events`)).items || [];
    } catch (_) {
      events = [];
    }
  }

  function handleClick(event) {
    if (event.target.closest("[data-sw-close]")) { closeWorkflow(); return; }
    if (event.target.closest("[data-sw-create]")) { createCase(); return; }
    const caseItem = event.target.closest("[data-sw-id]");
    if (caseItem) { loadCase(caseItem.dataset.swId); return; }
    const caseAction = event.target.closest("[data-sw-case]");
    if (caseAction) { performCaseAction(caseAction.dataset.swCase); return; }
    const nodeAction = event.target.closest("[data-sw-node]");
    if (nodeAction) { performNodeAction(nodeAction.dataset.swNodeId, nodeAction.dataset.swNode); return; }
    const assignment = event.target.closest("[data-sw-assign]");
    if (assignment) { saveAssignment(assignment.dataset.swAssign); return; }
    if (event.target.closest("[data-sw-context]")) refreshContext();
  }

  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && document.getElementById("serviceWorkflowModal")?.classList.contains("show")) {
      closeWorkflow();
    }
  });

  injectUi();
  updateVisibility();
  document.addEventListener(ACCOUNT_READY_EVENT, updateVisibility);
  setTimeout(updateVisibility, 500);

  window.ZHILINK_SERVICE_WORKFLOW = {
    open: openWorkflow,
    reload: listCases,
    getCurrent: () => activeCase,
  };
  window.ZHILINK_SERVICE_WORKFLOW_READY = true;
})();
