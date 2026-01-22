from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.core.settings import GetSettings
from app.services.services_db import (
    GetPricingSummaryFromDb,
    GetUsageSummaryFromDb,
)


class DataStore:
    def GetPricingSummary(self, user_id: str, period: str | None) -> dict[str, Any]:
        raise NotImplementedError

    def GetUsageSummary(self, user_id: str, period: str | None) -> dict[str, Any]:
        raise NotImplementedError


@dataclass
class MySQLDataStore(DataStore):
    def GetPricingSummary(self, user_id: str, period: str | None) -> dict[str, Any]:
        return GetPricingSummaryFromDb(user_id, period)

    def GetUsageSummary(self, user_id: str, period: str | None) -> dict[str, Any]:
        return GetUsageSummaryFromDb(user_id, period)


@lru_cache(maxsize=1)
def GetDataStore() -> DataStore:
    settings = GetSettings()
    if settings.db_backend.lower() != "mysql":
        raise RuntimeError("Only MySQL backend is supported")
    return MySQLDataStore()
