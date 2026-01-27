from typing import Optional
from app.core.services_db import GetMysqlConfig
from app.core.services_db import MysqlConnection

def GetLatestPeriodForUser(user_id: str) -> Optional[str]:
    config = GetMysqlConfig()
    query = (
        "SELECT MAX(period) AS period "
        "FROM ("
        f"SELECT DATE_FORMAT(p.created_at, '%%Y-%%m') AS period "
        f"FROM {config.payments_table} p "
        "WHERE p.user_id = %(user_id)s "
        "UNION ALL "
        f"SELECT DATE_FORMAT(COALESCE(r.start_time, r.created_at), '%%Y-%%m') AS period "
        f"FROM {config.rentals_table} r "
        "WHERE r.user_id = %(user_id)s"
        ") t"
    )
    with MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"user_id": user_id})
            row = cursor.fetchone()
            if not row:
                return None
            return row.get("period")