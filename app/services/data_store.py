from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.core.settings import get_settings


class DataStore:
    def get_pricing_summary(self, user_id: str, period: str) -> dict[str, Any]:
        raise NotImplementedError

    def get_usage_summary(self, user_id: str, period: str) -> dict[str, Any]:
        raise NotImplementedError


@dataclass
class MockDataStore(DataStore):
    def get_pricing_summary(self, user_id: str, period: str) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "period": period,
            "currency": "KRW",
            "total_amount": 18200,
            "discounts": 1200,
            "rides": 14,
            "avg_price": 1300,
        }

    def get_usage_summary(self, user_id: str, period: str) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "period": period,
            "total_rides": 14,
            "total_distance_km": 48.7,
            "total_minutes": 312,
            "favorite_zone": "홍대입구",
            "peak_hours": ["08:00-09:00", "18:00-20:00"],
        }


class AwsDynamoDataStore(DataStore):
    def __init__(self) -> None:
        settings = get_settings()
        try:
            import boto3  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("boto3 is required for AWS access") from exc

        self._pricing_table_name = settings.pricing_table
        self._usage_table_name = settings.usage_table
        self._dynamo = boto3.resource("dynamodb", region_name=settings.aws_region)
        self._pricing_table = self._dynamo.Table(self._pricing_table_name)
        self._usage_table = self._dynamo.Table(self._usage_table_name)

    def get_pricing_summary(self, user_id: str, period: str) -> dict[str, Any]:
        response = self._pricing_table.get_item(
            Key={
                "user_id": user_id,
                "period": period,
            }
        )
        return response.get("Item", {})

    def get_usage_summary(self, user_id: str, period: str) -> dict[str, Any]:
        response = self._usage_table.get_item(
            Key={
                "user_id": user_id,
                "period": period,
            }
        )
        return response.get("Item", {})


@lru_cache(maxsize=1)
def get_data_store() -> DataStore:
    settings = get_settings()
    if settings.sandbox_mode or settings.use_mock_data:
        return MockDataStore()

    try:
        return AwsDynamoDataStore()
    except Exception:
        return MockDataStore()
