import json

from fastapi import APIRouter, HTTPException

from app.schemas import AssistantRequest, AssistantResponse, LlmMessage
from app.core.llm_service import GetLlmService
from app.services.data_store import GetDataStore


router = APIRouter()

DEFAULT_SYSTEM_MESSAGE = (
    "당신은 한국어로 친절하고 간결하게 답변하는 챗봇입니다. "
    "모든 답변은 반드시 한국어로만 작성하세요."
)

def _ValidateMessage(message: LlmMessage) -> None:
    if message.role != "user":
        raise HTTPException(status_code=400, detail="message.role must be user")
    if not message.content.strip():
        raise HTTPException(status_code=400, detail="message.content is required")
    if message.user_id <= 0:
        raise HTTPException(status_code=400, detail="message.user_id must be positive")


def _AsJson(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _GenerateResponse(payload: AssistantRequest) -> AssistantResponse:
    _ValidateMessage(payload.message)
    data_store = GetDataStore()
    user_id = str(payload.message.user_id)
    pricing_summary = data_store.GetPricingSummary(user_id, None)
    usage_summary = data_store.GetUsageSummary(user_id, None)
    system_context = (
        f"{DEFAULT_SYSTEM_MESSAGE}\n"
        f"UserId: {user_id}\n"
        "Locale: ko\n"
        f"PricingData:\n{_AsJson(pricing_summary)}\n"
        f"UsageData:\n{_AsJson(usage_summary)}"
    )
    llm_messages = [
        {
            "role": "system",
            "content": system_context,
        },
        {
            "role": payload.message.role,
            "content": payload.message.content,
        }
    ]
    reply = GetLlmService().GenerateChat(llm_messages)
    return AssistantResponse(
        text=reply,
        model=GetLlmService().model_id,
    )


@router.post("/generate", response_model=AssistantResponse)
def Generate(payload: AssistantRequest) -> AssistantResponse:
    return _GenerateResponse(payload)


@router.post("/v1/assistant", response_model=AssistantResponse)
def Assistant(payload: AssistantRequest) -> AssistantResponse:
    return _GenerateResponse(payload)