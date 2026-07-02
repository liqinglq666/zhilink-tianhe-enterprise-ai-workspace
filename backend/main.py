# -*- coding: utf-8 -*-
"""FastAPI entrypoint for 智链天河：企业运营 AI 助手."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from zhilian_tianhe_agent.constants import (  # noqa: E402
    APP_FULL_NAME,
    APP_SUBTITLE,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LEGAL_DISCLAIMER,
    MODULES,
)
from zhilian_tianhe_agent.llm_client import LLMClient, LLMConfig  # noqa: E402

from .schemas import (  # noqa: E402
    APIConfig,
    AgentResponse,
    DefaultsResponse,
    HealthResponse,
    LandingRequest,
    MatchRequest,
    PolicyRequest,
    ProfileRequest,
    ReportRequest,
    TextRequest,
)
from .service import agent_response, build_docx, build_markdown, make_hub, profile_to_dict  # noqa: E402

APP_VERSION = "2.2.0-fastapi-streaming"
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "1500000"))
FRONTEND_DIR = ROOT / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"

PROVIDER_PRESETS = {
    "通义千问 DashScope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "tip": "适合国内使用，支持阿里云百炼 DashScope 的 OpenAI 兼容接口。",
    },
    "OpenAI 兼容接口": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "tip": "适合 OpenAI 官方接口或兼容网关。",
    },
    "自定义兼容接口": {
        "base_url": DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
        "tip": "适合硅基流动、DeepSeek、火山方舟、私有化网关等 OpenAI-compatible 接口。",
    },
}


app = FastAPI(
    title=APP_FULL_NAME,
    description=APP_SUBTITLE,
    version=APP_VERSION,
)

cors_env = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
allow_origins = ["*"] if cors_env == "*" else [x.strip() for x in cors_env.split(",") if x.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Prevent accidental huge contract/meeting payloads in public web deployments."""

    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": f"请求内容过大，请脱敏并精简到 {MAX_BODY_BYTES // 1024}KB 以内后再提交。"},
            )
    return await call_next(request)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):  # noqa: ARG001
    return JSONResponse(status_code=502, content={"detail": str(exc)})

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):  # noqa: ARG001
    return JSONResponse(status_code=400, content={"detail": str(exc)})

app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(app=APP_FULL_NAME, version=APP_VERSION)


@app.get("/api/defaults", response_model=DefaultsResponse)
def defaults() -> DefaultsResponse:
    return DefaultsResponse(
        provider_presets=PROVIDER_PRESETS,
        modules=MODULES,
        disclaimer=LEGAL_DISCLAIMER,
    )


