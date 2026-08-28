# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable, TypeVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import iterate_in_threadpool

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
from zhilian_tianhe_agent.errors import ModelGatewayError  # noqa: E402
from zhilian_tianhe_agent.llm_client import LLMClient, LLMConfig  # noqa: E402

from .body_limit import BodyTooLarge, read_limited_body, replay_body  # noqa: E402
from .limits import ClientConcurrencyLimiter, SlidingWindowRateLimiter  # noqa: E402
from .project_routes import register_project_routes  # noqa: E402
from .schemas import (  # noqa: E402
    APIConfig,
    AgentResponse,
    ContractRequest,
    DefaultsResponse,
    HealthResponse,
    LandingRequest,
    MatchRequest,
    MeetingRequest,
    PolicyRequest,
    ProfileRequest,
    ReportRequest,
)
from .security import (  # noqa: E402
    DEFAULT_CONTENT_SECURITY_POLICY,
    DEFAULT_PERMISSIONS_POLICY,
    apply_security_headers,
    parse_cors_origins,
)
from .service import agent_response, build_docx, build_markdown, make_hub, profile_to_dict  # noqa: E402


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default


def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = _env_int(name, default)
    return max(minimum, min(value, maximum))


APP_VERSION = "2.8.1"
MAX_BODY_BYTES = _env_int("MAX_BODY_BYTES", 1500000)
RATE_LIMIT_REQUESTS = _env_int("RATE_LIMIT_REQUESTS", 30)
RATE_LIMIT_WINDOW_SECONDS = _env_int("RATE_LIMIT_WINDOW_SECONDS", 60)
MAX_CONCURRENT_GENERATIONS_PER_CLIENT = _env_int("MAX_CONCURRENT_GENERATIONS_PER_CLIENT", 1)
MODEL_TEST_TIMEOUT_SECONDS = _bounded_env_int("MODEL_TEST_TIMEOUT_SECONDS", 20, 5, 120)
MODEL_REQUEST_TIMEOUT_SECONDS = _bounded_env_int("MODEL_REQUEST_TIMEOUT_SECONDS", 120, 10, 600)
MODEL_MAX_STREAM_SECONDS = _bounded_env_int("MODEL_MAX_STREAM_SECONDS", max(MODEL_REQUEST_TIMEOUT_SECONDS, 180), 10, 1800)
CLIENT_STREAM_IDLE_TIMEOUT_MS = (MODEL_REQUEST_TIMEOUT_SECONDS + 15) * 1000
CLIENT_STREAM_HARD_TIMEOUT_MS = max(
    (MODEL_MAX_STREAM_SECONDS + 15) * 1000,
    CLIENT_STREAM_IDLE_TIMEOUT_MS + 15_000,
)
TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "").strip().lower() in {"1", "true", "yes", "on"}
ALLOW_WILDCARD_CORS = os.getenv("ALLOW_WILDCARD_CORS", "").strip().lower() in {"1", "true", "yes", "on"}
ENABLE_HSTS = os.getenv("ENABLE_HSTS", "").strip().lower() in {"1", "true", "yes", "on"}
HSTS_MAX_AGE = _env_int("HSTS_MAX_AGE", 31536000)
CONTENT_SECURITY_POLICY = os.getenv("CONTENT_SECURITY_POLICY", DEFAULT_CONTENT_SECURITY_POLICY).strip()
PERMISSIONS_POLICY = os.getenv("PERMISSIONS_POLICY", DEFAULT_PERMISSIONS_POLICY).strip()
FRONTEND_DIR = ROOT / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"

RATE_LIMITER = SlidingWindowRateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)
GENERATION_LIMITER = ClientConcurrencyLimiter(MAX_CONCURRENT_GENERATIONS_PER_CLIENT)
T = TypeVar("T")

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

app = FastAPI(title=APP_FULL_NAME, description=APP_SUBTITLE, version=APP_VERSION)

