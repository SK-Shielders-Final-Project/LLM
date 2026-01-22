from app.core.settings import get_settings
from app.services.llm_service import get_llm_service
from app.services.prompt_builder import build_assistant_prompt
from app.services.data_store import MockDataStore


def main() -> None:
    settings = get_settings()
    data_store = MockDataStore()
    pricing = data_store.get_pricing_summary(user_id="user_001", period="2025-12")
    usage = data_store.get_usage_summary(user_id="user_001", period="2025-12")

    prompt = build_assistant_prompt(
        message="지난달 요금과 사용 패턴을 요약하고, 절약 팁을 알려줘.",
        pricing_summary=pricing,
        usage_summary=usage,
        locale="ko-KR",
    )
    response = get_llm_service().generate(prompt)

    print(f"Model: {settings.model_id}")
    print(response)


if __name__ == "__main__":
    main()
