from typing import Optional

from pydantic import BaseModel, Field


class PriceSummaryRequest(BaseModel):
    user_id: str = Field(..., examples=["1"])


class UsageSummaryRequest(BaseModel):
    user_id: str = Field(..., examples=["1"])


class AssistantRequest(BaseModel):
    user_id: str = Field(..., examples=["1"])
    period: Optional[str] = Field(None, examples=["2025-12"])
    message: str = Field(..., examples=["이번 달 사용 요약해줘"])
    locale: str = Field("ko-KR", examples=["ko-KR"])
    include_pricing: bool = True
    include_usage: bool = True


class SummaryResponse(BaseModel):
    summary: str
    data: dict
    model_used: str


class AssistantResponse(BaseModel):
    reply: str
    data: dict
    model_used: str