cors_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
allow_origins = parse_cors_origins(cors_env, allow_wildcard=ALLOW_WILDCARD_CORS)
if allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Workspace-Key"],
        expose_headers=[
            "Retry-After",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Window",
        ],
        max_age=600,
    )

register_project_routes(app)


def _client_key(request: Request) -> str:
    if TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _too_large_response() -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content={"detail": f"请求内容过大，请脱敏并精简到 {MAX_BODY_BYTES // 1024}KB 以内后再提交。"},
    )


def _rate_limited_response(retry_after: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "请求过于频繁，请稍后再试。"},
        headers={"Retry-After": str(retry_after)},
    )


@app.middleware("http")
async def guard_requests(request: Request, call_next):
    is_write = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    has_body = request.method in {"POST", "PUT", "PATCH"}
    is_api_write = is_write and request.url.path.startswith("/api/")
    rate_decision = None

    if is_api_write:
        rate_decision = RATE_LIMITER.check(_client_key(request))
        if not rate_decision.allowed:
            return _rate_limited_response(rate_decision.retry_after)

    if has_body:
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_BODY_BYTES:
            return _too_large_response()
        upstream_receive = request.receive
        try:
            body = await read_limited_body(upstream_receive, MAX_BODY_BYTES)
        except BodyTooLarge:
            return _too_large_response()
        request._receive = replay_body(body, upstream_receive)

    response = await call_next(request)
    if rate_decision is not None and RATE_LIMIT_REQUESTS > 0:
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(rate_decision.remaining)
        response.headers["X-RateLimit-Window"] = str(RATE_LIMIT_WINDOW_SECONDS)
    return response


@app.middleware("http")
async def secure_responses(request: Request, call_next):
    response = await call_next(request)
    return apply_security_headers(
        response,
        path=request.url.path,
        content_security_policy=CONTENT_SECURITY_POLICY,
        permissions_policy=PERMISSIONS_POLICY,
        enable_hsts=ENABLE_HSTS,
        hsts_max_age=HSTS_MAX_AGE,
    )


@app.exception_handler(ModelGatewayError)
async def model_gateway_error_handler(request: Request, exc: ModelGatewayError):  # noqa: ARG001
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after is not None else None
    return JSONResponse(status_code=exc.status_code, content=exc.to_payload(), headers=headers)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):  # noqa: ARG001
    return JSONResponse(
        status_code=500,
        content={"detail": "服务处理过程中发生异常，请稍后重试。", "code": "INTERNAL_RUNTIME_ERROR", "retryable": True},
    )


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
    return DefaultsResponse(provider_presets=PROVIDER_PRESETS, modules=MODULES, disclaimer=LEGAL_DISCLAIMER)


def _acquire_generation(request: Request) -> str:
    key = _client_key(request)
    if not GENERATION_LIMITER.try_acquire(key):
        raise HTTPException(
            status_code=429,
            detail="当前已有生成任务正在运行，请等待完成或取消后再试。",
            headers={"Retry-After": "2"},
        )
    return key


def _run_generation(request: Request, callback: Callable[[], T]) -> T:
    key = _acquire_generation(request)
    try:
        return callback()
    finally:
        GENERATION_LIMITER.release(key)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_meta(*, provisional: bool = False) -> dict:
    return {
        "type": "meta",
        "mode": "AI模型流式模式",
        "provisional": provisional,
        "idle_timeout_ms": CLIENT_STREAM_IDLE_TIMEOUT_MS,
        "hard_timeout_ms": CLIENT_STREAM_HARD_TIMEOUT_MS,
    }


def _stream_error_payload(exc: Exception) -> dict:
    if isinstance(exc, ModelGatewayError):
        payload = {"type": "error", "error": exc.user_message, "code": exc.code, "retryable": exc.retryable}
        if exc.retry_after is not None:
            payload["retry_after"] = exc.retry_after
        return payload
    return {"type": "error", "error": "生成过程中发生异常，请稍后重试。", "code": "STREAM_INTERNAL_ERROR", "retryable": True}