def _sse(data: dict) -> str:
    """Encode one server-sent-event data frame."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_response(chunks) -> StreamingResponse:
    """Wrap model token iterator as SSE stream for fetch ReadableStream."""

    def event_generator():
        full: list[str] = []
        yield _sse({"type": "meta", "mode": "AI模型流式模式"})
        try:
            for chunk in chunks:
                if not chunk:
                    continue
                full.append(chunk)
                yield _sse({"type": "delta", "content": chunk})
            yield _sse({"type": "done", "content": "".join(full), "mode": "AI模型流式模式"})
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "error": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/test-connection", response_model=AgentResponse)
def test_connection(config: APIConfig) -> AgentResponse:
    client = LLMClient(
        LLMConfig(
            api_key=config.api_key.strip(),
            base_url=config.base_url.strip(),
            model=config.model.strip(),
            temperature=config.temperature,
            timeout=20,
        )
    )
    if not client.enabled:
        return AgentResponse(ok=False, mode="未配置", error="请先填写 API Key、Base URL 和模型名称。")
    try:
        content = client.chat("你是接口连通性测试助手。", "请只回复：连接成功")
        return AgentResponse(ok=True, content=content, mode="AI模型模式")
    except Exception as exc:  # noqa: BLE001
        return AgentResponse(ok=False, mode="连接失败", error=str(exc))


@app.post("/api/profile", response_model=AgentResponse)
def profile(req: ProfileRequest) -> AgentResponse:
    hub = make_hub(req.config)
    return agent_response(hub.profile.run(profile_to_dict(req.profile)))



@app.post("/api/profile/stream")
def profile_stream(req: ProfileRequest) -> StreamingResponse:
    hub = make_hub(req.config)
    return _stream_response(hub.profile.stream(profile_to_dict(req.profile)))


@app.post("/api/meeting", response_model=AgentResponse)
def meeting(req: TextRequest) -> AgentResponse:
    if len(req.text.strip()) < 8:
        raise HTTPException(status_code=400, detail="会议内容过短，请补充会议背景、结论或待办事项。")
    hub = make_hub(req.config)
    return agent_response(hub.meeting.run(req.text, req.profile_summary))



@app.post("/api/meeting/stream")
def meeting_stream(req: TextRequest) -> StreamingResponse:
    if len(req.text.strip()) < 8:
        raise HTTPException(status_code=400, detail="会议内容过短，请补充会议背景、结论或待办事项。")
    hub = make_hub(req.config)
    return _stream_response(hub.meeting.stream(req.text, req.profile_summary))


@app.post("/api/contract", response_model=AgentResponse)
def contract(req: TextRequest) -> AgentResponse:
    if len(req.text.strip()) < 12:
        raise HTTPException(status_code=400, detail="合同文本过短，请粘贴关键条款后再生成风险提示。")
    hub = make_hub(req.config)
    return agent_response(hub.contract.run(req.text, req.profile_summary))



@app.post("/api/contract/stream")
def contract_stream(req: TextRequest) -> StreamingResponse:
    if len(req.text.strip()) < 12:
        raise HTTPException(status_code=400, detail="合同文本过短，请粘贴关键条款后再生成风险提示。")
    hub = make_hub(req.config)
    return _stream_response(hub.contract.stream(req.text, req.profile_summary))


@app.post("/api/policy", response_model=AgentResponse)
def policy(req: PolicyRequest) -> AgentResponse:
    hub = make_hub(req.config)
    return agent_response(hub.policy.run(profile_to_dict(req.profile), req.demand))



@app.post("/api/policy/stream")
def policy_stream(req: PolicyRequest) -> StreamingResponse:
    hub = make_hub(req.config)
    return _stream_response(hub.policy.stream(profile_to_dict(req.profile), req.demand))


@app.post("/api/match", response_model=AgentResponse)
def match(req: MatchRequest) -> AgentResponse:
    if not any([req.offer.strip(), req.need.strip(), req.target.strip(), req.scenario.strip()]):
        raise HTTPException(status_code=400, detail="请至少填写供给、需求、目标对象或业务场景中的一项。")
    hub = make_hub(req.config)
    return agent_response(hub.match.run(profile_to_dict(req.profile), req.offer, req.need, req.target, req.scenario))



@app.post("/api/match/stream")
def match_stream(req: MatchRequest) -> StreamingResponse:
    if not any([req.offer.strip(), req.need.strip(), req.target.strip(), req.scenario.strip()]):
        raise HTTPException(status_code=400, detail="请至少填写供给、需求、目标对象或业务场景中的一项。")
    hub = make_hub(req.config)
    return _stream_response(hub.match.stream(profile_to_dict(req.profile), req.offer, req.need, req.target, req.scenario))


@app.post("/api/landing", response_model=AgentResponse)
def landing(req: LandingRequest) -> AgentResponse:
    hub = make_hub(req.config)
    return agent_response(hub.landing.run(profile_to_dict(req.profile), req.landing_info, req.existing_results))



@app.post("/api/landing/stream")
def landing_stream(req: LandingRequest) -> StreamingResponse:
    hub = make_hub(req.config)
    return _stream_response(hub.landing.stream(profile_to_dict(req.profile), req.landing_info, req.existing_results))


@app.post("/api/report", response_model=AgentResponse)
def report(req: ReportRequest) -> AgentResponse:
    if req.use_ai_summary:
        hub = make_hub(req.config)
        return agent_response(hub.report.run(req.results))
    return AgentResponse(ok=True, content=build_markdown(req.results), mode="本地报告模式")



@app.post("/api/report/stream")
def report_stream(req: ReportRequest) -> StreamingResponse:
    if req.use_ai_summary:
        hub = make_hub(req.config)
        return _stream_response(hub.report.stream(req.results))
    return _stream_response(iter([build_markdown(req.results)]))


@app.post("/api/report/markdown")
def report_markdown(req: ReportRequest) -> Response:
    content = build_markdown(req.results)
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=zhilian_tianhe_report.md"},
    )


@app.post("/api/report/txt")
def report_txt(req: ReportRequest) -> Response:
    content = build_markdown(req.results)
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=zhilian_tianhe_report.txt"},
    )


@app.post("/api/report/docx")
def report_docx(req: ReportRequest) -> Response:
    try:
        data = build_docx(req.results)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=zhilian_tianhe_report.docx"},
    )
