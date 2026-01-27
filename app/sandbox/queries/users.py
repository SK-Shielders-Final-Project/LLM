from typing import Any

from app.core.services_db import FetchOneDict, GetMysqlConfig, MysqlConnection


def GetUserProfileFromDb(user_id: str) -> dict[str, Any]:
    config = GetMysqlConfig()
    query = (
        "SELECT "
        "user_id, "
        "username, "
        "name, "
        "email, "
        "phone, "
        "total_point, "
        "admin_level, "
        "created_at, "
        "updated_at "
        f"FROM {config.users_table} "
        "WHERE user_id = %(user_id)s "
        "LIMIT 1"
    )
    with MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"user_id": user_id})
            return FetchOneDict(cursor)
