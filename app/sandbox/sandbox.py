from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

from app.sandbox.queries import (
    GetAvailableBikesFromDb,
    GetPaymentsFromDb,
    GetPricingSummaryFromDb,
    GetRentalsFromDb,
    GetUsageSummaryFromDb,
    GetUserProfileFromDb,
)


def _NormalizeUserId(user_id: Any) -> str:
    return str(user_id).strip()


@dataclass
class Sandbox:
    def GetAvailableBikes(self, limit: int = 20) -> list[dict[str, Any]]:
        return GetAvailableBikesFromDb(limit=limit)

    def GetPayments(self, user_id: Any, limit: int = 20) -> list[dict[str, Any]]:
        return GetPaymentsFromDb(user_id=_NormalizeUserId(user_id), limit=limit)

    def GetRentals(self, user_id: Any, limit: int = 20) -> list[dict[str, Any]]:
        return GetRentalsFromDb(user_id=_NormalizeUserId(user_id), limit=limit)

    def GetUserProfile(self, user_id: Any) -> dict[str, Any]:
        return GetUserProfileFromDb(user_id=_NormalizeUserId(user_id))

    def GetPricingSummary(self, user_id: Any, period: Optional[str] = None) -> dict[str, Any]:
        return GetPricingSummaryFromDb(_NormalizeUserId(user_id), period)

    def GetUsageSummary(self, user_id: Any, period: Optional[str] = None) -> dict[str, Any]:
        return GetUsageSummaryFromDb(_NormalizeUserId(user_id), period)


@lru_cache(maxsize=1)
def GetSandbox() -> Sandbox:
    return Sandbox()
