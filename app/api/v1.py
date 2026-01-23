import json

from fastapi import APIRouter, HTTPException

from app.core.llm_service import GetLlmService
from app.schemas import AssistantRequest, AssistantResponse, LlmMessage
from app.services.data_store import GetDataStore

router = APIRouter()

SYSTEM_PROMPT = (
    "당신은 한국어로 친절하고 간결하게 답변하는 챗봇입니다. "
    "모든 답변은 반드시 한국어로만 작성하세요. "
    "password와 card_number는 절대로 노출하지 마세요."
)


def _AsJson(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _Normalize(text: str) -> str:
    return text.strip().lower().replace(" ", "")

## 사용 가능한 자전거 정보
def _FormatAvailableBikes(bikes: list[dict]) -> str:
    if not bikes:
        return "현재 사용 가능한 자전거가 없습니다."
    lines = ["현재 사용 가능한 자전거입니다."]
    for idx, bike in enumerate(bikes, start=1):
        bike_id = bike.get("bike_id", "-")
        lat = bike.get("latitude", "-")
        lon = bike.get("longitude", "-")
        lines.append(f"Bike {idx} (ID: {bike_id})")
        lines.append(f"위치 정보: {lat}, {lon}")
    return "\n".join(lines)

## 결제 내역역
def _FormatPayments(payments: list[dict]) -> str:
    if not payments:
        return "결제 내역이 없습니다."
    lines = ["결제 내역입니다."]
    for idx, payment in enumerate(payments, start=1):
        username = payment.get("username", "-")
        amount = payment.get("amount", "-")
        status = payment.get("payment_status", "-")
        method = payment.get("payment_method", "-")
        created_at = payment.get("created_at", "-")
        lines.append(
            f"{idx}. 사용자: {username}, 금액: {amount}원, 상태: {status}, "
            f"수단: {method}, 일시: {created_at}"
        )
    return "\n".join(lines)

## 사용 내역역
def _FormatUsageHistory(rows: list[dict]) -> str:
    if not rows:
        return "사용 내역이 없습니다."
    lines = ["사용 내역입니다."]
    for idx, row in enumerate(rows, start=1):
        username = row.get("username", "-")
        bike_id = row.get("bike_id", "-")
        start_time = row.get("start_time", "-")
        end_time = row.get("end_time", "-")
        total_distance = row.get("total_distance", "-")
        total_amount = row.get("amount", "-")
        lines.append(
            f"{idx}. 사용자: {username}, 자전거: {bike_id}, "
            f"이용 시간: {start_time} ~ {end_time}, "
            f"총 거리: {total_distance}"
            f"총 가격: {total_amount}"
        )
    return "\n".join(lines)


## 전체 시스템 프롬프트 생성
def _BuildSystemContext(message: LlmMessage) -> str:
    data_store = GetDataStore()
    user_id = str(message.user_id)
    user_profile = data_store.GetUserProfile(user_id)
    pricing_summary = data_store.GetPricingSummary(user_id, None)
    usage_summary = data_store.GetUsageSummary(user_id, None)
    return (
        f"{SYSTEM_PROMPT}\n"
        f"UserId: {user_id}\n"
        "Locale: ko\n"
        f"UserProfile:\n{_AsJson(user_profile)}\n"
        f"PricingData:\n{_AsJson(pricing_summary)}\n"
        f"UsageData:\n{_AsJson(usage_summary)}"
    )


def _GenerateResponse(payload: AssistantRequest) -> AssistantResponse:
    message = payload.message
    if message.role != "user":
        raise HTTPException(status_code=400, detail="message.role must be user")
    if not message.content.strip():
        raise HTTPException(status_code=400, detail="message.content is required")
    if message.user_id <= 0:
        raise HTTPException(status_code=400, detail="message.user_id must be positive")

    content = message.content.strip()
    normalized = _Normalize(content)
    data_store = GetDataStore()
    user_id = str(message.user_id)

    if "자전거" in normalized and ("사용가능" in normalized or "대여가능" in normalized):
        bikes = data_store.GetAvailableBikes(limit=20)
        reply = _FormatAvailableBikes(bikes)
        return AssistantResponse(text=reply, model=GetLlmService().model_id)

    if "결제" in normalized or "결재" in normalized:
        payments = data_store.GetPayments(user_id=user_id, limit=20)
        reply = _FormatPayments(payments)
        return AssistantResponse(text=reply, model=GetLlmService().model_id)

    if "사용내역" in normalized or "이용내역" in normalized:
        useage = data_store.GetRentals(user_id=user_id, limit=20)
        reply = _FormatUsageHistory(useage)
        return AssistantResponse(text=reply, model=GetLlmService().model_id)

    llm_messages = [
        {"role": "system", "content": _BuildSystemContext(message)},
        {"role": message.role, "content": message.content},
    ]
    reply = GetLlmService().GenerateChat(llm_messages)
    return AssistantResponse(text=reply, model=GetLlmService().model_id)


@router.post("/generate", response_model=AssistantResponse)
def Generate(payload: AssistantRequest) -> AssistantResponse:
    return _GenerateResponse(payload)