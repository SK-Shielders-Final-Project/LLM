from fastapi import APIRouter, HTTPException

from app.schemas import (
    AssistantRequest,
    AssistantResponse,
    PriceSummaryRequest,
    SummaryResponse,
    UsageSummaryRequest,
)
from app.services.data_store import get_data_store
from app.services.llm_service import get_llm_service
from app.services.prompt_builder import (
    build_assistant_prompt,
    build_price_summary_prompt,
    build_usage_summary_prompt,
)


router = APIRouter()


@router.post("/v1/summary/price", response_model=SummaryResponse)
def summarize_price(payload: PriceSummaryRequest) -> SummaryResponse:
    data_store = get_data_store()
    pricing = data_store.get_pricing_summary(payload.user_id, payload.period)
    if not pricing:
        raise HTTPException(status_code=404, detail="pricing data not found")

    prompt = build_price_summary_prompt(
        pricing_summary=pricing,
        locale=payload.locale,
    )
    summary = get_llm_service().generate(prompt)

    return SummaryResponse(
        summary=summary,
        data=pricing,
        model_used=get_llm_service().model_id,
    )


@router.post("/v1/summary/usage", response_model=SummaryResponse)
def summarize_usage(payload: UsageSummaryRequest) -> SummaryResponse:
    data_store = get_data_store()
    usage = data_store.get_usage_summary(payload.user_id, payload.period)
    if not usage:
        raise HTTPException(status_code=404, detail="usage data not found")

    prompt = build_usage_summary_prompt(
        usage_summary=usage,
        locale=payload.locale,
    )
    summary = get_llm_service().generate(prompt)

    return SummaryResponse(
        summary=summary,
        data=usage,
        model_used=get_llm_service().model_id,
    )


@router.post("/v1/assistant", response_model=AssistantResponse)
def assistant(payload: AssistantRequest) -> AssistantResponse:
    data_store = get_data_store()
    pricing = {}
    usage = {}

    if payload.include_pricing:
        pricing = data_store.get_pricing_summary(payload.user_id, payload.period)
    if payload.include_usage:
        usage = data_store.get_usage_summary(payload.user_id, payload.period)

    prompt = build_assistant_prompt(
        message=payload.message,
        pricing_summary=pricing,
        usage_summary=usage,
        locale=payload.locale,
    )
    reply = get_llm_service().generate(prompt)

    return AssistantResponse(
        reply=reply,
        data={
            "pricing": pricing,
            "usage": usage,
        },
        model_used=get_llm_service().model_id,
    )
