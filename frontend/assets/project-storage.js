/* Persistent project workspaces and immutable version history. */
(() => {
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  if (!contracts) throw new Error("Workspace contracts must load before project storage.");

  const WORKSPACE_KEY_STORAGE = contracts.storage.workspaceKey;
  const CURRENT_PROJECT_STORAGE = contracts.storage.currentProject;
  const RESTORE_SECTION_STORAGE = contracts.storage.restoreSection;
  const PROJECT_TIMEOUT_MS = 20000;
  const PERSISTED_META_FIELDS = ["origin", "example_key", "result_schema_version"];
  const MODULE_LABELS = {
    project: "项目信息",
    identity: "使用身份",
    ...contracts.resultTitles,
  };
  const FORM_LABELS = {
    profileName: "企业名称",
    profileIndustry: "所属行业",
    profileLocation: "所在场景",
    profileScale: "团队规模",
    profileStage: "发展阶段",
    profileRole: "使用角色",
    profileDemands: "当前需求",
    meetingInput: "会议原文",
    contractInput: "合同原文",
    policyDemand: "政策需求",
    offerInput: "可提供资源",
    needInput: "业务需求",
    targetInput: "目标对象",
    scenarioInput: "合作场景",
    pilotScene: "试点场景",
    userRoles: "使用角色",
    dataScope: "数据范围",
    deployment: "部署方式",
    pilotPeriod: "试点周期",
    reviewMode: "复核机制",
  };

  let currentProject = readJson(localStorage.getItem(CURRENT_PROJECT_STORAGE), null);
  let projectDirty = false;
  let includeArchived = false;
  let historyVisible = false;

  function readJson(raw, fallback) {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  }

  function createWorkspaceKey() {
    if (!window.crypto || !window.crypto.getRandomValues) {
      throw new Error("当前浏览器不支持安全随机数，无法启用项目存储。");
    }
    const bytes = new Uint8Array(32);
    window.crypto.getRandomValues(bytes);
    return Array.from(bytes, value => value.toString(16).padStart(2, "0")).join("");
  }

  function workspaceKey() {
    let key = localStorage.getItem(WORKSPACE_KEY_STORAGE) || "";
    if (key.length < 32) {
      key = createWorkspaceKey();
      localStorage.setItem(WORKSPACE_KEY_STORAGE, key);
    }
    return key;
  }

  function projectHeaders(hasBody = false) {
    const headers = { "X-Workspace-Key": workspaceKey() };
    if (hasBody) headers["Content-Type"] = "application/json";
    return headers;
  }

  async function projectRequest(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), PROJECT_TIMEOUT_MS);
    const method = options.method || "GET";
    try {
      const response = await fetch(path, {
        ...options,
        method,
        headers: { ...projectHeaders(Boolean(options.body)), ...(options.headers || {}) },
        signal: controller.signal,
      });
      const text = await response.text();
      const data = readJson(text, {});
      if (!response.ok) {
        const error = new Error(data.detail || text || "项目操作失败。");
        error.code = data.code || "PROJECT_REQUEST_FAILED";
        error.currentVersion = data.current_version;
        throw error;
      }
      return data;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("项目存储请求超时，请稍后重试。");
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  function cleanMeta(meta) {
    const result = {};
    Object.entries(meta || {}).slice(0, 12).forEach(([key, value]) => {
      const cleaned = {
        mode: String(value?.mode || "").slice(0, 200),
        error: String(value?.error || "").slice(0, 1000),
        time: String(value?.time || "").slice(0, 100),
      };
      PERSISTED_META_FIELDS.forEach(field => {
        const current = value?.[field];
        if (typeof current === "string" && current) cleaned[field] = current.slice(0, 200);
      });
      result[key] = cleaned;
    });
    return result;
  }

  function collectProjectSnapshot() {
    saveProfileToState();
    saveFormState();
    const forms = {};
    formInputIds.forEach(id => {
      const element = $(id);
      if (element) forms[id] = element.value || "";
    });
    return {
      identity: {
        org: String(state.identity?.org || ""),
        role: String(state.identity?.role || ""),
        contact: String(state.identity?.contact || ""),
      },
      profile: { ...(state.profile || {}) },
      forms,
      results: { ...(state.results || {}) },
      meta: cleanMeta(state.meta),
      current_section: document.querySelector(".page.active-page")?.id || "home",
    };
  }

  function applyProjectSnapshot(project) {
    const snapshot = project.snapshot || {};
    localStorage.setItem(contracts.storage.identity, JSON.stringify(snapshot.identity || {}));
    sessionStorage.setItem(contracts.storage.profile, JSON.stringify(snapshot.profile || {}));
    sessionStorage.setItem(contracts.storage.formInputs, JSON.stringify(snapshot.forms || {}));
    sessionStorage.setItem(contracts.storage.results, JSON.stringify(snapshot.results || {}));
    sessionStorage.setItem(contracts.storage.meta, JSON.stringify(snapshot.meta || {}));
    localStorage.setItem(RESTORE_SECTION_STORAGE, snapshot.current_section || "home");
    setCurrentProject(project, false);
    location.reload();
  }

  function setCurrentProject(project, dirty = false) {
    currentProject = project ? {
      id: project.id,
      name: project.name,
      description: project.description || "",
      status: project.status || "active",
      lock_version: project.lock_version,
      updated_at: project.updated_at || "",
    } : null;
    projectDirty = Boolean(dirty);
    if (currentProject) {
      localStorage.setItem(CURRENT_PROJECT_STORAGE, JSON.stringify(currentProject));
    } else {
      localStorage.removeItem(CURRENT_PROJECT_STORAGE);
    }
    renderProjectStatus();
  }

  function markProjectDirty() {
    if (!currentProject || projectDirty) return;
    projectDirty = true;
    renderProjectStatus();
  }

  function renderProjectStatus() {
    const button = document.getElementById("openProjectManager");
    if (!button) return;
    if (!currentProject) {
      button.textContent = "项目";
      button.title = "创建或打开持久化项目";
      button.classList.remove("project-dirty");
      return;
    }
    button.textContent = `${currentProject.name}${projectDirty ? " · 未保存" : ` · v${currentProject.lock_version}`}`;
    button.title = projectDirty ? "当前项目有未保存更改" : `当前项目版本 v${currentProject.lock_version}`;
    button.classList.toggle("project-dirty", projectDirty);
  }

  function injectStylesheets() {
    if (!document.querySelector("link[data-project-storage]")) {
      const stylesheet = document.createElement("link");
      stylesheet.rel = "stylesheet";
      stylesheet.href = "/assets/project-storage.css";
      stylesheet.dataset.projectStorage = "true";
      document.head.appendChild(stylesheet);
    }
    if (!document.querySelector("link[data-project-history]")) {
      const stylesheet = document.createElement("link");
      stylesheet.rel = "stylesheet";
      stylesheet.href = "/assets/project-history.css";
      stylesheet.dataset.projectHistory = "true";
      document.head.appendChild(stylesheet);
    }
  }

  function injectProjectUI() {
    injectStylesheets();
    const topActions = document.querySelector(".top-actions");
    if (topActions && !document.getElementById("openProjectManager")) {
      const button = document.createElement("button");
      button.id = "openProjectManager";
      button.type = "button";
      button.className = "secondary project-manager-button";
      button.addEventListener("click", openProjectManager);
      const reportButton = topActions.querySelector('[data-goto="report"]');
      topActions.insertBefore(button, reportButton || topActions.firstChild);
    }

    if (!document.getElementById("projectManagerModal")) {
      const modal = document.createElement("div");
      modal.id = "projectManagerModal";
      modal.className = "project-modal";
      modal.setAttribute("aria-hidden", "true");
      modal.innerHTML = `
        <div class="project-modal-backdrop" data-close-project-manager></div>
        <section class="project-dialog" role="dialog" aria-modal="true" aria-labelledby="projectManagerTitle">
          <div class="project-dialog-header">
            <div>
              <span class="track">项目存储</span>
              <h2 id="projectManagerTitle">项目、材料与版本历史</h2>
              <p>只有显式保存才写入数据库。模型 API Key 与接口配置不会写入项目或历史版本。</p>
            </div>
            <button class="icon-btn" type="button" data-close-project-manager aria-label="关闭项目管理">✕</button>
          </div>
          <div class="project-current-card" id="projectCurrentCard"></div>
          <div class="project-editor">
            <label>项目名称<input id="projectNameInput" maxlength="120" placeholder="例如：天河商圈活动筹备" /></label>
            <label>项目说明<textarea id="projectDescriptionInput" maxlength="2000" rows="3" placeholder="说明项目目标、服务对象或当前阶段"></textarea></label>
            <label>版本说明（可选）<input id="projectVersionLabelInput" maxlength="200" placeholder="例如：补充法务意见和会议责任人" /></label>
            <div class="project-action-row">
              <button id="createProjectButton" class="primary" type="button">新建并保存</button>
              <button id="saveProjectButton" class="secondary" type="button">保存当前项目</button>
              <button id="archiveProjectButton" class="ghost" type="button">归档当前项目</button>
              <button id="showProjectHistoryButton" class="ghost" type="button">版本历史</button>
            </div>
          </div>
          <section id="projectHistorySection" class="project-history-section" hidden>
            <div class="project-list-header">
              <div><h3>版本历史</h3><p>每次有效保存生成不可变版本；恢复旧版会产生一个新版本。</p></div>
              <button id="refreshProjectHistoryButton" class="secondary small" type="button">刷新</button>
            </div>
            <div id="projectHistoryList" class="project-history-list"></div>
            <div id="projectHistoryDetail" class="project-history-detail"></div>
          </section>
          <div class="project-list-header">
            <div><h3>我的项目</h3><p>项目按当前浏览器工作区隔离。</p></div>
            <label class="project-archive-toggle"><input id="includeArchivedProjects" type="checkbox" />显示已归档</label>
          </div>
          <div id="projectList" class="project-list"><p class="project-empty">正在读取项目...</p></div>
          <div class="project-privacy-note">
            浏览器工作区密钥只保存在本机，服务端仅保存其哈希。清除浏览器网站数据后，将无法继续访问此前的匿名项目；账号迁移将在后续阶段实现。
          </div>
        </section>`;
      document.body.appendChild(modal);
      modal.addEventListener("click", handleProjectModalClick);
      document.getElementById("createProjectButton").addEventListener("click", createProject);
      document.getElementById("saveProjectButton").addEventListener("click", saveCurrentProject);
      document.getElementById("archiveProjectButton").addEventListener("click", archiveCurrentProject);
      document.getElementById("showProjectHistoryButton").addEventListener("click", toggleProjectHistory);
      document.getElementById("refreshProjectHistoryButton").addEventListener("click", loadProjectHistory);
      document.getElementById("includeArchivedProjects").addEventListener("change", event => {
        includeArchived = event.currentTarget.checked;
        loadProjectList();
      });
    }
    renderProjectStatus();
  }

  function handleProjectModalClick(event) {
    if (event.target.closest("[data-close-project-manager]")) {
      closeProjectManager();
      return;
    }
    const loadButton = event.target.closest("[data-load-project]");
    if (loadButton) loadProject(loadButton.dataset.loadProject);
    const deleteButton = event.target.closest("[data-delete-project]");
    if (deleteButton) deleteProject(deleteButton.dataset.deleteProject, deleteButton.dataset.projectName || "该项目");
    const viewVersionButton = event.target.closest("[data-view-project-version]");
    if (viewVersionButton) viewProjectVersion(Number(viewVersionButton.dataset.viewProjectVersion));
    const restoreVersionButton = event.target.closest("[data-restore-project-version]");
    if (restoreVersionButton) restoreProjectVersion(Number(restoreVersionButton.dataset.restoreProjectVersion));
  }

  function openProjectManager() {
    const modal = document.getElementById("projectManagerModal");
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    renderCurrentProjectCard();
    loadProjectList();
    if (historyVisible) loadProjectHistory();
    setTimeout(() => document.getElementById("projectNameInput")?.focus(), 30);
  }

  function closeProjectManager() {
    const modal = document.getElementById("projectManagerModal");
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
  }

  function renderCurrentProjectCard() {
    const card = document.getElementById("projectCurrentCard");
    const nameInput = document.getElementById("projectNameInput");
    const descriptionInput = document.getElementById("projectDescriptionInput");
    const archiveButton = document.getElementById("archiveProjectButton");
    const saveButton = document.getElementById("saveProjectButton");
    const historyButton = document.getElementById("showProjectHistoryButton");
    if (!currentProject) {
      card.innerHTML = "<strong>当前未打开持久化项目</strong><span>可以填写名称后新建，或从下方项目列表载入。</span>";
      nameInput.value = "";
      descriptionInput.value = "";
      archiveButton.disabled = true;
      saveButton.disabled = true;
      historyButton.disabled = true;
      return;
    }
    card.innerHTML = `<strong>${escapeHtml(currentProject.name)} · v${currentProject.lock_version}</strong><span>${currentProject.status === "archived" ? "已归档" : (projectDirty ? "有未保存更改" : "已保存")}</span>`;
    nameInput.value = currentProject.name || "";
    descriptionInput.value = currentProject.description || "";
    archiveButton.disabled = false;
    archiveButton.textContent = currentProject.status === "archived" ? "恢复当前项目" : "归档当前项目";
    saveButton.disabled = false;
    historyButton.disabled = false;
  }

  async function loadProjectList() {
    const list = document.getElementById("projectList");
    list.innerHTML = '<p class="project-empty">正在读取项目...</p>';
    try {
      const data = await projectRequest(`/api/projects?include_archived=${includeArchived ? "true" : "false"}`);
      if (!data.items?.length) {
        list.innerHTML = '<p class="project-empty">当前工作区还没有项目。</p>';
        return;
      }
      list.innerHTML = data.items.map(project => {
        const active = currentProject?.id === project.id;
        const updated = project.updated_at ? new Date(project.updated_at).toLocaleString() : "";
        return `<article class="project-list-item ${active ? "active" : ""}">
          <div><h4>${escapeHtml(project.name)}</h4><p>${escapeHtml(project.description || "暂无说明")}</p><span>${project.status === "archived" ? "已归档" : "进行中"} · v${project.lock_version} · ${escapeHtml(updated)}</span></div>
          <div class="project-list-actions">
            <button class="secondary small" type="button" data-load-project="${escapeHtml(project.id)}">打开</button>
            <button class="danger-light small" type="button" data-delete-project="${escapeHtml(project.id)}" data-project-name="${escapeHtml(project.name)}">删除</button>
          </div>
        </article>`;
      }).join("");
    } catch (error) {
      list.innerHTML = `<p class="project-empty error">${escapeHtml(error.message || String(error))}</p>`;
    }
  }

  function editorValues() {
    return {
      name: document.getElementById("projectNameInput").value.trim(),
      description: document.getElementById("projectDescriptionInput").value.trim(),
      version_label: document.getElementById("projectVersionLabelInput").value.trim(),
    };
  }

  function clearVersionLabel() {
    const input = document.getElementById("projectVersionLabelInput");
    if (input) input.value = "";
  }

  async function createProject() {
    const values = editorValues();
    if (!values.name) {
      toast("请填写项目名称。");
      document.getElementById("projectNameInput").focus();
      return;
    }
    const button = document.getElementById("createProjectButton");
    button.disabled = true;
    button.textContent = "正在保存...";
    try {
      const project = await projectRequest("/api/projects", {
        method: "POST",
        body: JSON.stringify({ ...values, snapshot: collectProjectSnapshot() }),
      });
      setCurrentProject(project, false);
      clearVersionLabel();
      renderCurrentProjectCard();
      await loadProjectList();
      if (historyVisible) await loadProjectHistory();
      toast("项目已创建并保存为 v1。");
    } catch (error) {
      toast(error.message || String(error));
    } finally {
      button.disabled = false;
      button.textContent = "新建并保存";
    }
  }

  async function saveCurrentProject() {
    if (!currentProject) {
      toast("请先新建或打开一个项目。");
      return;
    }
    const values = editorValues();
    if (!values.name) {
      toast("项目名称不能为空。");
      return;
    }
    const button = document.getElementById("saveProjectButton");
    button.disabled = true;
    button.textContent = "正在保存...";
    const previousVersion = currentProject.lock_version;
    try {
      const project = await projectRequest(`/api/projects/${encodeURIComponent(currentProject.id)}`, {
        method: "PUT",
        body: JSON.stringify({
          lock_version: currentProject.lock_version,
          ...values,
          snapshot: collectProjectSnapshot(),
        }),
      });
      setCurrentProject(project, false);
      clearVersionLabel();
      renderCurrentProjectCard();
      await loadProjectList();
      if (historyVisible) await loadProjectHistory();
      toast(project.lock_version === previousVersion ? "当前内容与已保存版本一致。" : `项目已保存为 v${project.lock_version}。`);
    } catch (error) {
      await handleProjectConflict(error);
    } finally {
      button.disabled = false;
      button.textContent = "保存当前项目";
    }
  }

  async function archiveCurrentProject() {
    if (!currentProject) return;
    const nextStatus = currentProject.status === "archived" ? "active" : "archived";
    try {
      const project = await projectRequest(`/api/projects/${encodeURIComponent(currentProject.id)}`, {
        method: "PUT",
        body: JSON.stringify({
          lock_version: currentProject.lock_version,
          status: nextStatus,
        }),
      });
      setCurrentProject(project, projectDirty);
      renderCurrentProjectCard();
      await loadProjectList();
      if (historyVisible) await loadProjectHistory();
      toast(nextStatus === "archived" ? `项目已归档为 v${project.lock_version}。` : `项目已恢复为 v${project.lock_version}。`);
    } catch (error) {
      await handleProjectConflict(error);
    }
  }

  async function handleProjectConflict(error) {
    if (error.code === "PROJECT_VERSION_CONFLICT") {
      toast(`项目已更新到 v${error.currentVersion || "新版本"}，请重新打开后再操作。`);
      await loadProjectList();
      if (historyVisible) await loadProjectHistory();
      return;
    }
    toast(error.message || String(error));
  }

  async function loadProject(projectId) {
    if (projectDirty && !confirm("当前项目有未保存更改，继续打开其他项目将丢失这些更改。是否继续？")) return;
    try {
      const project = await projectRequest(`/api/projects/${encodeURIComponent(projectId)}`);
      applyProjectSnapshot(project);
    } catch (error) {
      toast(error.message || String(error));
    }
  }

  async function deleteProject(projectId, projectName) {
    if (!confirm(`确认永久删除“${projectName}”及其全部版本历史吗？此操作不可恢复。`)) return;
    try {
      await projectRequest(`/api/projects/${encodeURIComponent(projectId)}`, { method: "DELETE" });
      if (currentProject?.id === projectId) setCurrentProject(null, false);
      renderCurrentProjectCard();
      hideHistory();
      await loadProjectList();
      toast("项目及版本历史已删除。");
    } catch (error) {
      toast(error.message || String(error));
    }
  }

  function toggleProjectHistory() {
    if (!currentProject) return;
    historyVisible = !historyVisible;
    const section = document.getElementById("projectHistorySection");
    section.hidden = !historyVisible;
    document.getElementById("showProjectHistoryButton").textContent = historyVisible ? "收起版本历史" : "版本历史";
    if (historyVisible) loadProjectHistory();
  }

  function hideHistory() {
    historyVisible = false;
    const section = document.getElementById("projectHistorySection");
    if (section) section.hidden = true;
    const button = document.getElementById("showProjectHistoryButton");
    if (button) button.textContent = "版本历史";
  }

  function versionKindLabel(kind) {
    return {
      create: "创建",
      baseline: "历史启用基线",
      save: "保存",
      metadata: "项目信息更新",
      archive: "归档",
      unarchive: "恢复归档",
      restore: "历史恢复",
    }[kind] || kind;
  }

  function changedModuleText(modules) {
    return (modules || []).map(key => MODULE_LABELS[key] || key).join("、") || "项目信息";
  }

  async function loadProjectHistory() {
    const list = document.getElementById("projectHistoryList");
    const detail = document.getElementById("projectHistoryDetail");
    if (!currentProject) {
      list.innerHTML = '<p class="project-empty">请先打开一个项目。</p>';
      detail.innerHTML = "";
      return;
    }
    list.innerHTML = '<p class="project-empty">正在读取版本历史...</p>';
    detail.innerHTML = "";
    try {
      const data = await projectRequest(`/api/projects/${encodeURIComponent(currentProject.id)}/versions?limit=100`);
      if (!data.items?.length) {
        list.innerHTML = '<p class="project-empty">该项目还没有版本记录。</p>';
        return;
      }
      list.innerHTML = data.items.map(version => {
        const created = version.created_at ? new Date(version.created_at).toLocaleString() : "";
        const current = version.version_number === currentProject.lock_version;
        const source = version.source_version_number ? ` · 来源 v${version.source_version_number}` : "";
        return `<article class="project-version-item ${current ? "current" : ""}">
          <div class="project-version-number">v${version.version_number}</div>
          <div class="project-version-copy">
            <h4>${escapeHtml(version.label || versionKindLabel(version.change_kind))}${current ? ' <span class="project-version-current">当前</span>' : ""}</h4>
            <p>${escapeHtml(versionKindLabel(version.change_kind))}${escapeHtml(source)} · ${escapeHtml(changedModuleText(version.changed_modules))}</p>
            <span>${escapeHtml(created)}</span>
          </div>
          <div class="project-version-actions">
            <button class="secondary small" type="button" data-view-project-version="${version.version_number}">查看</button>
            <button class="ghost small" type="button" data-restore-project-version="${version.version_number}" ${current ? "disabled" : ""}>恢复材料</button>
          </div>
        </article>`;
      }).join("");
    } catch (error) {
      list.innerHTML = `<p class="project-empty error">${escapeHtml(error.message || String(error))}</p>`;
    }
  }

  function compactText(value, max = 180) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    return text.length > max ? `${text.slice(0, max)}…` : text;
  }

  function renderVersionMaterialSummary(version) {
    const snapshot = version.snapshot || {};
    const rows = [];
    Object.entries(snapshot.profile || {}).forEach(([key, value]) => {
      if (String(value || "").trim()) rows.push(["企业档案", key, value]);
    });
    Object.entries(snapshot.forms || {}).forEach(([key, value]) => {
      if (String(value || "").trim()) rows.push(["表单", FORM_LABELS[key] || key, value]);
    });
    Object.entries(snapshot.results || {}).forEach(([key, value]) => {
      if (String(value || "").trim()) rows.push(["AI 结果", MODULE_LABELS[key] || key, value]);
    });
    if (!rows.length) return '<p class="project-empty">该版本没有非空业务材料。</p>';
    return `<div class="project-version-materials">${rows.map(([type, label, value]) => `
      <article>
        <span>${escapeHtml(type)}</span>
        <strong>${escapeHtml(label)}</strong>
        <p>${escapeHtml(compactText(value))}</p>
        <small>${String(value || "").length.toLocaleString()} 字符</small>
      </article>`).join("")}</div>`;
  }

  async function viewProjectVersion(versionNumber) {
    if (!currentProject) return;
    const detail = document.getElementById("projectHistoryDetail");
    detail.innerHTML = '<p class="project-empty">正在读取版本详情...</p>';
    try {
      const version = await projectRequest(`/api/projects/${encodeURIComponent(currentProject.id)}/versions/${versionNumber}`);
      const created = version.created_at ? new Date(version.created_at).toLocaleString() : "";
      detail.innerHTML = `
        <div class="project-version-detail-head">
          <div>
            <span class="track">版本详情</span>
            <h3>v${version.version_number} · ${escapeHtml(version.label || versionKindLabel(version.change_kind))}</h3>
            <p>${escapeHtml(created)} · 变更：${escapeHtml(changedModuleText(version.changed_modules))}</p>
          </div>
          <button class="ghost small" type="button" data-restore-project-version="${version.version_number}" ${version.version_number === currentProject.lock_version ? "disabled" : ""}>恢复此版本材料</button>
        </div>
        <div class="project-version-meta-grid">
          <div><span>历史项目名称</span><strong>${escapeHtml(version.name)}</strong></div>
          <div><span>历史项目状态</span><strong>${version.status === "archived" ? "已归档" : "进行中"}</strong></div>
          <div><span>变更类型</span><strong>${escapeHtml(versionKindLabel(version.change_kind))}</strong></div>
          <div><span>来源版本</span><strong>${version.source_version_number ? `v${version.source_version_number}` : "无"}</strong></div>
        </div>
        <p class="project-history-safety">版本详情为只读摘要。恢复操作只恢复业务快照，当前项目名称、说明和归档状态不会被旧版本覆盖。</p>
        ${renderVersionMaterialSummary(version)}`;
    } catch (error) {
      detail.innerHTML = `<p class="project-empty error">${escapeHtml(error.message || String(error))}</p>`;
    }
  }

  async function restoreProjectVersion(versionNumber) {
    if (!currentProject || versionNumber === currentProject.lock_version) return;
    if (projectDirty && !confirm("当前项目有未保存更改。恢复历史版本会丢弃这些未保存更改，是否继续？")) return;
    if (!confirm(`确认把 v${versionNumber} 的业务材料恢复为新的当前版本吗？历史记录不会被删除。`)) return;
    const versionLabel = document.getElementById("projectVersionLabelInput")?.value.trim() || `恢复自版本 v${versionNumber}`;
    try {
      const project = await projectRequest(
        `/api/projects/${encodeURIComponent(currentProject.id)}/versions/${versionNumber}/restore`,
        {
          method: "POST",
          body: JSON.stringify({
            lock_version: currentProject.lock_version,
            version_label: versionLabel,
          }),
        },
      );
      toast(`已恢复 v${versionNumber} 的材料，并生成 v${project.lock_version}。`);
      applyProjectSnapshot(project);
    } catch (error) {
      await handleProjectConflict(error);
    }
  }

  function bindDirtyTracking() {
    document.addEventListener("input", event => {
      const id = event.target?.id || "";
      if (formInputIds.includes(id) || ["identityOrg", "identityRole", "identityContact"].includes(id)) {
        markProjectDirty();
      }
    });
    window.addEventListener(contracts.events.resultUpdated, event => {
      if (event.detail?.source === "commit") markProjectDirty();
    });
    window.addEventListener("beforeunload", event => {
      if (!currentProject || !projectDirty) return;
      event.preventDefault();
      event.returnValue = "";
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && document.getElementById("projectManagerModal")?.classList.contains("show")) {
        closeProjectManager();
      }
    });
  }

  function restoreSectionAfterProjectLoad() {
    const section = localStorage.getItem(RESTORE_SECTION_STORAGE);
    if (!section) return;
    localStorage.removeItem(RESTORE_SECTION_STORAGE);
    setTimeout(() => go(section), 0);
  }

  injectProjectUI();
  bindDirtyTracking();
  restoreSectionAfterProjectLoad();
  window.PROJECT_STORAGE_READY = true;
  window.PROJECT_HISTORY_READY = true;
})();
