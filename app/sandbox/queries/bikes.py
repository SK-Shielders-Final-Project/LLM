from typing import Any

from app.core.services_db import FetchAllDicts, GetMysqlConfig, MysqlConnection


def GetAvailableBikesFromDb(limit: int = 10) -> list[dict[str, Any]]:
    config = GetMysqlConfig()
    query = (
        "SELECT "
        "bike_id, "
        "serial_number, "
        "model_name, "
        "status, "
        "latitude, "
        "longitude, "
        "updated_at "
        f"FROM {config.bikes_table} "
        "WHERE status = 'AVAILABLE' "
        "ORDER BY updated_at DESC "
        "LIMIT %(limit)s"
    )
    with MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"limit": limit})
            return FetchAllDicts(cursor)
