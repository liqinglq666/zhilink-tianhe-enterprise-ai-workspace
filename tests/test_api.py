from fastapi.testclient import TestClient

from backend.main import app, MAX_BODY_BYTES

client = TestClient(app)


def test_health():
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.json()
    assert data['ok'] is True
    assert 'fastapi' in data['version']


def test_defaults():
    resp = client.get('/api/defaults')
    assert resp.status_code == 200
    data = resp.json()
    assert 'provider_presets' in data
    assert 'modules' in data
    assert 'demo_profile' not in data
    assert 'demo_inputs' not in data


def test_profile_requires_api():
    resp = client.post('/api/profile', json={
        'config': {'api_key': '', 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'model': 'qwen-plus', 'temperature': 0.35},
        'profile': {'name': '测试企业', 'industry': '现代商贸', 'location': '天河路商圈', 'scale': '10-50人', 'stage': '成长扩张期', 'contact_role': '负责人', 'demands': '需要政策、合同、会议和供需协作'}
    })
    assert resp.status_code == 502
    assert '请先配置' in resp.json()['detail']


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
