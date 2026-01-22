from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from app.core.settings import get_settings


@dataclass
class LLMResponse:
    text: str


class MockLLM:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id

    def generate(self, prompt: str) -> str:
        return (
            "현재는 SANDBOX 모드입니다. 실제 모델 호출 없이 응답을 모의 생성합니다.\n"
            "요약: 지난달 사용량/요금 패턴이 안정적이며 출퇴근 시간대 이용이 많습니다.\n"
            "팁: 정기권 또는 할인 프로모션을 활용하면 평균 요금을 낮출 수 있습니다."
        )


class VllmService:
    def __init__(self) -> None:
        settings = get_settings()
        self.model_id = settings.model_id
        try:
            from vllm import LLM, SamplingParams  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("vllm is required to run the model") from exc

        self._llm = LLM(
            model=self.model_id,
            dtype="float16",
            trust_remote_code=settings.trust_remote_code,
        )
        self._sampling_params = SamplingParams(
            temperature=settings.temperature,
            top_p=settings.top_p,
            max_tokens=settings.max_tokens,
            stop=["User:"],
        )

    def generate(self, prompt: str) -> str:
        outputs = self._llm.generate([prompt], self._sampling_params)
        if not outputs or not outputs[0].outputs:
            return ""
        return outputs[0].outputs[0].text.strip()


class LLMService:
    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self.model_id = settings.model_id
        self._backend: Optional[object] = None

    def _ensure_backend(self) -> object:
        if self._backend is not None:
            return self._backend

        if self._settings.sandbox_mode or self._settings.use_mock_llm:
            self._backend = MockLLM(self.model_id)
        else:
            self._backend = VllmService()

        return self._backend

    def generate(self, prompt: str) -> str:
        backend = self._ensure_backend()
        return backend.generate(prompt)


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService()
