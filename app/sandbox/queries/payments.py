from typing import Any, Optional

from app.core.services_db import FetchAllDicts, GetMysqlConfig, MysqlConnection


def GetPaymentsFromDb(user_id: Optional[str] = None, limit: int = 50) -> list[dict[str, Any]]:
    config = GetMysqlConfig()
    query = (
        "SELECT "
        "r.payment_id, "
        "r.user_id, "
        "u.username, "
        "r.amount, "
        "r.payment_status, "
        "r.payment_method, "
        "r.transaction_id, "
        "r.created_at "
        f"FROM {config.payments_table} r "
        f"LEFT JOIN {config.users_table} u ON r.user_id = u.user_id "
    )
    params: dict[str, Any] = {"limit": limit}
    if user_id:
        query += "WHERE r.user_id = %(user_id)s "
        params["user_id"] = user_id
    query += "ORDER BY r.payment_id DESC LIMIT %(limit)s"
    with MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return FetchAllDicts(cursor)
