/* Organization-scoped Tianhe enterprise-service knowledge base. */
(() => {
  const READY_EVENT = "zhilink:account-ready";
  const REQUEST_TIMEOUT_MS = 20000;
  let current = null;
  let currentSearch = null;
  let includeArchived = false;

  function safe(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  }
  function notify(message) { if (typeof toast === "function") toast(message); else console.info(message); }
  function account() { return window.ZHILINK_ACCOUNT?.getSession?.() || { authenticated: false, organizations: [], csrf_token: "" }; }
  function organization() { return window.ZHILINK_ACCOUNT?.getActiveOrganization?.() || null; }
  function role() { return organization()?.role || ""; }
  function canEdit() { return ["owner", "admin", "editor"].includes(role()); }
  function canReview() { return ["owner", "admin"].includes(role()); }
  function splitValues(value) { return String(value || "").split(/[，,\n]/).map(item => item.trim()).filter(Boolean).slice(0, 20); }
  function joinValues(value) { return Array.isArray(value) ? value.join("，") : ""; }

  function headers(write = false) {
    const org = organization();
    const session = account();
    if (!session.authenticated || !org) throw new Error("请先登录并选择组织空间。");
    const result = { "X-Organization-Id": org.id };
    if (write) {
      result["Content-Type"] = "application/json";
      result["X-CSRF-Token"] = session.csrf_token || "";
    }
    return result;
  }

  async function request(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(path, {
        ...options,
        headers: { ...headers(Boolean(options.body)), ...(options.headers || {}) },
        credentials: "same-origin",
        signal: controller.signal,
      });
      const text = await response.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!response.ok) {
        const error = new Error(data.detail || text || "知识库操作失败。");
        error.code = data.code || "KNOWLEDGE_REQUEST_FAILED";
        throw error;
      }
      return data;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("知识库请求超时，请稍后重试。");
      throw error;
    } finally { clearTimeout(timer); }
  }

  function injectUi() {
    const topActions = document.querySelector(".top-actions");
    if (topActions && !document.getElementById("openKnowledgeBase")) {
      const button = document.createElement("button");
      button.id = "openKnowledgeBase";
      button.type = "button";
      button.className = "secondary knowledge-base-button";
      button.textContent = "知识库";
      button.hidden = true;
      button.addEventListener("click", openModal);
      const report = topActions.querySelector('[data-goto="report"]');
      topActions.insertBefore(button, report || topActions.firstChild);
    }
    if (document.getElementById("knowledgeBaseModal")) return;
    const modal = document.createElement("div");
    modal.id = "knowledgeBaseModal";
    modal.className = "knowledge-modal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div class="knowledge-backdrop" data-close-knowledge></div>
      <section class="knowledge-dialog" role="dialog" aria-modal="true" aria-labelledby="knowledgeBaseTitle">
        <header class="knowledge-dialog-header">
          <div><span class="track">天河企业服务知识库</span><h2 id="knowledgeBaseTitle">来源、版本、适用范围与审核</h2><p>只有组织已批准的发布版本会进入检索结果。内部材料不得伪装成官方政策。</p></div>
          <button class="icon-btn" type="button" data-close-knowledge aria-label="关闭知识库">✕</button>
        </header>
        <div class="knowledge-toolbar">
          <div class="knowledge-search">
            <input id="knowledgeSearchQuery" maxlength="4000" placeholder="搜索服务指南、办事流程、案例、模板或常见问题" />
            <input id="knowledgeSearchCategory" maxlength="100" placeholder="分类（可选）" />
            <button id="runKnowledgeSearch" class="primary" type="button">检索已发布知识</button>
          </div>
          <div class="knowledge-toolbar-actions">
            <button id="newKnowledgeArticle" class="secondary" type="button">新建草稿</button>
            <label><input id="includeArchivedKnowledge" type="checkbox" />显示已归档</label>
            <button id="refreshKnowledgeList" class="ghost" type="button">刷新</button>
          </div>
        </div>
        <div id="knowledgeSearchResult" class="knowledge-search-result"></div>
        <div class="knowledge-layout">
          <aside><div class="knowledge-list-heading"><strong>组织知识条目</strong><span id="knowledgeListCount"></span></div><div id="knowledgeArticleList" class="knowledge-list"></div></aside>
          <main id="knowledgeEditor" class="knowledge-editor"><div class="knowledge-empty">选择一个知识条目，或新建草稿。</div></main>
        </div>
      </section>`;
    document.body.appendChild(modal);
    modal.addEventListener("click", handleClick);
    document.getElementById("runKnowledgeSearch").addEventListener("click", runSearch);
    document.getElementById("newKnowledgeArticle").addEventListener("click", newArticle);
    document.getElementById("refreshKnowledgeList").addEventListener("click", loadList);
    document.getElementById("includeArchivedKnowledge").addEventListener("change", event => { includeArchived = event.currentTarget.checked; loadList(); });
  }

  function updateAvailability() {
    const button = document.getElementById("openKnowledgeBase");
    if (!button) return;
    const org = organization();
    button.hidden = !org;
    button.title = org ? `${org.name} · ${org.role} · 打开组织知识库` : "登录并选择组织后使用知识库";
    const create = document.getElementById("newKnowledgeArticle");
    if (create) create.hidden = !canEdit();
  }
  function openModal() {
    if (!organization()) { notify("请先登录并选择组织空间。"); return; }
    const modal = document.getElementById("knowledgeBaseModal");
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    updateAvailability();
    loadList();
    setTimeout(() => document.getElementById("knowledgeSearchQuery")?.focus(), 30);
  }
  function closeModal() { const modal = document.getElementById("knowledgeBaseModal"); modal.classList.remove("show"); modal.setAttribute("aria-hidden", "true"); }
  function statusLabel(item) {
    if (item.lifecycle_status === "archived") return "已归档";
    return { draft: "草稿", in_review: "待审核", approved: "已批准", rejected: "已退回" }[item.review_status] || item.review_status;
  }

  async function loadList() {
    const list = document.getElementById("knowledgeArticleList");
    list.innerHTML = '<p class="knowledge-empty">正在读取...</p>';
    try {
      const data = await request(`/api/knowledge?limit=100&include_archived=${includeArchived ? "true" : "false"}`);
      document.getElementById("knowledgeListCount").textContent = `${data.total || 0} 条`;
      if (!data.items?.length) { list.innerHTML = '<p class="knowledge-empty">当前组织还没有可见的知识条目。</p>'; return; }
      list.innerHTML = data.items.map(item => `
        <button class="knowledge-list-item ${current?.id === item.id ? "active" : ""}" type="button" data-knowledge-id="${safe(item.id)}">
          <span><strong>${safe(item.title)}</strong><small>${safe(item.citation_code)} · v${item.current_version}${item.published_version ? ` · 发布 v${item.published_version}` : ""}</small></span>
          <em class="knowledge-status knowledge-status-${safe(item.review_status)}">${safe(statusLabel(item))}</em>
        </button>`).join("");
    } catch (error) { list.innerHTML = `<p class="knowledge-error">${safe(error.message || String(error))}</p>`; }
  }

  async function loadArticle(id) {
    const editor = document.getElementById("knowledgeEditor");
    editor.innerHTML = '<p class="knowledge-empty">正在读取条目...</p>';
    try {
      current = await request(`/api/knowledge/${encodeURIComponent(id)}`);
      renderEditor();
      await Promise.all([loadVersions(), loadEvents()]);
      loadList();
    } catch (error) { editor.innerHTML = `<p class="knowledge-error">${safe(error.message || String(error))}</p>`; }
  }

  function sourceOptions(selected) {
    return [["official","政府官方来源"],["internal","组织内部资料"],["service_guide","企业服务指南"],["case","服务案例"],["template","材料模板"],["faq","常见问题"],["other","其他参考"]]
      .map(([value,label]) => `<option value="${value}" ${selected === value ? "selected" : ""}>${label}</option>`).join("");
  }

  function renderEditor() {
    const editor = document.getElementById("knowledgeEditor");
    const item = current;
    if (!item) { editor.innerHTML = '<div class="knowledge-empty">选择一个知识条目，或新建草稿。</div>'; return; }
    const version = item.version || {};
    const app = version.applicability || {};
    const source = version.source || {};
    const editable = Boolean(item.can_edit);
    const disabled = editable ? "" : "disabled";
    editor.innerHTML = `
      <div class="knowledge-editor-heading">
        <div><span class="track">${safe(item.citation_code)} · 当前 v${item.current_version}${item.published_version ? ` · 已发布 v${item.published_version}` : ""}</span><h3>${safe(version.title || "新建知识条目")}</h3><p>状态：${safe(statusLabel(item))}。编辑已发布条目会创建新草稿，旧发布版本继续可检索，直到新版本审核通过。</p></div>
        <div class="knowledge-action-strip">
          ${editable ? '<button class="primary" type="button" data-save-knowledge>保存新版本</button>' : ""}
          ${editable && ["draft","rejected"].includes(item.review_status) ? '<button class="secondary" type="button" data-knowledge-action="submit">提交审核</button>' : ""}
          ${item.can_review && item.review_status === "in_review" ? '<button class="primary" type="button" data-knowledge-action="approve">批准发布</button><button class="secondary" type="button" data-knowledge-action="reject">退回修改</button>' : ""}
          ${item.can_review && item.lifecycle_status === "active" ? '<button class="ghost" type="button" data-knowledge-action="archive">归档</button>' : ""}
          ${item.can_review && item.lifecycle_status === "archived" ? '<button class="secondary" type="button" data-knowledge-action="unarchive">恢复归档</button>' : ""}
        </div>
      </div>
      <div class="knowledge-form-grid">
        <label>标题<input id="kbTitle" maxlength="300" value="${safe(version.title || "")}" ${disabled}></label>
        <label>分类<input id="kbCategory" maxlength="100" value="${safe(version.category || "")}" ${disabled}></label>
        <label class="wide">摘要<textarea id="kbSummary" maxlength="2000" rows="3" ${disabled}>${safe(version.summary || "")}</textarea></label>
        <label class="wide">正文（Markdown）<textarea id="kbContent" maxlength="50000" rows="12" ${disabled}>${safe(version.content || "")}</textarea></label>
        <label>标签<input id="kbTags" value="${safe(joinValues(version.tags))}" placeholder="用逗号分隔" ${disabled}></label>
        <label>适用区域<input id="kbRegions" value="${safe(joinValues(app.regions))}" placeholder="天河区，广州市" ${disabled}></label>
        <label>适用行业<input id="kbIndustries" value="${safe(joinValues(app.industries))}" ${disabled}></label>
        <label>主体类型<input id="kbEntityTypes" value="${safe(joinValues(app.entity_types))}" placeholder="企业，个体工商户" ${disabled}></label>
        <label>服务场景<input id="kbScenarios" value="${safe(joinValues(app.scenarios))}" ${disabled}></label>
        <label>适用角色<input id="kbRoles" value="${safe(joinValues(app.roles))}" ${disabled}></label>
        <label>生效日期<input id="kbValidFrom" type="date" value="${safe(version.valid_from || "")}" ${disabled}></label>
        <label>失效日期<input id="kbValidUntil" type="date" value="${safe(version.valid_until || "")}" ${disabled}></label>
        <label>来源类型<select id="kbSourceType" ${disabled}>${sourceOptions(source.source_type || "service_guide")}</select></label>
        <label>来源标题<input id="kbSourceTitle" maxlength="500" value="${safe(source.title || "")}" ${disabled}></label>
        <label>发布机构/维护方<input id="kbSourceIssuer" maxlength="500" value="${safe(source.issuer || "")}" ${disabled}></label>
        <label>文号/参考编号<input id="kbReferenceNumber" maxlength="200" value="${safe(source.reference_number || "")}" ${disabled}></label>
        <label class="wide">来源原文摘录<textarea id="kbSourceExcerpt" maxlength="2000" rows="3" placeholder="保存可核对的原文片段；官方来源必填" ${disabled}>${safe(source.excerpt || "")}</textarea></label>
        <label class="wide">来源链接（HTTPS）<input id="kbSourceUrl" maxlength="2000" value="${safe(source.url || "")}" ${disabled}></label>
        <label>来源发布日期<input id="kbSourcePublishedAt" type="date" value="${safe(source.published_at || "")}" ${disabled}></label>
        <label>版本说明<input id="kbChangeNote" maxlength="500" placeholder="说明本次变化" ${disabled}></label>
      </div>
      <section class="knowledge-history"><div><h4>版本历史</h4><span>历史版本不可改写；恢复会生成新的草稿版本。</span></div><div id="knowledgeVersionList"></div></section>
      <section class="knowledge-history"><div><h4>审核记录</h4><span>记录提交、批准、退回、归档和恢复操作。</span></div><div id="knowledgeEventList"></div></section>`;
  }

  function collectForm() {
    return {
      title: document.getElementById("kbTitle").value.trim(), category: document.getElementById("kbCategory").value.trim(), summary: document.getElementById("kbSummary").value.trim(), content: document.getElementById("kbContent").value.trim(),
      tags: splitValues(document.getElementById("kbTags").value),
      applicability: { regions: splitValues(document.getElementById("kbRegions").value), industries: splitValues(document.getElementById("kbIndustries").value), entity_types: splitValues(document.getElementById("kbEntityTypes").value), scenarios: splitValues(document.getElementById("kbScenarios").value), roles: splitValues(document.getElementById("kbRoles").value) },
      source: { source_type: document.getElementById("kbSourceType").value, title: document.getElementById("kbSourceTitle").value.trim(), issuer: document.getElementById("kbSourceIssuer").value.trim(), url: document.getElementById("kbSourceUrl").value.trim(), published_at: document.getElementById("kbSourcePublishedAt").value || null, reference_number: document.getElementById("kbReferenceNumber").value.trim(), excerpt: document.getElementById("kbSourceExcerpt").value.trim() },
      valid_from: document.getElementById("kbValidFrom").value || null, valid_until: document.getElementById("kbValidUntil").value || null, change_note: document.getElementById("kbChangeNote").value.trim(),
    };
  }

  function newArticle() {
    if (!canEdit()) { notify("当前角色只能查看已发布知识。"); return; }
    current = { id:"", citation_code:"待创建", review_status:"draft", lifecycle_status:"active", current_version:1, published_version:null, can_edit:true, can_review:canReview(), version:{ title:"", category:"企业服务指南", summary:"", content:"", tags:[], applicability:{regions:["天河区"],industries:[],entity_types:[],scenarios:[],roles:[]}, source:{source_type:"service_guide",title:"",issuer:organization()?.name || "",url:"",published_at:null,reference_number:"",excerpt:""}, valid_from:null, valid_until:null } };
    renderEditor();
  }

  async function saveArticle() {
    const body = collectForm();
    try {
      if (current.id) {
        body.expected_version = current.current_version;
        current = await request(`/api/knowledge/${encodeURIComponent(current.id)}`, { method:"PUT", body:JSON.stringify(body) });
        notify(`已保存为 v${current.current_version} 草稿。`);
      } else {
        current = await request("/api/knowledge", { method:"POST", body:JSON.stringify(body) });
        notify("知识条目草稿已创建。");
      }
      renderEditor();
      await Promise.all([loadList(), loadVersions(), loadEvents()]);
    } catch (error) { notify(error.message || String(error)); }
  }

  async function runAction(action, versionNumber = null) {
    if (!current?.id) return;
    let note = "";
    if (["reject","archive"].includes(action)) { note = prompt(action === "reject" ? "请填写退回原因：" : "请填写归档原因：") || ""; if (!note.trim()) return; }
    else if (action === "restore") note = prompt(`将 v${versionNumber} 恢复为新的草稿版本。可填写恢复说明：`) || `恢复自 v${versionNumber}`;
    else if (action === "approve") note = prompt("可填写批准说明（可选）：") || "";
    try {
      current = await request(`/api/knowledge/${encodeURIComponent(current.id)}/actions`, { method:"POST", body:JSON.stringify({action,expected_version:current.current_version,note,version_number:versionNumber}) });
      notify({submit:"已提交审核。",approve:"已批准并发布当前版本。",reject:"已退回修改。",archive:"已归档。",unarchive:"已恢复归档。",restore:"历史版本已恢复为新草稿。"}[action] || "操作完成。");
      renderEditor();
      await Promise.all([loadList(), loadVersions(), loadEvents()]);
    } catch (error) { notify(error.message || String(error)); }
  }

  async function loadVersions() {
    if (!current?.id) return;
    const container = document.getElementById("knowledgeVersionList");
    if (!container) return;
    try {
      const data = await request(`/api/knowledge/${encodeURIComponent(current.id)}/versions`);
      container.innerHTML = data.items?.length ? data.items.map(version => `<article class="knowledge-version-item"><div><strong>${safe(version.citation_id)}</strong><span>${safe(version.created_at ? new Date(version.created_at).toLocaleString() : "")}</span></div><p>${safe(version.change_note || "未填写版本说明")} · SHA-256 ${safe(version.content_sha256.slice(0,12))}…</p>${current.can_edit && version.version_number !== current.current_version ? `<button class="ghost small" type="button" data-restore-knowledge="${version.version_number}">恢复为新草稿</button>` : ""}</article>`).join("") : '<p class="knowledge-empty">暂无版本记录。</p>';
    } catch (error) { container.innerHTML = `<p class="knowledge-error">${safe(error.message || String(error))}</p>`; }
  }

  async function loadEvents() {
    if (!current?.id) return;
    const container = document.getElementById("knowledgeEventList");
    if (!container) return;
    try {
      const data = await request(`/api/knowledge/${encodeURIComponent(current.id)}/events`);
      container.innerHTML = data.items?.length ? data.items.map(event => `<article class="knowledge-event-item"><div><strong>${safe(event.action)} · v${event.version_number}</strong><span>${safe(event.actor_name)} · ${safe(event.actor_role)}</span></div><p>${safe(event.before_status)} → ${safe(event.after_status)}${event.note ? ` · ${safe(event.note)}` : ""}</p></article>`).join("") : '<p class="knowledge-empty">暂无审核记录。</p>';
    } catch (error) { container.innerHTML = `<p class="knowledge-error">${safe(error.message || String(error))}</p>`; }
  }

  async function runSearch() {
    const container = document.getElementById("knowledgeSearchResult");
    const query = document.getElementById("knowledgeSearchQuery").value.trim();
    const category = document.getElementById("knowledgeSearchCategory").value.trim();
    container.innerHTML = '<p class="knowledge-empty">正在检索已批准版本...</p>';
    try {
      const profile = { industry:state?.profile?.industry || "", location:state?.profile?.location || "", scale:state?.profile?.scale || "", stage:state?.profile?.stage || "", demands:state?.profile?.demands || "" };
      currentSearch = await request("/api/knowledge/search", { method:"POST", body:JSON.stringify({query,category,profile,limit:12}) });
      renderSearch();
    } catch (error) { container.innerHTML = `<p class="knowledge-error">${safe(error.message || String(error))}</p>`; }
  }

  function renderSearch() {
    const container = document.getElementById("knowledgeSearchResult");
    if (!currentSearch?.items?.length) { container.innerHTML = '<div class="knowledge-search-empty"><strong>未检索到可用的已发布知识</strong><p>草稿、待审核、已退回、已归档、未生效或已失效条目不会进入检索结果。</p></div>'; return; }
    container.innerHTML = `<div class="knowledge-search-heading"><div><strong>检索到 ${currentSearch.items.length} 条已发布知识</strong><span>引用必须保留具体版本号。</span></div><button class="secondary small" type="button" data-copy-knowledge-context>复制 AI 引用上下文</button></div><div class="knowledge-search-items">${currentSearch.items.map(item => `<article><header><strong>${safe(item.citation_id)}</strong><span>${safe(item.category)} · 相关度 ${safe(item.score)}</span></header><h4>${safe(item.title)}</h4><p>${safe(item.excerpt)}</p><small>来源：${safe(item.source.source_type)} · ${safe(item.source.issuer || item.source.title)}${item.valid_until ? ` · 有效至 ${safe(item.valid_until)}` : " · 未限定失效日期"}</small>${(item.warnings || []).length ? `<ul>${item.warnings.map(value => `<li>${safe(value)}</li>`).join("")}</ul>` : ""}<button class="ghost small" type="button" data-knowledge-id="${safe(item.article_id)}">查看条目</button></article>`).join("")}</div>`;
  }

  async function copyContext() {
    if (!currentSearch?.markdown_context) return;
    if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(currentSearch.markdown_context);
    else if (typeof copyText === "function") await copyText(currentSearch.markdown_context);
    else throw new Error("当前浏览器不支持复制。");
    notify("已复制带版本号的知识库引用上下文。");
  }

  function handleClick(event) {
    if (event.target.closest("[data-close-knowledge]")) return closeModal();
    const article = event.target.closest("[data-knowledge-id]");
    if (article) return loadArticle(article.dataset.knowledgeId);
    if (event.target.closest("[data-save-knowledge]")) return saveArticle();
    const action = event.target.closest("[data-knowledge-action]");
    if (action) return runAction(action.dataset.knowledgeAction);
    const restore = event.target.closest("[data-restore-knowledge]");
    if (restore) return runAction("restore", Number(restore.dataset.restoreKnowledge));
    if (event.target.closest("[data-copy-knowledge-context]")) copyContext().catch(error => notify(error.message || String(error)));
  }

  document.addEventListener("keydown", event => { if (event.key === "Escape" && document.getElementById("knowledgeBaseModal")?.classList.contains("show")) closeModal(); });
  injectUi();
  updateAvailability();
  document.addEventListener(READY_EVENT, updateAvailability);
  setTimeout(updateAvailability, 500);
  window.ZHILINK_KNOWLEDGE = { search: async (query, profile={}) => request("/api/knowledge/search", {method:"POST",body:JSON.stringify({query:query || "",profile,category:"",limit:8})}), getLastSearch:()=>currentSearch, open:openModal };
  window.ZHILINK_KNOWLEDGE_READY = true;
})();
