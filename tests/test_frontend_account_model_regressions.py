from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def _run_node(source: str) -> None:
    completed = subprocess.run(
        ["node", "-e", source],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_model_connection_check_uses_live_safe_transport() -> None:
    script = ASSETS / "api-drawer-v4.js"
    source = script.read_text(encoding="utf-8")

    assert 'fetch("/api/test-connection"' in source
    assert "interceptLegacyConnectionCheck" in source
    assert "event.stopImmediatePropagation()" in source
    assert "CONNECTION_TECHNICAL_DETAIL_RE" in source
    assert "window.apiPost" not in source

    harness = f"""
const fs = require('fs');
const vm = require('vm');
class Element {{}}
global.Element = Element;
const elements = {{
  testConnection: Object.assign(new Element(), {{ textContent: '检查连接', disabled: false, dataset: {{}}, closest: s => s === '#testConnection' ? elements.testConnection : null }}),
  connectionResult: {{ textContent: '' }},
  apiKey: {{ value: 'sk-test-only' }},
  baseUrl: {{ value: 'https://example.com/v1' }},
  modelName: {{ value: 'test-model' }},
  temperature: {{ value: '0.35' }},
}};
const clickHandlers = [];
global.document = {{
  readyState: 'loading',
  body: {{ classList: {{ contains: () => false, add: () => {{}}, remove: () => {{}} }} }},
  getElementById: id => elements[id] || null,
  addEventListener: (type, handler, options) => {{ if (type === 'click' && options === true) clickHandlers.push(handler); }},
}};
global.window = {{ ZHILINK_UI_V4_RUNTIME: {{ subscribe: () => {{}} }} }};
let request = null;
global.fetch = async (url, init) => {{
  request = {{ url, init }};
  return {{ ok: true, status: 200, json: async () => ({{ ok: true, content: '连接成功' }}) }};
}};
vm.runInThisContext(fs.readFileSync({json.dumps(str(script))}, 'utf8'));
if (clickHandlers.length !== 1) throw new Error(`expected one capture handler, got ${{clickHandlers.length}}`);
const event = {{ target: elements.testConnection, preventDefault() {{}}, stopImmediatePropagation() {{}} }};
clickHandlers[0](event);
setImmediate(() => {{
  if (!request || request.url !== '/api/test-connection') throw new Error('connection endpoint was not called');
  const payload = JSON.parse(request.init.body);
  if (payload.api_key !== 'sk-test-only' || payload.model !== 'test-model') throw new Error('draft config was not sent');
  if (!elements.connectionResult.textContent.includes('服务可用')) throw new Error(elements.connectionResult.textContent);
  if (elements.testConnection.disabled) throw new Error('button remained disabled');
}});
"""
    _run_node(harness)


def test_logout_clears_user_scoped_browser_state_only_on_unload() -> None:
    script = ASSETS / "storage-recovery.js"
    source = script.read_text(encoding="utf-8")

    for key in (
        "zhilian_api_key",
        "zhilian_profile",
        "zhilian_form_inputs",
        "zhilian_results",
        "zhilian_meta",
        "zhilian_identity",
        "zhilian_provider",
        "zhilian_base_url",
        "zhilian_model",
        "zhilian_temperature",
    ):
        assert key in source
    assert 'target?.closest("#logoutButton")' in source
    assert 'window.addEventListener("beforeunload"' in source

    harness = f"""
const fs = require('fs');
const vm = require('vm');
class Element {{}}
global.Element = Element;
class Storage {{
  constructor() {{ this.data = new Map(); }}
  getItem(key) {{ return this.data.has(key) ? this.data.get(key) : null; }}
  setItem(key, value) {{ this.data.set(key, String(value)); }}
  removeItem(key) {{ this.data.delete(key); }}
}}
global.localStorage = new Storage();
global.sessionStorage = new Storage();
localStorage.setItem('zhilian_identity', '{{}}');
localStorage.setItem('zhilian_current_project_v1', '{{}}');
localStorage.setItem('zhilian_provider', 'custom');
localStorage.setItem('zhilian_base_url', 'https://example.com/v1');
localStorage.setItem('zhilian_model', 'secret-model');
localStorage.setItem('zhilian_temperature', '0.5');
localStorage.setItem('keep_me', 'preserved');
sessionStorage.setItem('zhilian_profile', '{{}}');
sessionStorage.setItem('zhilian_form_inputs', '{{}}');
sessionStorage.setItem('zhilian_results', '{{}}');
sessionStorage.setItem('zhilian_meta', '{{}}');
sessionStorage.setItem('zhilian_api_key', 'sk-sensitive');
const clickHandlers = [];
const unloadHandlers = [];
global.document = {{ addEventListener: (type, handler, options) => {{ if (type === 'click' && options === true) clickHandlers.push(handler); }} }};
global.window = {{ addEventListener: (type, handler) => {{ if (type === 'beforeunload') unloadHandlers.push(handler); }} }};
vm.runInThisContext(fs.readFileSync({json.dumps(str(script))}, 'utf8'));
if (clickHandlers.length !== 1 || unloadHandlers.length !== 1) throw new Error('logout lifecycle listeners missing');
const target = Object.assign(new Element(), {{ closest: s => s === '#logoutButton' ? target : null }});
clickHandlers[0]({{ target }});
if (!sessionStorage.getItem('zhilian_api_key')) throw new Error('state cleared before successful unload');
unloadHandlers[0]();
for (const key of ['zhilian_api_key','zhilian_profile','zhilian_form_inputs','zhilian_results','zhilian_meta']) {{
  if (sessionStorage.getItem(key) !== null) throw new Error(`session key leaked: ${{key}}`);
}}
for (const key of ['zhilian_identity','zhilian_provider','zhilian_base_url','zhilian_model','zhilian_temperature']) {{
  if (localStorage.getItem(key) !== null) throw new Error(`local key leaked: ${{key}}`);
}}
if (localStorage.getItem('keep_me') !== 'preserved') throw new Error('unrelated browser state was removed');
"""
    _run_node(harness)
