/* Small runtime guards for customer-facing copy and legacy DOM id collisions. */
(() => {
  const TOAST_REWRITES = [
    [/模型配置已保存/g, "AI 服务设置已保存"],
    [/已切换当前编辑内容为公共模型，保存后生效/g, "已选择平台 AI 服务，保存后生效"],
    [/已从当前编辑内容中清空 API Key，保存后生效/g, "已清除访问密钥，保存后生效"],
    [/已生成示例结果；不会计入正式工作台、待核对事项或运营报告/g, "示例内容仅供体验，不会加入当前项目、待处理事项或报告"],
    [/当前包含示例或旧会话材料。请先清除隔离材料，再保存正式项目/g, "当前包含示例或历史会话内容。请先清除这些内容，再保存项目"],
    [/已清除 (\d+) 项示例或旧会话材料/g, "已清除 $1 项示例或历史会话内容"],
  ];

  function fixServiceDialogTitleId() {
    const dialog = document.querySelector("#serviceWorkflowModal .service-workflow-dialog");
    const title = dialog?.querySelector(":scope > header h2");
    if (!dialog || !title) return;
    if (title.id === "swTitle") title.id = "swDialogTitle";
    if (dialog.getAttribute("aria-labelledby") === "swTitle") dialog.setAttribute("aria-labelledby", "swDialogTitle");
  }

  function rewriteToastMessage(message) {
    let value = String(message || "");
    TOAST_REWRITES.forEach(([pattern, replacement]) => { value = value.replace(pattern, replacement); });
    return value;
  }

  function wrapToast() {
    const original = window.toast;
    if (typeof original !== "function" || original.__enterpriseWrapped) return;
    const wrapped = function enterpriseToast(message) {
      return original.call(this, rewriteToastMessage(message));
    };
    wrapped.__enterpriseWrapped = true;
    wrapped.__enterpriseOriginal = original;
    window.toast = wrapped;
  }

  function apply() {
    fixServiceDialogTitleId();
    wrapToast();
    window.ZHILINK_ENTERPRISE_USER_VIEW_GUARDS_READY = true;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply, { once: true });
  else apply();
})();
