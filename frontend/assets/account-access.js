/* Same-origin account, organization, CSRF, and RBAC controls. */
(() => {
  const ACTIVE_ORG_STORAGE = "zhilian_active_organization_v1";
  const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1";
  const WORKSPACE_KEY_STORAGE = "zhilian_workspace_key_v1";
  const nativeFetch = window.fetch.bind(window);
  let account = {
    authenticated: false,
    user: null,
    organizations: [],
    csrf_token: "",
    expires_at: null,
  };
  let activeOrganizationId = localStorage.getItem(ACTIVE_ORG_STORAGE) || "";
  let accountModalOpen = false;
  let sessionReady = Promise.resolve();

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function notify(message) {
    if (typeof toast === "function") toast(message);
    else console.info(message);
  }

  function pathOf(input) {
    try {
      const raw = typeof input === "string" ? input : input.url;
      return new URL(raw, location.origin).pathname;
    } catch (_) {
      return "";
    }
  }

  function isWrite(method) {
    return ["POST", "PUT", "PATCH", "DELETE"].includes(String(method || "GET").toUpperCase());
  }

  window.fetch = async function securedWorkspaceFetch(input, init = {}) {
    const path = pathOf(input);
    const method = init.method || (typeof input !== "string" && input.method) || "GET";
    if (activeOrganizationId && isWrite(method) && !account.csrf_token) {
      await sessionReady;
    }
    const headers = new Headers(init.headers || (typeof input !== "string" ? input.headers : undefined));
    if (path.startsWith("/api/projects") && activeOrganizationId) {
      headers.set("X-Organization-Id", activeOrganizationId);
    }
    if (
      account.authenticated &&
      account.csrf_token &&
      isWrite(method) &&
      (path.startsWith("/api/projects") || path.startsWith("/api/organizations") || path === "/api/auth/logout")
    ) {
      headers.set("X-CSRF-Token", account.csrf_token);
    }
    return nativeFetch(input, {
      ...init,
      headers,
      credentials: "same-origin",
    });
  };

  async function request(path, options = {}) {
    const response = await fetch(path, options);
    const text = await response.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) { data = {}; }
    if (!response.ok) {
      const error = new Error(data.detail || text || "操作失败。");
      error.code = data.code || "ACCOUNT_REQUEST_FAILED";
      throw error;
    }
    return data;
  }

  function activeOrganization() {
    return account.organizations.find(item => item.id === activeOrganizationId) || null;
  }

  function normalizeActiveOrganization() {
    if (!account.authenticated) {
      activeOrganizationId = "";
      localStorage.removeItem(ACTIVE_ORG_STORAGE);
      return;
    }
    const stored = localStorage.getItem(ACTIVE_ORG_STORAGE);
    if (stored === "anonymous") {
      activeOrganizationId = "";
      return;
    }
    if (stored && account.organizations.some(item => item.id === stored)) {
      activeOrganizationId = stored;
      return;
    }
    activeOrganizationId = account.organizations[0]?.id || "";
    if (activeOrganizationId) localStorage.setItem(ACTIVE_ORG_STORAGE, activeOrganizationId);
  }

  function applyRoleState() {
    const organization = activeOrganization();
    document.body.dataset.authenticated = account.authenticated ? "true" : "false";
    document.body.dataset.orgRole = organization?.role || "anonymous";
    document.body.dataset.orgScope = organization ? "organization" : "anonymous";
    renderAccountButton();
  }

  function renderAccountButton() {
    const button = document.getElementById("openAccountManager");
    if (!button) return;
    if (!account.authenticated) {
      button.textContent = "登录 / 组织";
      button.title = "登录后使用组织空间和角色权限";
      return;
    }
    const organization = activeOrganization();
    button.textContent = organization
      ? `${organization.name} · ${roleLabel(organization.role)}`
      : `${account.user.display_name} · 匿名空间`;
    button.title = organization
      ? `当前组织：${organization.name}`
      : "当前仍在匿名浏览器工作区";
  }

  function roleLabel(role) {
    return ({ owner: "所有者", admin: "管理员", editor: "编辑者", viewer: "只读成员" })[role] || role || "";
  }

  function injectUI() {
    if (!document.querySelector("link[data-account-access]")) {
      const stylesheet = document.createElement("link");
      stylesheet.rel = "stylesheet";
      stylesheet.href = "/assets/account-access.css";
      stylesheet.dataset.accountAccess = "true";
      document.head.appendChild(stylesheet);
    }

    const topActions = document.querySelector(".top-actions");
    if (topActions && !document.getElementById("openAccountManager")) {
      const button = document.createElement("button");
      button.id = "openAccountManager";
      button.type = "button";
      button.className = "secondary account-manager-button";
      button.addEventListener("click", openAccountManager);
      const reportButton = topActions.querySelector('[data-goto="report"]');
      topActions.insertBefore(button, reportButton || topActions.firstChild);
    }

    if (!document.getElementById("accountManagerModal")) {
      const modal = document.createElement("div");
      modal.id = "accountManagerModal";
      modal.className = "account-modal";
      modal.setAttribute("aria-hidden", "true");
      modal.innerHTML = `
        <div class="account-modal-backdrop" data-close-account-manager></div>
        <section class="account-dialog" role="dialog" aria-modal="true" aria-labelledby="accountManagerTitle">
          <div class="account-dialog-header">
            <div>
              <span class="track">账号与组织</span>
              <h2 id="accountManagerTitle">组织空间与角色权限</h2>
              <p>登录会话使用 HttpOnly Cookie；组织项目按成员角色执行读取、编辑和管理权限。</p>
            </div>
            <button class="icon-btn" type="button" data-close-account-manager aria-label="关闭账号管理">✕</button>
          </div>
          <div id="accountManagerContent"></div>
        </section>`;
      document.body.appendChild(modal);
      modal.addEventListener("click", handleModalClick);
      modal.addEventListener("change", handleModalChange);
      modal.addEventListener("submit", handleModalSubmit);
    }
    renderAccountButton();
  }

  function renderAccountManager() {
    const content = document.getElementById("accountManagerContent");
    if (!content) return;
    if (!account.authenticated) {
      content.innerHTML = `
        <div class="account-auth-grid">
          <form id="loginForm" class="account-panel">
            <h3>登录</h3>
            <label>邮箱<input name="email" type="email" autocomplete="email" maxlength="320" required /></label>
            <label>密码<input name="password" type="password" autocomplete="current-password" maxlength="128" required /></label>
            <button class="primary" type="submit">登录</button>
          </form>
          <form id="registerForm" class="account-panel">
            <h3>注册并创建组织</h3>
            <label>显示名称<input name="display_name" maxlength="120" autocomplete="name" required /></label>
            <label>邮箱<input name="email" type="email" autocomplete="email" maxlength="320" required /></label>
            <label>密码<input name="password" type="password" autocomplete="new-password" maxlength="128" required /></label>
            <label>组织名称<input name="organization_name" maxlength="120" placeholder="留空则自动创建个人工作区" /></label>
            <button class="primary" type="submit">注册</button>
          </form>
        </div>
        <p class="account-note">当前版本暂未接入邮箱验证、密码找回和邮件邀请。请勿在公开演示环境使用重要生产密码。</p>`;
      return;
    }

    const organization = activeOrganization();
    const options = [
      '<option value="anonymous">匿名浏览器工作区</option>',
      ...account.organizations.map(item => `<option value="${safe(item.id)}" ${item.id === activeOrganizationId ? "selected" : ""}>${safe(item.name)} · ${safe(roleLabel(item.role))}</option>`),
    ].join("");
    const canManage = ["owner", "admin"].includes(organization?.role || "");
    content.innerHTML = `
      <section class="account-profile-card">
        <div><strong>${safe(account.user.display_name)}</strong><span>${safe(account.user.email)}</span></div>
        <button id="logoutButton" class="ghost" type="button">退出登录</button>
      </section>
      <section class="account-panel">
        <h3>当前工作空间</h3>
        <label>项目范围<select id="activeOrganizationSelect">${options}</select></label>
        <p>${organization ? `当前角色：${safe(roleLabel(organization.role))}。项目和版本历史归属于该组织。` : "当前使用匿名浏览器工作区；清除网站数据会失去匿名项目访问密钥。"}</p>
        <form id="createOrganizationForm" class="account-inline-form">
          <input name="name" maxlength="120" placeholder="新组织名称" required />
          <button class="secondary" type="submit">创建组织</button>
        </form>
        ${organization && canManage ? '<button id="claimAnonymousProjectsButton" class="secondary" type="button">迁移本浏览器匿名项目到当前组织</button>' : ""}
      </section>
      ${organization ? `
        <section class="account-panel">
          <div class="account-section-heading"><div><h3>组织成员</h3><p>所有者可管理全部角色；管理员只能管理编辑者和只读成员。</p></div><button id="refreshMembersButton" class="secondary small" type="button">刷新</button></div>
          ${canManage ? `
            <form id="addMemberForm" class="account-member-form">
              <input name="email" type="email" maxlength="320" placeholder="已注册成员邮箱" required />
              <select name="role">
                <option value="viewer">只读成员</option>
                <option value="editor">编辑者</option>
                ${organization.role === "owner" ? '<option value="admin">管理员</option><option value="owner">所有者</option>' : ""}
              </select>
              <button class="secondary" type="submit">添加成员</button>
            </form>` : ""}
          <div id="organizationMemberList" class="account-member-list"><p class="account-empty">正在读取成员...</p></div>
        </section>` : ""}`;
    if (organization) loadMembers();
  }

  async function loadSession() {
    try {
      account = await request("/api/auth/session");
    } catch (error) {
      account = { authenticated: false, user: null, organizations: [], csrf_token: "", expires_at: null };
      console.warn("Account session unavailable", error);
    }
    normalizeActiveOrganization();
    applyRoleState();
    if (accountModalOpen) renderAccountManager();
  }

  async function loadMembers() {
    const list = document.getElementById("organizationMemberList");
    const organization = activeOrganization();
    if (!list || !organization) return;
    try {
      const data = await request(`/api/organizations/${encodeURIComponent(organization.id)}/members`);
      const canManage = ["owner", "admin"].includes(organization.role);
      list.innerHTML = data.items.map(member => {
        const canEditTarget = canManage && (
          organization.role === "owner" || !["owner", "admin"].includes(member.role)
        );
        const roleOptions = ["viewer", "editor", "admin", "owner"].filter(role => (
          organization.role === "owner" || ["viewer", "editor"].includes(role)
        )).map(role => `<option value="${role}" ${role === member.role ? "selected" : ""}>${safe(roleLabel(role))}</option>`).join("");
        return `<article class="account-member-item">
          <div><strong>${safe(member.display_name)}</strong><span>${safe(member.email)}</span></div>
          <div class="account-member-actions">
            ${canEditTarget ? `<select data-member-role="${safe(member.user_id)}">${roleOptions}</select><button class="danger-light small" type="button" data-remove-member="${safe(member.user_id)}" data-member-name="${safe(member.display_name)}">移除</button>` : `<span class="account-role-badge">${safe(roleLabel(member.role))}</span>`}
          </div>
        </article>`;
      }).join("") || '<p class="account-empty">当前组织没有成员。</p>';
    } catch (error) {
      list.innerHTML = `<p class="account-empty error">${safe(error.message || String(error))}</p>`;
    }
  }

  function openAccountManager() {
    accountModalOpen = true;
    const modal = document.getElementById("accountManagerModal");
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    renderAccountManager();
  }

  function closeAccountManager() {
    accountModalOpen = false;
    const modal = document.getElementById("accountManagerModal");
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
  }

  async function authenticate(path, form) {
    const values = Object.fromEntries(new FormData(form).entries());
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      account = await request(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      normalizeActiveOrganization();
      localStorage.removeItem(CURRENT_PROJECT_STORAGE);
      applyRoleState();
      renderAccountManager();
      notify(path.endsWith("register") ? "账号和组织已创建。" : "登录成功。" );
    } catch (error) {
      notify(error.message || String(error));
    } finally {
      button.disabled = false;
    }
  }

  async function createOrganization(form) {
    const name = new FormData(form).get("name")?.toString().trim() || "";
    if (!name) return;
    try {
      const organization = await request("/api/organizations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      account.organizations.push(organization);
      activeOrganizationId = organization.id;
      localStorage.setItem(ACTIVE_ORG_STORAGE, activeOrganizationId);
      localStorage.removeItem(CURRENT_PROJECT_STORAGE);
      notify("组织已创建，正在切换工作空间。");
      location.reload();
    } catch (error) {
      notify(error.message || String(error));
    }
  }

  async function addMember(form) {
    const organization = activeOrganization();
    if (!organization) return;
    const values = Object.fromEntries(new FormData(form).entries());
    try {
      await request(`/api/organizations/${encodeURIComponent(organization.id)}/members`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      form.reset();
      await loadMembers();
      notify("组织成员已添加。" );
    } catch (error) {
      notify(error.message || String(error));
    }
  }

  async function updateMemberRole(userId, role) {
    const organization = activeOrganization();
    if (!organization) return;
    try {
      await request(`/api/organizations/${encodeURIComponent(organization.id)}/members/${encodeURIComponent(userId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      await loadMembers();
      notify("成员角色已更新。" );
    } catch (error) {
      notify(error.message || String(error));
      await loadMembers();
    }
  }

  async function removeMember(userId, name) {
    const organization = activeOrganization();
    if (!organization || !confirm(`确认将“${name}”移出当前组织吗？`)) return;
    try {
      await request(`/api/organizations/${encodeURIComponent(organization.id)}/members/${encodeURIComponent(userId)}`, { method: "DELETE" });
      await loadMembers();
      notify("成员已移出组织。" );
    } catch (error) {
      notify(error.message || String(error));
    }
  }

  function ensureWorkspaceKey() {
    let key = localStorage.getItem(WORKSPACE_KEY_STORAGE) || "";
    if (key.length >= 32) return key;
    if (!window.crypto?.getRandomValues) throw new Error("当前浏览器不支持安全随机数。");
    const bytes = new Uint8Array(32);
    window.crypto.getRandomValues(bytes);
    key = Array.from(bytes, value => value.toString(16).padStart(2, "0")).join("");
    localStorage.setItem(WORKSPACE_KEY_STORAGE, key);
    return key;
  }

  async function claimAnonymousProjects() {
    const organization = activeOrganization();
    if (!organization) return;
    if (!confirm("迁移后，这些项目将只在当前组织空间中可见，匿名工作区将不再拥有访问权限。是否继续？")) return;
    try {
      const data = await request(`/api/organizations/${encodeURIComponent(organization.id)}/claim-workspace-projects`, {
        method: "POST",
        headers: { "X-Workspace-Key": ensureWorkspaceKey() },
      });
      localStorage.removeItem(CURRENT_PROJECT_STORAGE);
      notify(`已迁移 ${data.claimed} 个匿名项目。`);
      location.reload();
    } catch (error) {
      notify(error.message || String(error));
    }
  }

  async function logout() {
    try {
      await request("/api/auth/logout", { method: "POST" });
    } catch (error) {
      notify(error.message || String(error));
      return;
    }
    account = { authenticated: false, user: null, organizations: [], csrf_token: "", expires_at: null };
    activeOrganizationId = "";
    localStorage.removeItem(ACTIVE_ORG_STORAGE);
    localStorage.removeItem(CURRENT_PROJECT_STORAGE);
    notify("已退出登录。" );
    location.reload();
  }

  function switchOrganization(value) {
    const next = value === "anonymous" ? "" : value;
    if (next === activeOrganizationId) return;
    activeOrganizationId = next;
    localStorage.setItem(ACTIVE_ORG_STORAGE, next || "anonymous");
    localStorage.removeItem(CURRENT_PROJECT_STORAGE);
    location.reload();
  }

  function handleModalClick(event) {
    if (event.target.closest("[data-close-account-manager]")) return closeAccountManager();
    if (event.target.closest("#logoutButton")) return logout();
    if (event.target.closest("#refreshMembersButton")) return loadMembers();
    if (event.target.closest("#claimAnonymousProjectsButton")) return claimAnonymousProjects();
    const remove = event.target.closest("[data-remove-member]");
    if (remove) removeMember(remove.dataset.removeMember, remove.dataset.memberName || "该成员");
  }

  function handleModalChange(event) {
    if (event.target.id === "activeOrganizationSelect") switchOrganization(event.target.value);
    if (event.target.matches("[data-member-role]")) updateMemberRole(event.target.dataset.memberRole, event.target.value);
  }

  function handleModalSubmit(event) {
    event.preventDefault();
    if (event.target.id === "loginForm") authenticate("/api/auth/login", event.target);
    if (event.target.id === "registerForm") authenticate("/api/auth/register", event.target);
    if (event.target.id === "createOrganizationForm") createOrganization(event.target);
    if (event.target.id === "addMemberForm") addMember(event.target);
  }

  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && accountModalOpen) closeAccountManager();
  });

  injectUI();
  sessionReady = loadSession().finally(() => {
    window.ACCOUNT_ACCESS_READY = true;
    document.dispatchEvent(new CustomEvent("zhilink:account-ready"));
  });
  window.ZHILINK_ACCOUNT = {
    getSession: () => account,
    getActiveOrganizationId: () => activeOrganizationId,
    getActiveOrganization: activeOrganization,
    reload: loadSession,
  };
})();
