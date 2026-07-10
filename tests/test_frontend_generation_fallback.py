from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_retries_failed_streams_with_stable_endpoint():
    script = (ROOT / "frontend" / "assets" / "bugfixes.js").read_text(encoding="utf-8")

    assert "async function requestStableGeneration" in script
    assert 'return streamUrl.replace(/\\/stream(?=\\?|$)/, "");' in script
    assert "return await requestStableGeneration(url, payload, key, err);" in script
    assert "流式通道暂不可用，正在自动切换稳定生成模式" in script


def test_stable_fallback_reuses_same_payload_and_saves_result():
    script = (ROOT / "frontend" / "assets" / "bugfixes.js").read_text(encoding="utf-8")

    assert "body: JSON.stringify(payload)" in script
    assert "window.finishStreamingResult(key, content, mode);" in script
    assert "data && data.ok === false" in script
    assert "模型稳定生成失败" in script