def _cleanup_stream(iterator, cancel_callback: Callable[[], None] | None = None) -> None:
    # Close the upstream socket before closing the Python iterator. This allows a
    # browser AbortController cancellation to interrupt a requests/urllib3 read that
    # is currently running in Starlette's worker thread.
    if cancel_callback is not None:
        try:
            cancel_callback()
        except Exception:  # noqa: BLE001
            pass
    close = getattr(iterator, "close", None)
    if callable(close):
        try:
            close()
        except Exception:  # noqa: BLE001
            pass


def _stream_response(
    chunks,
    *,
    release_key: str | None = None,
    cancel_callback: Callable[[], None] | None = None,
) -> StreamingResponse:
    """Forward model deltas without duplicating the completed result in server memory."""

    async def event_generator():
        iterator = iter(chunks)
        try:
            yield _sse(_stream_meta())
            async for chunk in iterate_in_threadpool(iterator):
                if chunk:
                    yield _sse({"type": "delta", "content": chunk})
            # The browser already owns the assembled deltas; avoid a second full copy here.
            yield _sse({"type": "done", "content": "", "mode": "AI模型流式模式"})
        except Exception as exc:  # noqa: BLE001
            yield _sse(_stream_error_payload(exc))
        finally:
            _cleanup_stream(iterator, cancel_callback)
            if release_key is not None:
                GENERATION_LIMITER.release(release_key)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


def _verified_stream_response(
    events,
    *,
    release_key: str | None = None,
    cancel_callback: Callable[[], None] | None = None,
) -> StreamingResponse:
    """Stream provisional model text, then deliver one trusted verified replacement."""

    async def event_generator():
        iterator = iter(events)
        verified = False
        final_mode = "AI模型流式模式（已校验）"
        try:
            yield _sse(_stream_meta(provisional=True))
            async for event in iterate_in_threadpool(iterator):
                event_type = getattr(event, "type", "")
                if event_type == "delta":
                    content = getattr(event, "content", "")
                    if content:
                        yield _sse({"type": "delta", "content": content, "provisional": True})
                elif event_type == "verifying":
                    yield _sse({"type": "verifying", "message": "AI 草稿已生成，正在进行事实与规则校验。"})
                elif event_type == "verified":
                    content = getattr(event, "content", "")
                    if not content:
                        raise ModelGatewayError(
                            "STREAM_VERIFICATION_EMPTY",
                            "结果校验完成但没有可用内容，请重新生成。",
                            502,
                            True,
                        )
                    verified = True
                    final_mode = getattr(event, "mode", "") or final_mode
                    yield _sse({"type": "verified", "content": content, "mode": final_mode})
                else:
                    raise ModelGatewayError(
                        "STREAM_EVENT_INVALID",
                        "生成流程返回了无法识别的事件，请稍后重试。",
                        502,
                        True,
                    )

            if not verified:
                raise ModelGatewayError(
                    "STREAM_VERIFICATION_MISSING",
                    "生成已结束，但事实校验未完成；本次草稿不会保存，请重新生成。",
                    502,
                    True,
                )
            yield _sse({"type": "done", "content": "", "mode": final_mode})
        except Exception as exc:  # noqa: BLE001
            yield _sse(_stream_error_payload(exc))
        finally:
            _cleanup_stream(iterator, cancel_callback)
            if release_key is not None:
                GENERATION_LIMITER.release(release_key)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


def _start_generation_stream(
    request: Request,
    chunks_factory: Callable[[], object],
    *,
    cancel_callback: Callable[[], None] | None = None,
) -> StreamingResponse:
    key = _acquire_generation(request)
    try:
        chunks = chunks_factory()
    except Exception:
        GENERATION_LIMITER.release(key)
        raise
    return _stream_response(chunks, release_key=key, cancel_callback=cancel_callback)


