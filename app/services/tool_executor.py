from __future__ import annotations

import json
import re
from typing import Any

from app.sandbox import GetSandbox


def _ParseToolArgs(raw_args: Any) -> dict[str, Any]:
    if not raw_args:
        return {}
    if isinstance(raw_args, dict):
        return raw_args
    try:
        return json.loads(raw_args)
    except json.JSONDecodeError:
        return {}


def _NormalizeLimit(value: Any, default: int = 20) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(10, parsed))


def _NormalizeUserId(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value)
    match = re.search(r"(\d+)", text)
    if match:
        return match.group(1)
    return fallback


def ExecuteToolCall(tool_call: dict[str, Any], user_id: int) -> dict[str, Any]:
    function = tool_call.get("function") or {}
    tool_name = function.get("name") or ""
    args = _ParseToolArgs(function.get("arguments"))
    return ExecuteTool(tool_name, args, user_id)


def ExecuteTool(tool_name: str, args: dict[str, Any], user_id: int) -> dict[str, Any]:
    sandbox = GetSandbox()
    resolved_user_id = _NormalizeUserId(args.get("user_id"), str(user_id))
    if tool_name == "get_available_bikes":
        limit = _NormalizeLimit(args.get("limit"), default=20)
        return {"tool": tool_name, "data": sandbox.GetAvailableBikes(limit=limit)}
    if tool_name == "get_payments":
        limit = _NormalizeLimit(args.get("limit"), default=20)
        return {
            "tool": tool_name,
            "data": sandbox.GetPayments(user_id=resolved_user_id, limit=limit),
        }
    if tool_name == "get_rentals":
        limit = _NormalizeLimit(args.get("limit"), default=20)
        return {
            "tool": tool_name,
            "data": sandbox.GetRentals(user_id=resolved_user_id, limit=limit),
        }
    if tool_name == "get_user_profile":
        return {"tool": tool_name, "data": sandbox.GetUserProfile(user_id=resolved_user_id)}
    if tool_name == "get_pricing_summary":
        return {
            "tool": tool_name,
            "data": sandbox.GetPricingSummary(
                user_id=resolved_user_id, period=args.get("period")
            ),
        }
    if tool_name == "get_usage_summary":
        return {
            "tool": tool_name,
            "data": sandbox.GetUsageSummary(
                user_id=resolved_user_id, period=args.get("period")
            ),
        }
    if tool_name == "get_total_payments":
        return {
            "tool": tool_name,
            "data": sandbox.GetTotalPayments(
                user_id=resolved_user_id, period=args.get("period")
            ),
        }
    return {"tool": tool_name, "error": "unsupported_tool"}
