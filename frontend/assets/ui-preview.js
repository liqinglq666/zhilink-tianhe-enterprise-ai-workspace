(() => {
  "use strict";

  const body = document.body;
  const sidebar = document.getElementById("previewSidebar");
  const scrim = document.getElementById("sidebarScrim");
  const mobileMenu = document.getElementById("mobileMenu");
  const collapseSidebar = document.getElementById("collapseSidebar");
  const accountButton = document.getElementById("accountButton");
  const accountMenu = document.getElementById("accountMenu");
  const newTaskButton = document.getElementById("newTaskButton");
  const taskDialog = document.getElementById("taskDialog");
  const toast = document.getElementById("previewToast");
  let toastTimer = null;

  const taskNames = {
    meeting: "会议纪要",
    contract: "合同审阅",
    policy: "政策助手",
    match: "供需协作",
    profile: "企业档案",
    landing: "实施计划",
    report: "报告归档",
  };

  function showToast(message) {
    if (!toast) return;
    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add("show");
    toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2600);
  }

  function closeAccountMenu() {
    if (!accountMenu || !accountButton) return;
    accountMenu.hidden = true;
    accountButton.setAttribute("aria-expanded", "false");
  }

  function toggleAccountMenu() {
    if (!accountMenu || !accountButton) return;
    const willOpen = accountMenu.hidden;
    accountMenu.hidden = !willOpen;
    accountButton.setAttribute("aria-expanded", String(willOpen));
  }

  function closeMobileNavigation() {
    body.classList.remove("mobile-nav-open");
    if (scrim) scrim.hidden = true;
  }

  function openMobileNavigation() {
    body.classList.add("mobile-nav-open");
    if (scrim) scrim.hidden = false;
  }

  function handleTask(taskKey) {
    const name = taskNames[taskKey] || "业务任务";
    if (taskDialog?.open) taskDialog.close();
    closeMobileNavigation();
    showToast(`UI 预览：${name}入口已响应，确认设计后将连接现有模块。`);

    document.querySelectorAll(".preview-nav .nav-item").forEach((item) => {
      item.classList.toggle("active", item.dataset.task === taskKey);
    });
    window.setTimeout(() => {
      document.querySelector(".task-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
  }

  accountButton?.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleAccountMenu();
  });

  document.addEventListener("click", (event) => {
    if (accountMenu && accountButton && !accountMenu.hidden) {
      const target = event.target;
      if (target instanceof Node && !accountMenu.contains(target) && !accountButton.contains(target)) {
        closeAccountMenu();
      }
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAccountMenu();
      closeMobileNavigation();
    }
  });

  mobileMenu?.addEventListener("click", openMobileNavigation);
  scrim?.addEventListener("click", closeMobileNavigation);

  collapseSidebar?.addEventListener("click", () => {
    const collapsed = body.classList.toggle("sidebar-collapsed");
    try {
      window.localStorage.setItem("zhilink_preview_sidebar_collapsed", collapsed ? "1" : "0");
    } catch (_error) {
      // The preview remains usable when storage is unavailable.
    }
  });

  try {
    if (window.localStorage.getItem("zhilink_preview_sidebar_collapsed") === "1" && window.innerWidth > 820) {
      body.classList.add("sidebar-collapsed");
    }
  } catch (_error) {
    // Storage may be blocked in private browsing contexts.
  }

  newTaskButton?.addEventListener("click", () => {
    if (typeof taskDialog?.showModal === "function") {
      taskDialog.showModal();
    } else {
      showToast("请选择下方任一常用任务开始处理。 ");
      document.querySelector(".task-section")?.scrollIntoView({ behavior: "smooth" });
    }
  });

  document.querySelectorAll("[data-task]").forEach((element) => {
    element.addEventListener("click", (event) => {
      event.preventDefault();
      handleTask(element.dataset.task);
    });
    if (element.getAttribute("role") === "button") {
      element.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          handleTask(element.dataset.task);
        }
      });
    }
  });

  document.querySelectorAll("[data-account-action]").forEach((element) => {
    element.addEventListener("click", () => {
      const action = element.dataset.accountAction || "账户设置";
      closeAccountMenu();
      showToast(`UI 预览：${action}将复用当前系统能力。`);
    });
  });

  document.querySelectorAll("[data-top-action]").forEach((element) => {
    element.addEventListener("click", () => {
      showToast(`UI 预览：${element.dataset.topAction}入口已响应。`);
    });
  });

  document.querySelectorAll("[data-demo-project]").forEach((element) => {
    element.addEventListener("click", () => {
      showToast(`展示项目：${element.dataset.demoProject}`);
      closeMobileNavigation();
    });
  });

  document.querySelectorAll("[data-demo-material]").forEach((element) => {
    element.addEventListener("click", () => showToast(`展示材料：${element.dataset.demoMaterial}`));
  });

  document.querySelectorAll("[data-demo-pending]").forEach((element) => {
    element.addEventListener("click", () => showToast(`待确认：${element.dataset.demoPending}`));
  });

  document.getElementById("viewAllTasks")?.addEventListener("click", () => {
    if (typeof taskDialog?.showModal === "function") taskDialog.showModal();
  });

  document.getElementById("feedbackButton")?.addEventListener("click", () => {
    showToast("这是新版 UI 预览，可直接在聊天中告诉我需要调整的位置。 ");
  });

  document.querySelector("[data-preview-nav]")?.addEventListener("click", () => {
    document.querySelectorAll(".preview-nav .nav-item").forEach((item) => item.classList.remove("active"));
    document.querySelector("[data-preview-nav]")?.classList.add("active");
    closeMobileNavigation();
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 820) closeMobileNavigation();
  });

  if (sidebar) sidebar.setAttribute("data-preview-ready", "true");
  window.ZHILINK_UI_PREVIEW_READY = true;
})();
