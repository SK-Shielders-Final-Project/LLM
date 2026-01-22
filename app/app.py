from app.core.settings import GetSettings
from app.services.llm_service import GetLlmService
from app.services.prompt_builder import BuildAssistantPrompt
from app.services.data_store import GetDataStore


def Main() -> None:
    ## SandBox 권한에서 가져오는 함수들
    settings = GetSettings()
    data_store = GetDataStore()

    ## 실제 DB Connection 넣어서 DB 정보를 가져와야함.
    pricing = data_store.GetPricingSummary(user_id="user_001", period="2025-12")
    usage = data_store.GetUsageSummary(user_id="user_001", period="2025-12")

    ## 실제 main에서 작성하는 프롬프트
    prompt = BuildAssistantPrompt(
        message="지난달 요금과 사용 패턴을 요약하고, 절약 팁을 알려줘.",
        pricing_summary=pricing,
        usage_summary=usage,
        locale="ko-KR",
    )
    response = GetLlmService().Generate(prompt) #LLM 답변을 전송함.

    print(f"Model: {settings.model_id}")
    print(response)


if __name__ == "__main__":
    Main()