def _start_verified_generation_stream(
    request: Request,
    events_factory: Callable[[], object],
    *,
    cancel_callback: Callable[[], None] | None = None,
) -> StreamingResponse:
    key = _acquire_generation(request)
    try:
        events = events_factory()
    except Exception:
        GENERATION_LIMITER.release(key)
        raise
    return _verified_stream_response(events, release_key=key, cancel_callback=cancel_callback)


@app.post("/api/test-connection", response_model=AgentResponse)
def test_connection(config: APIConfig, request: Request) -> AgentResponse:
    def execute() -> AgentResponse:
        try:
            client = LLMClient(
                LLMConfig(
                    api_key=config.api_key.strip(),
                    base_url=config.base_url.strip(),
                    model=config.model.strip(),
                    temperature=config.temperature,
                    timeout=MODEL_TEST_TIMEOUT_SECONDS,
                )
            )
            content = client.chat("你是接口连通性测试助手。", "请只回复：连接成功")
            return AgentResponse(ok=True, content=content, mode="AI模型模式")
        except ModelGatewayError as exc:
            return AgentResponse(
                ok=False,
                mode="连接失败",
                error=exc.user_message,
                error_code=exc.code,
                retryable=exc.retryable,
                retry_after=exc.retry_after,
            )
        except Exception:  # noqa: BLE001
            return AgentResponse(ok=False, mode="连接失败", error="连接测试发生异常，请检查配置后重试。", error_code="MODEL_TEST_FAILED", retryable=True)

    return _run_generation(request, execute)


@app.post("/api/profile", response_model=AgentResponse)
def profile(req: ProfileRequest, request: Request) -> AgentResponse:
    return _run_generation(request, lambda: agent_response(make_hub(req.config).profile.run(profile_to_dict(req.profile))))


@app.post("/api/profile/stream")
def profile_stream(req: ProfileRequest, request: Request) -> StreamingResponse:
    hub = make_hub(req.config)
    return _start_generation_stream(
        request,
        lambda: hub.profile.stream(profile_to_dict(req.profile)),
        cancel_callback=hub.llm.cancel_active_requests,
    )


@app.post("/api/meeting", response_model=AgentResponse)
def meeting(req: MeetingRequest, request: Request) -> AgentResponse:
    if len(req.text.strip()) < 8:
        raise HTTPException(status_code=400, detail="会议内容过短，请补充会议背景、结论或待办事项。")
    return _run_generation(request, lambda: agent_response(make_hub(req.config).meeting.run(req.text, req.profile_summary)))


@app.post("/api/meeting/stream")
def meeting_stream(req: MeetingRequest, request: Request) -> StreamingResponse:
    if len(req.text.strip()) < 8:
        raise HTTPException(status_code=400, detail="会议内容过短，请补充会议背景、结论或待办事项。")
    hub = make_hub(req.config)
    return _start_verified_generation_stream(
        request,
        lambda: hub.meeting.stream_events(req.text, req.profile_summary),
        cancel_callback=hub.llm.cancel_active_requests,
    )


@app.post("/api/contract", response_model=AgentResponse)
def contract(req: ContractRequest, request: Request) -> AgentResponse:
    if len(req.text.strip()) < 12:
        raise HTTPException(status_code=400, detail="合同文本过短，请粘贴关键条款后再生成风险提示。")
    return _run_generation(request, lambda: agent_response(make_hub(req.config).contract.run(req.text, req.profile_summary)))


@app.post("/api/contract/stream")
def contract_stream(req: ContractRequest, request: Request) -> StreamingResponse:
    if len(req.text.strip()) < 12:
        raise HTTPException(status_code=400, detail="合同文本过短，请粘贴关键条款后再生成风险提示。")
    hub = make_hub(req.config)
    return _start_verified_generation_stream(
        request,
        lambda: hub.contract.stream_events(req.text, req.profile_summary),
        cancel_callback=hub.llm.cancel_active_requests,
    )


