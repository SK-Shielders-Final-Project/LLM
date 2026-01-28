from typing import Any, Optional

from app.core.services_db import FetchAllDicts, GetMysqlConfig, MysqlConnection


def GetRentalsFromDb(user_id: Optional[str] = None, limit: int = 50) -> list[dict[str, Any]]:
    config = GetMysqlConfig()
    query = (
        "SELECT "
        "r.rental_id, "
        "r.user_id, "
        "u.username, "
        "r.bike_id, "
        "r.start_time, "
        "r.end_time, "
        "r.total_distance, "
        "r.created_at "
        f"FROM {config.rentals_table} r "
        f"LEFT JOIN {config.users_table} u ON r.user_id = u.user_id "
    )
    params: dict[str, Any] = {"limit": limit}
    if user_id:
        query += "WHERE r.user_id = :user_id "
        params["user_id"] = user_id
    query += "ORDER BY r.rental_id DESC FETCH FIRST :limit ROWS ONLY"
    with MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return FetchAllDicts(cursor)
