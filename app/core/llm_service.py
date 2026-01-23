from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

import requests

from app.core.settings import GetSettings


class LLMService:
    def __init__(self) -> None:
        settings = GetSettings()
        self._settings = settings
        self.model_id = settings.model_id
        self._base_url = self._normalize_base_url(settings.llm_base_url)

    def _normalize_base_url(self, base_url: str) -> str:
        base_url = base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        return base_url

    def _fetch_first_model_id(self) -> Optional[str]:
        url = f"{self._base_url}/models"
        response = requests.get(url, timeout=self._settings.llm_timeout_sec)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        models = data.get("data") or []
        if not models:
            return None
        return models[0].get("id")

    def _PostChat(self, messages: list[dict[str, str]]) -> str:
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": self._settings.temperature,
            "top_p": self._settings.top_p,
            "max_tokens": self._settings.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self._settings.llm_api_key}"}
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=self._settings.llm_timeout_sec,
        )
        if response.status_code == 404:
            fallback_model_id = self._fetch_first_model_id()
            if fallback_model_id and fallback_model_id != payload["model"]:
                payload["model"] = fallback_model_id
                self.model_id = fallback_model_id
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self._settings.llm_timeout_sec,
                )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return message.get("content") or ""

    def Generate(self, prompt: str) -> str:
        return self.GenerateChat([{"role": "user", "content": prompt}])

    def GenerateChat(self, messages: list[dict[str, str]]) -> str:
        return self._PostChat(messages)


@lru_cache(maxsize=1)
def GetLlmService() -> LLMService:
    return LLMService()
