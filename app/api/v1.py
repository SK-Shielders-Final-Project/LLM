from fastapi import APIRouter, HTTPException

from app.schemas import (
    AssistantRequest,
    AssistantResponse,
    PriceSummaryRequest,
    SummaryResponse,
    UsageSummaryRequest,
)
from app.services.data_store import GetDataStore
from app.services.llm_service import GetLlmService
from app.services.prompt_builder import (
    BuildAssistantPrompt,
    BuildPriceSummaryPrompt,
    BuildUsageSummaryPrompt,
)


router = APIRouter()


@router.post("/v1/summary/price", response_model=SummaryResponse)
def SummarizePrice(payload: PriceSummaryRequest) -> SummaryResponse:
    data_store = GetDataStore()
    pricing = data_store.GetPricingSummary(payload.user_id, None)
    if not pricing:
        raise HTTPException(status_code=404, detail="pricing data not found")

    prompt = BuildPriceSummaryPrompt(
        pricing_summary=pricing,
        locale="ko-KR",
    )
    summary = GetLlmService().Generate(prompt)

    return SummaryResponse(
        summary=summary,
        data=pricing,
        model_used=GetLlmService().model_id,
    )


@router.post("/v1/summary/usage", response_model=SummaryResponse)
def SummarizeUsage(payload: UsageSummaryRequest) -> SummaryResponse:
    data_store = GetDataStore()
    usage = data_store.GetUsageSummary(payload.user_id, None)
    if not usage:
        raise HTTPException(status_code=404, detail="usage data not found")

    prompt = BuildUsageSummaryPrompt(
        usage_summary=usage,
        locale="ko-KR",
    )
    summary = GetLlmService().Generate(prompt)

    return SummaryResponse(
        summary=summary,
        data=usage,
        model_used=GetLlmService().model_id,
    )


@router.post("/v1/assistant", response_model=AssistantResponse)
def Assistant(payload: AssistantRequest) -> AssistantResponse:
    data_store = GetDataStore()
    pricing = {}
    usage = {}

    if payload.include_pricing:
        pricing = data_store.GetPricingSummary(payload.user_id, payload.period)
    if payload.include_usage:
        usage = data_store.GetUsageSummary(payload.user_id, payload.period)

    prompt = BuildAssistantPrompt(
        message=payload.message,
        pricing_summary=pricing,
        usage_summary=usage,
        locale=payload.locale,
    )
    reply = GetLlmService().Generate(prompt)

    return AssistantResponse(
        reply=reply,
        data={
            "pricing": pricing,
            "usage": usage,
        },
        model_used=GetLlmService().model_id,
    )
