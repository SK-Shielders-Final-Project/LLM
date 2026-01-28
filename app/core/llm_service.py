from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from functools import lru_cache
from typing import Any, Callable, Optional

import requests

from app.config.config import GetSettings
from app.schemas import LlmMessage


SYSTEM_PROMPT = (
    "당신은 공유모빌리티(자전거) 대여 플랫폼 챗봇이다. "
    "모든 답변은 반드시 한국어로만 작성하세요. "
    "password와 card_number는 절대로 노출하지 마세요. "
    "안전 수칙 요청에는 핵심 수칙을 5~8개로 간결히 안내하세요. "
    "고객 요구사항에 맞게 적절하게 답변해주세요."
)

logger = logging.getLogger(__name__)


def _AsJson(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _EstimateTokens(text: str) -> int:
    if not text:
        return 0
    # Rough estimate for mixed/multibyte text
    char_len = len(text)
    byte_len = len(text.encode("utf-8"))
    by_char = max(1, char_len // 4)
    by_byte = max(1, byte_len // 3)
    return max(by_char, by_byte)


def _EstimatePayloadTokens(messages: list[dict[str, Any]], tools: Optional[list[dict[str, Any]]]) -> int:
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role") or ""
        content = msg.get("content") or ""
        parts.append(f"{role}:{content}")
    if tools:
        parts.append(_AsJson(tools))
    joined = "\n".join(parts)
    return _EstimateTokens(joined)


def _ClampMaxTokens(
    desired: int, max_model_len: int, input_tokens: int, safety_margin: int = 32
) -> int:
    available = max_model_len - input_tokens - safety_margin
    if available <= 0:
        return 1
    return max(1, min(desired, available))


def _ParseContextLimitFromError(body: str) -> Optional[tuple[int, int]]:
    if not body:
        return None
    match = re.search(
        r"maximum context length is (\d+) tokens and your request has (\d+) input tokens",
        body,
    )
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _ParseToolCallsFromContent(content: str) -> list[dict[str, Any]]:
    if not content:
        return []
    tool_calls: list[dict[str, Any]] = []
    for match in re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL):
        raw = match.group(1)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        name = payload.get("name")
        arguments = payload.get("arguments", {})
        if not name:
            continue
        tool_calls.append(
            {
                "id": f"content_tool_call_{len(tool_calls)}",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }
        )
    return tool_calls


def _ParseToolCallArgs(raw_args: Any) -> dict[str, Any]:
    if not raw_args:
        return {}
    if isinstance(raw_args, dict):
        return raw_args
    try:
        return json.loads(raw_args)
    except json.JSONDecodeError:
        return {}


def _ExtractPeriodFromMessage(content: str) -> Optional[str]:
    if not content:
        return None
    text = content.strip()
    if re.search(r"\bthis_month\b|이번\s*달|이번달", text, re.IGNORECASE):
        now = datetime.utcnow()
        return f"{now.year:04d}-{now.month:02d}"
    year_match = re.search(r"(\d{4})", text)
    month_match = re.search(r"(\d{1,2})\s*월", text)
    if month_match:
        year = int(year_match.group(1)) if year_match else datetime.utcnow().year
        month = int(month_match.group(1))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"
    standard_match = re.search(r"(\d{4})\s*[-/.]\s*(\d{1,2})", text)
    if standard_match:
        year = int(standard_match.group(1))
        month = int(standard_match.group(2))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"
    return None


def _PreferTotalUsageTool(tool_calls: list[dict[str, Any]], user_message: str) -> None:
    if not tool_calls or not user_message:
        return
    if not re.search(r"사용\s*내역|사용내역|총\s*사용량|총사용량", user_message):
        return
    for tool_call in tool_calls:
        function = tool_call.get("function") or {}
        tool_name = function.get("name") or ""
        if tool_name in {"get_usage_summary", "get_rentals"}:
            function["name"] = "get_total_usage"


def _InjectPeriodIfMissing(tool_calls: list[dict[str, Any]], user_message: str) -> None:
    if not tool_calls:
        return
    period_hint = _ExtractPeriodFromMessage(user_message)
    if not period_hint:
        return
    for tool_call in tool_calls:
        function = tool_call.get("function") or {}
        tool_name = function.get("name") or ""
        if tool_name not in {
            "get_pricing_summary",
            "get_usage_summary",
            "get_total_payments",
            "get_total_usage",
        }:
            continue
        args = _ParseToolCallArgs(function.get("arguments"))
        if args.get("period"):
            continue
        args["period"] = period_hint
        function["arguments"] = json.dumps(args, ensure_ascii=False)


def _InferToolFromUserMessage(
    content: str, tool_keywords_map: dict[str, list[str]]
) -> Optional[str]:
    if not content:
        return None
    text = content.lower()
    for tool_name, keywords in tool_keywords_map.items():
        if not keywords:
            continue
        pattern = "|".join(re.escape(keyword.lower()) for keyword in keywords if keyword)
        if not pattern:
            continue
        if re.search(pattern, text):
            return tool_name
    return None


def _BuildForcedToolCall(tool_name: str, user_id: int) -> dict[str, Any]:
    args: dict[str, Any] = {}
    if tool_name in {
        "get_user_profile",
        "get_payments",
        "get_rentals",
        "get_pricing_summary",
        "get_usage_summary",
        "get_total_payments",
        "get_total_usage",
    }:
        args["user_id"] = str(user_id)
    return {
        "id": "forced_tool_call_0",
        "type": "function",
        "function": {
            "name": tool_name,
            "arguments": json.dumps(args, ensure_ascii=False),
        },
    }


def BuildSystemContext(message: LlmMessage) -> str:
    return (
        f"{SYSTEM_PROMPT}\n"
        f"UserId: {message.user_id}\n"
        "Locale: ko\n"
        "필요한 정보가 있으면 적절한 도구를 호출하세요.\n"
        "사용자 정보/프로필 요청: get_user_profile 호출.\n"
        "결제 내역 요청: get_payments 호출.\n"
        "이용 내역 요청: get_rentals 호출.\n"
        "요금 요약 요청: get_pricing_summary 호출.\n"
        "이용 요약 요청: get_usage_summary 호출.\n"
        "자전거 목록 요청: get_available_bikes 호출.\n"
        "전체 결제 내역 요청: get_total_payments 호출.\n"
        "사용 내역 요청: get_total_usage 호출.\n"
        "전체 사용 내역 요청: get_total_usage 호출.\n"
    )


def BuildToolSchema() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_available_bikes",
                "description": "사용 가능한 자전거 목록을 조회한다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_payments",
                "description": "사용자의 결제 내역을 조회한다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["user_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_rentals",
                "description": "사용자의 이용 내역을 조회한다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    },
                    "required": ["user_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_user_profile",
                "description": "사용자 프로필을 조회한다.",
                "parameters": {
                    "type": "object",
                    "properties": {"user_id": {"type": "string"}},
                    "required": ["user_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_pricing_summary",
                "description": "사용자의 요금 요약을 조회한다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "period": {"type": "string"},
                    },
                    "required": ["user_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_usage_summary",
                "description": "사용자의 이용 요약을 조회한다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "period": {"type": "string"},
                    },
                    "required": ["user_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_total_payments",
                "description": "사용자의 총 결제 금액을 조회한다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "period": {"type": "string"},
                    },
                    "required": ["user_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_total_usage",
                "description": "사용자의 총 사용량을 조회한다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "period": {"type": "string"},
                    },
                    "required": ["user_id"],
                },
            },
        },
    ]


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

    def _PostChatMessage(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        input_tokens = _EstimatePayloadTokens(messages, tools)
        max_tokens = _ClampMaxTokens(
            self._settings.max_tokens,
            self._settings.max_model_len,
            input_tokens,
        )
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "temperature": self._settings.temperature,
            "top_p": self._settings.top_p,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        headers = {"Authorization": f"Bearer {self._settings.llm_api_key}"}
        logger.info(
            "LLM 요청 시작 url=%s model=%s messages=%s tools=%s",
            url,
            payload.get("model"),
            len(messages),
            [tool.get("function", {}).get("name") for tool in (tools or [])],
        )
        logger.info(
            "LLM 토큰 계산 input_est=%s max_tokens=%s",
            input_tokens,
            payload.get("max_tokens"),
        )
        response = self._PostRequest(url, payload, headers)
        if response.status_code == 404:
            fallback_model_id = self._fetch_first_model_id()
            if fallback_model_id and fallback_model_id != payload["model"]:
                payload["model"] = fallback_model_id
                self.model_id = fallback_model_id
                logger.warning("LLM 모델 대체: %s", fallback_model_id)
                response = self._PostRequest(url, payload, headers)
        if response.status_code == 400:
            logger.warning(
                "요청 400 응답 body=%s",
                response.text,
            )
            parsed = _ParseContextLimitFromError(response.text)
            if parsed:
                max_context_len, input_ctx_tokens = parsed
                adjusted_max = _ClampMaxTokens(
                    payload.get("max_tokens") or self._settings.max_tokens,
                    max_context_len,
                    input_ctx_tokens,
                )
                if adjusted_max < (payload.get("max_tokens") or 0):
                    logger.warning(
                        "max_tokens 재조정 max_context=%s input_tokens=%s max_tokens=%s",
                        max_context_len,
                        input_ctx_tokens,
                        adjusted_max,
                    )
                    payload["max_tokens"] = adjusted_max
                    response = self._PostRequest(url, payload, headers)
            if (
                response.status_code == 400
                and tools
                and self._settings.llm_tool_fallback_on_400
            ):
                logger.warning("도구 호출 미지원 가능성: 도구 없이 재시도")
                payload.pop("tools", None)
                payload.pop("tool_choice", None)
                response = self._PostRequest(url, payload, headers)
        self._RaiseForStatus(response, payload)
        data: dict[str, Any] = response.json()
        choices = data.get("choices") or []
        if not choices:
            return {}
        message = choices[0].get("message") or {}
        finish_reason = choices[0].get("finish_reason")
        if isinstance(message, dict):
            message["_finish_reason"] = finish_reason
        return message

    def _PostRequest(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> requests.Response:
        try:
            return requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._settings.llm_timeout_sec,
            )
        except requests.RequestException as exc:
            logger.exception("LLM 요청 실패 url=%s error=%s", url, exc)
            raise

    def _RaiseForStatus(self, response: requests.Response, payload: dict[str, Any]) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body = response.text
            logger.error(
                "LLM 응답 오류 status=%s body=%s payload_keys=%s",
                response.status_code,
                body,
                sorted(payload.keys()),
            )
            raise exc

    def _PostChat(self, messages: list[dict[str, Any]]) -> str:
        accumulated: list[str] = []
        current_messages = list(messages)
        max_continuations = 3
        for _ in range(max_continuations):
            message = self._PostChatMessage(current_messages)
            content = message.get("content") or ""
            if content:
                accumulated.append(content)
            finish_reason = message.get("_finish_reason")
            if finish_reason != "length":
                break
            if not content:
                break
            current_messages = current_messages + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": "계속"},
            ]
        return "".join(accumulated)

    def Generate(self, prompt: str) -> str:
        return self.GenerateChat([{"role": "user", "content": prompt}])

    def GenerateChat(self, messages: list[dict[str, Any]]) -> str:
        return self._PostChat(messages)

    def GenerateChatWithTools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._PostChatMessage(messages, tools=tools)

    def GenerateAssistantReply(
        self,
        message: LlmMessage,
        tool_executor: Callable[[dict[str, Any], int], dict[str, Any]],
    ) -> str:
        llm_messages: list[dict[str, Any]] = [
            {"role": "system", "content": BuildSystemContext(message)},
            {"role": message.role, "content": message.content},
        ]
        inferred_tool = _InferToolFromUserMessage(
            message.content, self._settings.tool_keywords_map
        )
        tools = BuildToolSchema() if inferred_tool else None
        if tools:
            llm_message = self.GenerateChatWithTools(llm_messages, tools)
        else:
            llm_message = self._PostChatMessage(llm_messages)
        tool_calls = llm_message.get("tool_calls") or []
        if not tool_calls:
            raw_content = llm_message.get("content") or ""
            content_tool_calls = _ParseToolCallsFromContent(raw_content)
            if content_tool_calls:
                tool_calls = content_tool_calls
            else:
                if "<tool_call>" in raw_content:
                    logger.warning("불완전한 tool_call 감지: 내용 무시 후 보정")
                if inferred_tool:
                    logger.info("도구 호출 없음: 의도 기반 보정 tool=%s", inferred_tool)
                    forced_tool_call = _BuildForcedToolCall(inferred_tool, message.user_id)
                    tool_calls = [forced_tool_call]
                else:
                    logger.info("LLM 도구 호출 없음")
                    content = llm_message.get("content") or ""
                    if content:
                        return content
                    logger.info("LLM 응답 비어있음: 도구 없이 재시도")
                    return self.GenerateChat(llm_messages)

        _PreferTotalUsageTool(tool_calls, message.content)
        _InjectPeriodIfMissing(tool_calls, message.content)

        tool_messages: list[dict[str, Any]] = []
        for idx, tool_call in enumerate(tool_calls):
            tool_call_id = tool_call.get("id") or f"tool_call_{idx}"
            tool_name = (tool_call.get("function") or {}).get("name")
            logger.info("도구 호출 실행 name=%s id=%s", tool_name, tool_call_id)
            result = tool_executor(tool_call, message.user_id)
            tool_messages.append(
                {"role": "tool", "tool_call_id": tool_call_id, "content": _AsJson(result)}
            )

        assistant_message = {
            "role": "assistant",
            "content": llm_message.get("content") or "",
            "tool_calls": tool_calls,
        }
        final_messages = llm_messages + [assistant_message] + tool_messages
        return self.GenerateChat(final_messages)


@lru_cache(maxsize=1)
def GetLlmService() -> LLMService:
    return LLMService()