@app.post("/api/policy", response_model=AgentResponse)
def policy(req: PolicyRequest, request: Request) -> AgentResponse:
    return _run_generation(request, lambda: agent_response(make_hub(req.config).policy.run(profile_to_dict(req.profile), req.demand)))


@app.post("/api/policy/stream")
def policy_stream(req: PolicyRequest, request: Request) -> StreamingResponse:
    hub = make_hub(req.config)
    return _start_generation_stream(
        request,
        lambda: hub.policy.stream(profile_to_dict(req.profile), req.demand),
        cancel_callback=hub.llm.cancel_active_requests,
    )


@app.post("/api/match", response_model=AgentResponse)
def match(req: MatchRequest, request: Request) -> AgentResponse:
    if not any([req.offer.strip(), req.need.strip(), req.target.strip(), req.scenario.strip()]):
        raise HTTPException(status_code=400, detail="请至少填写供给、需求、目标对象或业务场景中的一项。")
    return _run_generation(
        request,
        lambda: agent_response(make_hub(req.config).match.run(profile_to_dict(req.profile), req.offer, req.need, req.target, req.scenario)),
    )


@app.post("/api/match/stream")
def match_stream(req: MatchRequest, request: Request) -> StreamingResponse:
    if not any([req.offer.strip(), req.need.strip(), req.target.strip(), req.scenario.strip()]):
        raise HTTPException(status_code=400, detail="请至少填写供给、需求、目标对象或业务场景中的一项。")
    hub = make_hub(req.config)
    return _start_generation_stream(
        request,
        lambda: hub.match.stream(profile_to_dict(req.profile), req.offer, req.need, req.target, req.scenario),
        cancel_callback=hub.llm.cancel_active_requests,
    )


@app.post("/api/landing", response_model=AgentResponse)
def landing(req: LandingRequest, request: Request) -> AgentResponse:
    return _run_generation(
        request,
        lambda: agent_response(make_hub(req.config).landing.run(profile_to_dict(req.profile), req.landing_info, req.existing_results)),
    )


@app.post("/api/landing/stream")
def landing_stream(req: LandingRequest, request: Request) -> StreamingResponse:
    hub = make_hub(req.config)
    return _start_generation_stream(
        request,
        lambda: hub.landing.stream(profile_to_dict(req.profile), req.landing_info, req.existing_results),
        cancel_callback=hub.llm.cancel_active_requests,
    )


@app.post("/api/report", response_model=AgentResponse)
def report(req: ReportRequest, request: Request) -> AgentResponse:
    if req.use_ai_summary:
        return _run_generation(request, lambda: agent_response(make_hub(req.config).report.run(req.results)))
    return AgentResponse(ok=True, content=build_markdown(req.results), mode="本地报告模式")


@app.post("/api/report/stream")
def report_stream(req: ReportRequest, request: Request) -> StreamingResponse:
    if req.use_ai_summary:
        hub = make_hub(req.config)
        return _start_generation_stream(
            request,
            lambda: hub.report.stream(req.results),
            cancel_callback=hub.llm.cancel_active_requests,
        )
    return _stream_response(iter([build_markdown(req.results)]))


@app.post("/api/report/markdown")
def report_markdown(req: ReportRequest) -> Response:
    return Response(
        content=build_markdown(req.results),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=zhilian_tianhe_report.md"},
    )


@app.post("/api/report/txt")
def report_txt(req: ReportRequest) -> Response:
    return Response(
        content=build_markdown(req.results),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=zhilian_tianhe_report.txt"},
    )


@app.post("/api/report/docx")
def report_docx(req: ReportRequest) -> Response:
    try:
        data = build_docx(req.results)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Word 报告生成失败，请稍后重试。") from exc
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=zhilian_tianhe_report.docx"},
    )
