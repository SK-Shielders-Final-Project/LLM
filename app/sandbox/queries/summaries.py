from typing import Any, Optional

from app.core.services_db import FetchOneDict, GetMysqlConfig, MysqlConnection
from app.sandbox.sub_query.date import _ResolvePeriodFromText
from app.sandbox.sub_query.getLastUser import GetLatestPeriodForUser


def GetPricingSummaryFromDb(user_id: str, period: Optional[str]) -> dict[str, Any]:
    config = GetMysqlConfig()
    resolved_period = period or GetLatestPeriodForUser(user_id)
    if not resolved_period:
        return {}
    query = (
        "SELECT "
        ":user_id AS user_id, "
        ":period AS period, "
        "'KRW' AS currency, "
        "NVL(SUM(p.amount), 0) AS total_amount, "
        "0 AS discounts, "
        "COUNT(r.rental_id) AS rides, "
        "CASE "
        "WHEN COUNT(r.rental_id) = 0 THEN 0 "
        "ELSE ROUND(NVL(SUM(p.amount), 0) / COUNT(r.rental_id)) "
        "END AS avg_price "
        f"FROM {config.payments_table} p "
        f"LEFT JOIN {config.rentals_table} r "
        "ON p.user_id = r.user_id "
        "AND TO_CHAR(NVL(r.start_time, r.created_at), 'YYYY-MM') = :period "
        "WHERE p.user_id = :user_id "
        "AND p.payment_status = 'DONE' "
        "AND TO_CHAR(p.created_at, 'YYYY-MM') = :period"
    )
    with MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"user_id": user_id, "period": resolved_period})
            return FetchOneDict(cursor)


def GetUsageSummaryFromDb(user_id: str, period: Optional[str]) -> dict[str, Any]:
    config = GetMysqlConfig()
    resolved_period = period or GetLatestPeriodForUser(user_id)
    if not resolved_period:
        return {}
    summary_query = (
        "SELECT "
        ":user_id AS user_id, "
        ":period AS period, "
        "COUNT(r.rental_id) AS total_rides, "
        "NVL(ROUND(SUM(r.total_distance), 2), 0) AS total_distance_km, "
        "NVL(SUM((NVL(r.end_time, r.created_at) - NVL(r.start_time, r.created_at)) "
        "* 24 * 60), 0) "
        "AS total_minutes, "
        "NULL AS favorite_zone "
        f"FROM {config.rentals_table} r "
        "WHERE r.user_id = :user_id "
        "AND TO_CHAR(r.created_at, 'YYYY-MM') = :period"
    )
    peak_query = (
        "SELECT EXTRACT(HOUR FROM r.start_time) AS hour_bucket "
        f"FROM {config.rentals_table} r "
        "WHERE r.user_id = :user_id "
        "AND TO_CHAR(r.created_at, 'YYYY-MM') = :period "
        "GROUP BY hour_bucket "
        "ORDER BY COUNT(*) DESC "
        "FETCH FIRST 2 ROWS ONLY"
    )
    with MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(summary_query, {"user_id": user_id, "period": resolved_period})
            summary = FetchOneDict(cursor)

            cursor.execute(peak_query, {"user_id": user_id, "period": resolved_period})
            peak_rows = cursor.fetchall()
            peak_hours = [
                f"{int(row['hour_bucket']):02d}:00-{int(row['hour_bucket']):02d}:59"
                for row in peak_rows
                if row.get("hour_bucket") is not None
            ]
            summary["peak_hours"] = peak_hours
            return summary

def GetTotalPaymentFromDb(user_id: str, period: Optional[str] = None) -> dict[str, Any]:
    config = GetMysqlConfig()
    resolved_period = _ResolvePeriodFromText(period, user_id)
    if not resolved_period:
        return {}
    query = (
        "SELECT "
        ":user_id AS user_id, "
        ":period AS period, "
        "'KRW' AS currency, "
        "NVL(SUM(CASE WHEN payment_method = 'CARD' THEN amount ELSE 0 END), 0) "
        "AS card_amount, "
        "NVL(SUM(CASE WHEN payment_method = 'POINT' THEN amount ELSE 0 END), 0) "
        "AS point_amount, "
        "NVL(SUM(CASE WHEN payment_method IN ('CARD', 'POINT') THEN amount ELSE 0 END), 0) "
        "AS total_amount "
        f"FROM {config.payments_table} "
        "WHERE user_id = :user_id "
        "AND payment_status = 'DONE' "
        "AND TO_CHAR(created_at, 'YYYY-MM') = :period"
    )
    with MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"user_id": user_id, "period": resolved_period})
            return FetchOneDict(cursor)


def GetTotalUsageFromDb(user_id: str, period: Optional[str] = None) -> dict[str, Any]:
    config = GetMysqlConfig()
    reserved_period = _ResolvePeriodFromText(period, user_id)

    if not reserved_period:
        return {}

    rentals_query = (
        "SELECT "
        "COUNT(rental_id) AS total_rentals, "
        "NVL(SUM((NVL(end_time, created_at) - NVL(start_time, created_at)) "
        "* 24 * 60), 0) AS total_minutes "
        f"FROM {config.rentals_table} "
        "WHERE user_id = :user_id "
        "AND TO_CHAR(created_at, 'YYYY-MM') = :period"
    )
    payments_query = (
        "SELECT "
        "COUNT(amount) AS total_payments, "
        "NVL(SUM(amount), 0) AS total_amount "
        f"FROM {config.payments_table} "
        "WHERE user_id = :user_id "
        "AND payment_status = 'DONE' "
        "AND TO_CHAR(created_at, 'YYYY-MM') = :period"
    )
    with MysqlConnection() as connection:
        with connection.cursor() as cursor:
            params = {"user_id": user_id, "period": reserved_period}
            cursor.execute(rentals_query, params)
            rentals_summary = FetchOneDict(cursor) or {}
            cursor.execute(payments_query, params)
            payments_summary = FetchOneDict(cursor) or {}
            return {
                "user_id": user_id,
                "period": reserved_period,
                "total_rentals": rentals_summary.get("total_rentals", 0),
                "total_minutes": rentals_summary.get("total_minutes", 0),
                "total_amount": payments_summary.get("total_amount", 0),
                "total_payments": payments_summary.get("total_payments", 0),
            }