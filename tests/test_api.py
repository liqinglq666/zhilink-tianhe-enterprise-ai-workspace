from fastapi.testclient import TestClient

from backend.main import app, MAX_BODY_BYTES

client = TestClient(app)


def test_health():
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.json()
    assert data['ok'] is True
    assert 'generation-controls' in data['version']
    assert 'project-storage' in data['version']


def test_defaults():
    resp = client.get('/api/defaults')
    assert resp.status_code == 200
    data = resp.json()
    assert 'provider_presets' in data
    assert 'modules' in data
    assert 'demo_profile' not in data
    assert 'demo_inputs' not in data


def test_frontend_bundle_contains_generation_and_project_controls():
    resp = client.get('/assets/app.js')
    assert resp.status_code == 200
    assert 'GENERATION_CANCELLED' in resp.text
    assert 'data-cancel-generation' in resp.text
    assert 'PROJECT_STORAGE_READY' in resp.text
    assert 'X-Workspace-Key' in resp.text
    assert resp.headers['cache-control'] == 'no-store, max-age=0'
    assert resp.headers['content-type'].startswith('application/javascript')


def test_profile_requires_api():
    resp = client.post('/api/profile', json={
        'config': {'api_key': '', 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'model': 'qwen-plus', 'temperature': 0.35},
        'profile': {'name': '测试企业', 'industry': '现代商贸', 'location': '天河路商圈', 'scale': '10-50人', 'stage': '成长扩张期', 'contact_role': '负责人', 'demands': '需要政策、合同、会议和供需协作'}
    })
    assert resp.status_code == 400
    data = resp.json()
    assert data['code'] == 'MODEL_NOT_CONFIGURED'
    assert data['retryable'] is False
    assert 'API Key' in data['detail']


def test_connection_test_returns_error_metadata():
    resp = client.post('/api/test-connection', json={
        'api_key': '',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'model': 'qwen-plus',
        'temperature': 0.35,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['ok'] is False
    assert data['error_code'] == 'MODEL_NOT_CONFIGURED'
    assert data['retryable'] is False


def test_meeting_validation():
    resp = client.post('/api/meeting', json={
        'config': {},
        'text': '太短',
        'profile_summary': ''
    })
    assert resp.status_code == 400


def test_report_txt_export():
    resp = client.post('/api/report/txt', json={
        'config': {},
        'results': {'企业档案': '测试画像', '合同审阅': '测试风险'},
        'use_ai_summary': False,
    })
    assert resp.status_code == 200
    assert '测试画像' in resp.text
    assert resp.headers['content-type'].startswith('text/plain')


def test_body_size_limit():
    body = b'{"x":"' + (b'a' * (MAX_BODY_BYTES + 10)) + b'"}'
    resp = client.post('/api/report/txt', content=body, headers={'content-type': 'application/json'})
    assert resp.status_code == 413


def test_security_headers_are_applied_to_success_and_error_responses():
    for resp in (client.get('/health'), client.get('/missing-page')):
        assert resp.headers['x-content-type-options'] == 'nosniff'
        assert resp.headers['x-frame-options'] == 'DENY'
        assert resp.headers['content-security-policy'].startswith("default-src 'self'")


def test_api_responses_are_not_cached():
    resp = client.get('/api/defaults')
    assert resp.headers['cache-control'] == 'no-store'
    assert resp.headers['pragma'] == 'no-cache'
