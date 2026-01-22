from pydantic import BaseModel, Field


class PriceSummaryRequest(BaseModel):
    user_id: str = Field(..., examples=["user_001"])
    period: str = Field(..., examples=["2025-12"])
    locale: str = Field("ko-KR", examples=["ko-KR"])


class UsageSummaryRequest(BaseModel):
    user_id: str = Field(..., examples=["user_001"])
    period: str = Field(..., examples=["2025-12"])
    locale: str = Field("ko-KR", examples=["ko-KR"])


class AssistantRequest(BaseModel):
    user_id: str = Field(..., examples=["user_001"])
    period: str = Field("2025-12", examples=["2025-12"])
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
