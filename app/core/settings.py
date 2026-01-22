from dataclasses import dataclass, field
from functools import lru_cache
import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


## dotENV에서 변수명 가져오기
@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "LLM-SecLab Scooter Assistant")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")

    model_id: str = os.getenv("MODEL_ID", "yanolja/YanoljaNEXT-EEVE-10.8B")
    temperature: float = float(os.getenv("TEMPERATURE", "0.3"))
    top_p: float = float(os.getenv("TOP_P", "0.9"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "512"))
    trust_remote_code: bool = _env_bool("TRUST_REMOTE_CODE", True)

    use_mock_llm: bool = _env_bool("USE_MOCK_LLM", True)
    use_mock_data: bool = _env_bool("USE_MOCK_DATA", True)
    sandbox_mode: bool = _env_bool("SANDBOX_MODE", True)

    aws_region: str = os.getenv("AWS_REGION", "ap-northeast-2")
    pricing_table: str = os.getenv("PRICING_TABLE", "scooter_pricing_summary")
    usage_table: str = os.getenv("USAGE_TABLE", "scooter_usage_summary")

    cors_allow_origins: list[str] = field(
        default_factory=lambda: (
            os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
            if os.getenv("CORS_ALLOW_ORIGINS")
            else ["*"]
        )
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
