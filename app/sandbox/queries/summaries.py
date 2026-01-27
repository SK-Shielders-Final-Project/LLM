from typing import Any, Optional

from app.core.services_db import (
    FetchOneDict,
    GetLatestPeriodForUser,
    GetMysqlConfig,
    MysqlConnection,
)


def GetPricingSummaryFromDb(user_id: str, period: Optional[str]) -> dict[str, Any]:
    config = GetMysqlConfig()
    resolved_period = period or GetLatestPeriodForUser(user_id)
    if not resolved_period:
        return {}
    query = (
        "SELECT "
        "%(user_id)s AS user_id, "
        "%(period)s AS period, "
        "'KRW' AS currency, "
        "COALESCE(SUM(p.amount), 0) AS total_amount, "
        "0 AS discounts, "
        "COALESCE(COUNT(r.rental_id), 0) AS rides, "
        "CASE "
        "WHEN COUNT(r.rental_id) = 0 THEN 0 "
        "ELSE ROUND(COALESCE(SUM(p.amount), 0) / COUNT(r.rental_id)) "
        "END AS avg_price "
        f"FROM {config.payments_table} p "
        f"LEFT JOIN {config.rentals_table} r "
        "ON p.user_id = r.user_id "
        "AND DATE_FORMAT(COALESCE(r.start_time, r.created_at), '%%Y-%%m') = %(period)s "
        "WHERE p.user_id = %(user_id)s "
        "AND DATE_FORMAT(p.created_at, '%%Y-%%m') = %(period)s"
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
        "%(user_id)s AS user_id, "
        "%(period)s AS period, "
        "COALESCE(COUNT(r.rental_id), 0) AS total_rides, "
        "COALESCE(ROUND(SUM(r.total_distance), 2), 0) AS total_distance_km, "
        "COALESCE(SUM(TIMESTAMPDIFF(MINUTE, "
        "COALESCE(r.start_time, r.created_at), COALESCE(r.end_time, r.created_at))), 0) "
        "AS total_minutes, "
        "NULL AS favorite_zone "
        f"FROM {config.rentals_table} r "
        "WHERE r.user_id = %(user_id)s "
        "AND DATE_FORMAT(COALESCE(r.start_time, r.created_at), '%%Y-%%m') = %(period)s"
    )
    peak_query = (
        "SELECT HOUR(r.start_time) AS hour_bucket "
        f"FROM {config.rentals_table} r "
        "WHERE r.user_id = %(user_id)s "
        "AND DATE_FORMAT(COALESCE(r.start_time, r.created_at), '%%Y-%%m') = %(period)s "
        "GROUP BY hour_bucket "
        "ORDER BY COUNT(*) DESC "
        "LIMIT 2"
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
