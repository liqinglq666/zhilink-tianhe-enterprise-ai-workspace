# -*- coding: utf-8 -*-
"""Deterministic Markdown-to-JSON conversion endpoints."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from zhilian_tianhe_agent.structured_output import StructuredModule, StructuredResult, structure_markdown

router = APIRouter(prefix="/api/structured", tags=["structured-results"])


class StructuredConvertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    module: StructuredModule
    content: str = Field(min_length=1, max_length=80000)


@router.post("/convert", response_model=StructuredResult)
def convert_structured_result(payload: StructuredConvertRequest) -> StructuredResult:
    return structure_markdown(payload.module, payload.content)


@router.get("/schema")
def structured_result_schema() -> dict:
    """Expose the exact schema so external clients can validate stored JSON."""
    return StructuredResult.model_json_schema()


def register_structured_routes(app: FastAPI) -> None:
    app.include_router(router)
