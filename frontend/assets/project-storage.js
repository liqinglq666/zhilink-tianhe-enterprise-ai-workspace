/* Persistent project workspaces. Appended to app.js by backend. */
(() => {
  const WORKSPACE_KEY_STORAGE = "zhilian_workspace_key_v1";
  const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1";
  const RESTORE_SECTION_STORAGE = "zhilian_restore_section_v1";
  const PROJECT_TIMEOUT_MS = 20000;
  let currentProject = readJson(localStorage.getItem(CURRENT_PROJECT_STORAGE), null);
  let projectDirty = false;
  let includeArchived = false;

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
      result[key] = {
        mode: String(value?.mode || "").slice(0, 200),
        error: String(value?.error || "").slice(0, 1000),
        time: String(value?.time || "").slice(0, 100),
      };
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
    localStorage.setItem("zhilian_identity", JSON.stringify(snapshot.identity || {}));
    sessionStorage.setItem("zhilian_profile", JSON.stringify(snapshot.profile || {}));
    sessionStorage.setItem("zhilian_form_inputs", JSON.stringify(snapshot.forms || {}));
    sessionStorage.setItem("zhilian_results", JSON.stringify(snapshot.results || {}));
    sessionStorage.setItem("zhilian_meta", JSON.stringify(snapshot.meta || {}));
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
    button.textContent = `${currentProject.name}${projectDirty ? " · 未保存" : ""}`;
    button.title = projectDirty ? "当前项目有未保存更改" : "当前项目已保存";
    button.classList.toggle("project-dirty", projectDirty);
  }

  function injectProjectUI() {
    if (!document.querySelector('link[data-project-storage]')) {
      const stylesheet = document.createElement("link");
      stylesheet.rel = "stylesheet";
      stylesheet.href = "/assets/project-storage.css";
      stylesheet.dataset.projectStorage = "true";
      document.head.appendChild(stylesheet);
    }

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
              <h2 id="projectManagerTitle">项目与当前工作区</h2>
              <p>保存企业档案、业务表单和生成结果。模型 API Key 与接口配置不会写入项目。</p>
            </div>
            <button class="icon-btn" type="button" data-close-project-manager aria-label="关闭项目管理">✕</button>
          </div>
          <div class="project-current-card" id="projectCurrentCard"></div>
          <div class="project-editor">
            <label>项目名称<input id="projectNameInput" maxlength="120" placeholder="例如：天河商圈活动筹备" /></label>
            <label>项目说明<textarea id="projectDescriptionInput" maxlength="2000" rows="3" placeholder="说明项目目标、服务对象或当前阶段"></textarea></label>
            <div class="project-action-row">
              <button id="createProjectButton" class="primary" type="button">新建并保存</button>
              <button id="saveProjectButton" class="secondary" type="button">保存当前项目</button>
              <button id="archiveProjectButton" class="ghost" type="button">归档当前项目</button>
            </div>
          </div>
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
  }

  function openProjectManager() {
    const modal = document.getElementById("projectManagerModal");
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    renderCurrentProjectCard();
    loadProjectList();
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
    if (!currentProject) {
      card.innerHTML = "<strong>当前未打开持久化项目</strong><span>可以填写名称后新建，或从下方项目列表载入。</span>";
      nameInput.value = "";
      descriptionInput.value = "";
      archiveButton.disabled = true;
      saveButton.disabled = true;
      return;
    }
    card.innerHTML = `<strong>${escapeHtml(currentProject.name)}</strong><span>${currentProject.status === "archived" ? "已归档" : (projectDirty ? "有未保存更改" : "已保存")}</span>`;
    nameInput.value = currentProject.name || "";
    descriptionInput.value = currentProject.description || "";
    archiveButton.disabled = false;
    archiveButton.textContent = currentProject.status === "archived" ? "恢复当前项目" : "归档当前项目";
    saveButton.disabled = false;
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
          <div><h4>${escapeHtml(project.name)}</h4><p>${escapeHtml(project.description || "暂无说明")}</p><span>${project.status === "archived" ? "已归档" : "进行中"} · ${escapeHtml(updated)}</span></div>
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
    };
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
      renderCurrentProjectCard();
      await loadProjectList();
      toast("项目已创建并保存。");
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
      renderCurrentProjectCard();
      await loadProjectList();
      toast("项目已保存。");
    } catch (error) {
      if (error.code === "PROJECT_VERSION_CONFLICT") {
        toast("项目已在其他页面更新，请重新打开项目后再保存。");
        await loadProjectList();
      } else {
        toast(error.message || String(error));
      }
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
      toast(nextStatus === "archived" ? "项目已归档。" : "项目已恢复。" );
    } catch (error) {
      toast(error.message || String(error));
    }
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
    if (!confirm(`确认永久删除“${projectName}”吗？当前阶段尚未提供回收站。`)) return;
    try {
      await projectRequest(`/api/projects/${encodeURIComponent(projectId)}`, { method: "DELETE" });
      if (currentProject?.id === projectId) setCurrentProject(null, false);
      renderCurrentProjectCard();
      await loadProjectList();
      toast("项目已删除。");
    } catch (error) {
      toast(error.message || String(error));
    }
  }

  function bindDirtyTracking() {
    document.addEventListener("input", event => {
      const id = event.target?.id || "";
      if (formInputIds.includes(id) || ["identityOrg", "identityRole", "identityContact"].includes(id)) {
        markProjectDirty();
      }
    });
    const originalSetResult = setResult;
    setResult = function setResultAndMarkProject(key, result) {
      originalSetResult(key, result);
      markProjectDirty();
    };
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
})();
