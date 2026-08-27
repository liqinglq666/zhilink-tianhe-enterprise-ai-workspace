from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACCOUNT_ACCESS = ROOT / "frontend" / "assets" / "account-access.js"


def _function_segment(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_authentication_reinitializes_workspace_scope() -> None:
    source = ACCOUNT_ACCESS.read_text(encoding="utf-8")
    authenticate = _function_segment(
        source,
        "  async function authenticate(path, form) {",
        "  async function createOrganization(form) {",
    )

    clear_project = authenticate.index("localStorage.removeItem(CURRENT_PROJECT_STORAGE);")
    reload_workspace = authenticate.index("location.reload();")

    assert clear_project < reload_workspace
    assert "applyRoleState();" not in authenticate
    assert "renderAccountManager();" not in authenticate


def test_all_explicit_scope_changes_reload_workspace() -> None:
    source = ACCOUNT_ACCESS.read_text(encoding="utf-8")

    for start_marker, end_marker in (
        ("  async function authenticate(path, form) {", "  async function createOrganization(form) {"),
        ("  async function createOrganization(form) {", "  async function addMember(form) {"),
        ("  async function claimAnonymousProjects() {", "  async function logout() {"),
        ("  async function logout() {", "  function switchOrganization(value) {"),
        ("  function switchOrganization(value) {", "  function handleModalClick(event) {"),
    ):
        segment = _function_segment(source, start_marker, end_marker)
        assert "localStorage.removeItem(CURRENT_PROJECT_STORAGE);" in segment
        assert "location.reload();" in segment


def test_account_requests_keep_transport_errors_business_facing() -> None:
    source = ACCOUNT_ACCESS.read_text(encoding="utf-8")
    request_segment = _function_segment(
        source,
        "  function accountFailureMessage(status, detail) {",
        "  function activeOrganization() {",
    )

    assert "ACCOUNT_TECHNICAL_DETAIL_RE" in source
    assert "message.length <= 180" in request_segment
    assert "!ACCOUNT_TECHNICAL_DETAIL_RE.test(message)" in request_segment
    assert "[400, 401, 403, 404, 409, 422].includes(status)" in request_segment
    assert 'status === 429' in request_segment
    assert 'status >= 500' in request_segment
    assert '账户服务暂时不可用，请稍后重试。' in request_segment
    assert '网络连接异常，请稍后重试。' in request_segment
    assert "accountFailureMessage(response.status, data.detail)" in request_segment
    assert 'new Error(data.detail || text || "操作失败。")' not in request_segment
    assert 'new Error(text)' not in request_segment


def test_account_catches_do_not_fall_back_to_raw_error_stringification() -> None:
    source = ACCOUNT_ACCESS.read_text(encoding="utf-8")
    assert "error.message || String(error)" not in source
