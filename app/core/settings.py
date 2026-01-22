from dataclasses import dataclass, field
from functools import lru_cache
import os

from dotenv import load_dotenv


load_dotenv()


def _EnvBool(name: str, default: bool) -> bool:
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
    trust_remote_code: bool = _EnvBool("TRUST_REMOTE_CODE", True)

    db_backend: str = os.getenv("DB_BACKEND", "mysql")

    mysql_host: str = os.getenv("MYSQL_HOST", "")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "")

    users_table: str = os.getenv("USERS_TABLE", "users")
    rentals_table: str = os.getenv("RENTALS_TABLE", "rentals")
    payments_table: str = os.getenv("PAYMENTS_TABLE", "payments")
    bikes_table: str = os.getenv("BIKES_TABLE", "bikes")

    bastion_host: str = os.getenv("BASTION_HOST", "")
    bastion_port: int = int(os.getenv("BASTION_PORT", "22"))
    bastion_user: str = os.getenv("BASTION_USER", "")
    bastion_key_path: str = os.getenv("BASTION_KEY_PATH", "")

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
