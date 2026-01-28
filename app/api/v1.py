from __future__ import annotations

from fastapi import APIRouter, HTTPException
import requests

from app.core.llm_service import GetLlmService
from app.schemas import AssistantRequest, AssistantResponse, LlmMessage
from app.services.tool_executor import ExecuteToolCall

router = APIRouter()


def _ValidateMessage(message: LlmMessage) -> None:
    if message.role != "user":
        raise HTTPException(status_code=400, detail="message.role must be user")
    if not message.content.strip():
        raise HTTPException(status_code=400, detail="message.content is required")
    if message.user_id <= 0:
        raise HTTPException(status_code=400, detail="message.user_id must be positive")


def _GenerateResponse(payload: AssistantRequest) -> AssistantResponse:
    message = payload.message
    _ValidateMessage(message)

    service = GetLlmService()
    try:
        reply = service.GenerateAssistantReply(message, ExecuteToolCall)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM 서버 연결 실패: {exc.__class__.__name__}",
        ) from exc
    return AssistantResponse(text=reply, model=service.model_id)


@router.post("/generate", response_model=AssistantResponse)
def Generate(payload: AssistantRequest) -> AssistantResponse:
    return _GenerateResponse(payload)
