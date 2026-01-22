from __future__ import annotations

from functools import lru_cache

from app.core.settings import GetSettings


class VllmService:
    def __init__(self) -> None:
        settings = GetSettings()
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

    def Generate(self, prompt: str) -> str:
        outputs = self._llm.generate([prompt], self._sampling_params)
        if not outputs or not outputs[0].outputs:
            return ""
        return outputs[0].outputs[0].text.strip()


class LLMService:
    def __init__(self) -> None:
        settings = GetSettings()
        self.model_id = settings.model_id
        self._backend: VllmService | None = None

    def _EnsureBackend(self) -> VllmService:
        if self._backend is not None:
            return self._backend

        self._backend = VllmService()
        return self._backend

    def Generate(self, prompt: str) -> str:
        backend = self._EnsureBackend()
        return backend.Generate(prompt)


@lru_cache(maxsize=1)
def GetLlmService() -> LLMService:
    return LLMService()
