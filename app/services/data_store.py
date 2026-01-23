from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.core.settings import GetSettings
from app.core.services_db import (
    GetAvailableBikesFromDb,
    GetBikesFromDb,
    GetChatFromDb,
    GetFilesFromDb,
    GetInquiriesFromDb,
    GetNoticesFromDb,
    GetPaymentsFromDb,
    GetPricingSummaryFromDb,
    GetRentalsFromDb,
    GetUsersFromDb,
    GetUserProfileFromDb,
    GetUsageSummaryFromDb,
)


class DataStore:
    def GetPricingSummary(self, user_id: str, period: str | None) -> dict[str, Any]:
        raise NotImplementedError

    def GetUsageSummary(self, user_id: str, period: str | None) -> dict[str, Any]:
        raise NotImplementedError

    def GetUserProfile(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def GetUsers(self, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError


    def GetFiles(self, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError

    def GetNotices(self, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError

    def GetInquiries(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError

    def GetChat(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError

    def GetBikes(self, limit: int = 100) -> list[dict[str, Any]]:
        raise NotImplementedError

    def GetAvailableBikes(self, limit: int = 100) -> list[dict[str, Any]]:
        raise NotImplementedError

    def GetRentals(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError

    def GetPayments(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError


@dataclass
class MySQLDataStore(DataStore):
    def GetPricingSummary(self, user_id: str, period: str | None) -> dict[str, Any]:
        return GetPricingSummaryFromDb(user_id, period)

    def GetUsageSummary(self, user_id: str, period: str | None) -> dict[str, Any]:
        return GetUsageSummaryFromDb(user_id, period)

    def GetUserProfile(self, user_id: str) -> dict[str, Any]:
        return GetUserProfileFromDb(user_id)

    def GetUsers(self, limit: int = 50) -> list[dict[str, Any]]:
        return GetUsersFromDb(limit)

    def GetFiles(self, limit: int = 50) -> list[dict[str, Any]]:
        return GetFilesFromDb(limit)

    def GetNotices(self, limit: int = 50) -> list[dict[str, Any]]:
        return GetNoticesFromDb(limit)

    def GetInquiries(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return GetInquiriesFromDb(user_id, limit)

    def GetChat(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return GetChatFromDb(user_id, limit)

    def GetBikes(self, limit: int = 100) -> list[dict[str, Any]]:
        return GetBikesFromDb(limit)

    def GetAvailableBikes(self, limit: int = 100) -> list[dict[str, Any]]:
        return GetAvailableBikesFromDb(limit)

    def GetRentals(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return GetRentalsFromDb(user_id, limit)

    def GetPayments(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return GetPaymentsFromDb(user_id, limit)


@lru_cache(maxsize=1)
def GetDataStore() -> DataStore:
    settings = GetSettings()
    if settings.db_backend.lower() != "mysql":
        raise RuntimeError("Only MySQL backend is supported")
    return MySQLDataStore()
