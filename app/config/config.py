from dataclasses import dataclass, field
import json
from functools import lru_cache
import logging
import os

from dotenv import load_dotenv


load_dotenv()


def _EnvBool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _LoadToolKeywordMap(path: str) -> dict[str, list[str]]:
    if not path:
        return {}
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {}
        normalized: dict[str, list[str]] = {}
        for key, value in data.items():
            if not isinstance(key, str) or not isinstance(value, list):
                continue
            normalized[key] = [str(item) for item in value if item]
        return normalized
    except (OSError, json.JSONDecodeError):
        return {}

def _NormalizePath(path: str) -> str:
    if not path:
        return ""
    expanded = os.path.expanduser(os.path.expandvars(path.strip()))
    return expanded


def _BuildBaseUrlFromParts() -> str:
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    if base_url:
        return base_url
    host = os.getenv("LLM_HOST", "").strip()
    if not host:
        return ""
    scheme = os.getenv("LLM_SCHEME", "http").strip() or "http"
    port = os.getenv("LLM_PORT", "").strip()
    if port:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")

    model_id: str = os.getenv("MODEL_ID", "")
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
    top_p: float = float(os.getenv("TOP_P", "0.9"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "4096"))
    max_model_len: int = int(os.getenv("MAX_MODEL_LEN", "4096"))
    trust_remote_code: bool = _EnvBool("TRUST_REMOTE_CODE", True)

    llm_base_url: str = _BuildBaseUrlFromParts()
    llm_api_key: str = os.getenv("LLM_API_KEY", "EMPTY")
    llm_timeout_sec: float = float(os.getenv("LLM_TIMEOUT_SEC", "60"))
    llm_tool_fallback_on_400: bool = _EnvBool("LLM_TOOL_FALLBACK_ON_400", True)
    tool_keywords_path: str = os.getenv(
        "TOOL_KEYWORDS_PATH",
        os.path.join(os.path.dirname(__file__), "tool_keywords.json"),
    )
    tool_keywords_map: dict[str, list[str]] = field(
        default_factory=lambda: _LoadToolKeywordMap(
            os.getenv(
                "TOOL_KEYWORDS_PATH",
                os.path.join(os.path.dirname(__file__), "tool_keywords.json"),
            )
        )
    )

    db_backend: str = os.getenv("DB_BACKEND", "")

    oracle_host: str = os.getenv("ORACLE_HOST", "")
    oracle_port: int = int(os.getenv("ORACLE_PORT", "1521") or 1521)
    oracle_user: str = os.getenv("ORACLE_USER", "")
    oracle_password: str = os.getenv("ORACLE_PASSWORD", "")
    oracle_service: str = os.getenv("ORACLE_SERVICE", "")
    oracle_dsn: str = os.getenv("ORACLE_DSN", "")

    users_table: str = os.getenv("USERS_TABLE", "")
    rentals_table: str = os.getenv("RENTALS_TABLE", "")
    payments_table: str = os.getenv("PAYMENTS_TABLE", "")
    bikes_table: str = os.getenv("BIKES_TABLE", "")
    files_table: str = os.getenv("FILES_TABLE", "")
    notices_table: str = os.getenv("NOTICES_TABLE", "")
    inquiries_table: str = os.getenv("INQUIRIES_TABLE", "")
    chat_table: str = os.getenv("CHAT_TABLE", "chat")

    bastion_host: str = os.getenv("BASTION_HOST", "")
    bastion_port: int = int(os.getenv("BASTION_PORT", "22"))
    bastion_user: str = os.getenv("BASTION_USER", "")
    bastion_key_path: str = _NormalizePath(os.getenv("BASTION_KEY_PATH", ""))

    cors_allow_origins: list[str] = field(
        default_factory=lambda: (
            os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
            if os.getenv("CORS_ALLOW_ORIGINS")
            else ["*"]
        )
    )


@lru_cache(maxsize=1)
def GetSettings() -> Settings:
    return Settings()


def ConfigureLogging(settings: Settings) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.info("Booting %s", settings.app_name)
