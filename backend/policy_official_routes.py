# -*- coding: utf-8 -*-
"""Official-policy search and grounded generation endpoints."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import iterate_in_threadpool

from zhilian_tianhe_agent.errors import ModelGatewayError
from zhilian_tianhe_agent.official_policy import OfficialPolicyAgent
from zhilian_tianhe_agent.policy_quality import refine_policy_retrieval
from zhilian_tianhe_agent.policy_retrieval import OfficialPolicyRetrieval, get_official_policy_retriever

from .limits import ClientConcurrencyLimiter
from .schemas import APIConfig, ProfileData
from .service import make_hub, profile_to_dict

router = APIRouter(prefix="/api/policy/official", tags=["official-policy"])
MAX_POLICY_CONCURRENCY = max(1, int(os.getenv("MAX_CONCURRENT_GENERATIONS_PER_CLIENT", "1") or "1"))
MAX_POLICY_SEARCH_CONCURRENCY = max(1, int(os.getenv("MAX_CONCURRENT_POLICY_SEARCHES_PER_CLIENT", "1") or "1"))
TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "").strip().lower() in {"1", "true", "yes", "on"}
POLICY_GENERATION_LIMITER = ClientConcurrencyLimiter(MAX_POLICY_CONCURRENCY)
POLICY_SEARCH_LIMITER = ClientConcurrencyLimiter(MAX_POLICY_SEARCH_CONCURRENCY)
POLICY_MODE = "AI模型流式模式（官方候选来源与人工核验）"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OfficialPolicySearchRequest(StrictModel):
    profile: ProfileData = Field(default_factory=ProfileData)
    demand: str = Field(default="", max_length=20000)
    query: str = Field(default="", max_length=2000)
    limit: int = Field(default=6, ge=1, le=12)


class OfficialPolicyGenerateRequest(StrictModel):
    config: APIConfig = Field(default_factory=APIConfig)
    profile: ProfileData = Field(default_factory=ProfileData)
    demand: str = Field(default="", max_length=20000)


class OfficialPolicyGenerateResponse(StrictModel):
    ok: bool = True
    content: str = Field(max_length=120000)
    mode: str = Field(max_length=200)
    retrieval: OfficialPolicyRetrieval


def _client_key(request: Request) -> str:
    if TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _acquire(limiter: ClientConcurrencyLimiter, request: Request, message: str) -> str:
    key = _client_key(request)
    if not limiter.try_acquire(key):
        raise HTTPException(status_code=429, detail=message, headers={"Retry-After": "2"})
    return key


def _sse(data: Dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/search", response_model=OfficialPolicyRetrieval)
def search_official_policy(payload: OfficialPolicySearchRequest, request: Request) -> OfficialPolicyRetrieval:
    key = _acquire(POLICY_SEARCH_LIMITER, request, "当前已有政策检索任务正在运行，请稍后再试。")
    try:
        profile = profile_to_dict(payload.profile)
        raw = get_official_policy_retriever().search(
            profile,
            payload.demand,
            query=payload.query,
            limit=payload.limit,
        )
        return refine_policy_retrieval(raw, profile, payload.demand)
    finally:
        POLICY_SEARCH_LIMITER.release(key)


@router.post("", response_model=OfficialPolicyGenerateResponse)
def generate_official_policy(payload: OfficialPolicyGenerateRequest, request: Request) -> OfficialPolicyGenerateResponse:
    key = _acquire(POLICY_GENERATION_LIMITER, request, "当前已有政策生成任务正在运行，请等待完成或取消后再试。")
    try:
        hub = make_hub(payload.config)
        agent = OfficialPolicyAgent(hub.llm, get_official_policy_retriever())
        result = agent.run(profile_to_dict(payload.profile), payload.demand)
        return OfficialPolicyGenerateResponse(content=result.content, mode=result.mode, retrieval=result.retrieval)
    finally:
        POLICY_GENERATION_LIMITER.release(key)


@router.post("/stream")
def stream_official_policy(payload: OfficialPolicyGenerateRequest, request: Request) -> StreamingResponse:
    key = _acquire(POLICY_GENERATION_LIMITER, request, "当前已有政策生成任务正在运行，请等待完成或取消后再试。")
    try:
        hub = make_hub(payload.config)
        agent = OfficialPolicyAgent(hub.llm, get_official_policy_retriever())
        chunks, prepared = agent.stream(profile_to_dict(payload.profile), payload.demand)
    except Exception:
        POLICY_GENERATION_LIMITER.release(key)
        raise

    async def event_generator():
        iterator = iter(chunks)
        try:
            yield _sse({
                "type": "meta",
                "mode": POLICY_MODE,
                "retrieval": prepared.retrieval.model_dump(mode="json"),
            })
            async for chunk in iterate_in_threadpool(iterator):
                if chunk:
                    yield _sse({"type": "delta", "content": chunk})
            yield _sse({
                "type": "done",
                "content": "",
                "mode": POLICY_MODE,
                "retrieval": prepared.retrieval.model_dump(mode="json"),
            })
        except ModelGatewayError as exc:
            payload_data: dict[str, Any] = {
                "type": "error",
                "error": exc.user_message,
                "code": exc.code,
                "retryable": exc.retryable,
            }
            if exc.retry_after is not None:
                payload_data["retry_after"] = exc.retry_after
            yield _sse(payload_data)
        except Exception:  # noqa: BLE001
            yield _sse({
                "type": "error",
                "error": "官方政策分析过程中发生异常，请稍后重试。",
                "code": "POLICY_STREAM_INTERNAL_ERROR",
                "retryable": True,
            })
        finally:
            close = getattr(iterator, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001
                    pass
            POLICY_GENERATION_LIMITER.release(key)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


def register_official_policy_routes(app: FastAPI) -> None:
    app.include_router(router)
