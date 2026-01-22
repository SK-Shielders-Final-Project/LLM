from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from app.core.settings import GetSettings


@dataclass(frozen=True)
class MySQLDBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    users_table: str
    rentals_table: str
    payments_table: str
    bikes_table: str
    bastion_host: str
    bastion_port: int
    bastion_user: str
    bastion_key_path: str


def _GetMysqlConfig() -> MySQLDBConfig:
    settings = GetSettings()
    return MySQLDBConfig(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        users_table=settings.users_table,
        rentals_table=settings.rentals_table,
        payments_table=settings.payments_table,
        bikes_table=settings.bikes_table,
        bastion_host=settings.bastion_host,
        bastion_port=settings.bastion_port,
        bastion_user=settings.bastion_user,
        bastion_key_path=settings.bastion_key_path,
    )


def _ValidateMysqlConfig(config: MySQLDBConfig) -> None:
    missing = [
        name
        for name, value in {
            "MYSQL_HOST": config.host,
            "MYSQL_USER": config.user,
            "MYSQL_PASSWORD": config.password,
            "MYSQL_DATABASE": config.database,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"MySQL settings are missing: {', '.join(missing)}")


@contextmanager
def _MysqlConnection() -> Iterator[Any]:
    try:
        import pymysql  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("pymysql is required for MySQL access") from exc

    config = _GetMysqlConfig()
    _ValidateMysqlConfig(config)

    tunnel: Optional[Any] = None
    host = config.host
    port = config.port

    if config.bastion_host and config.bastion_user and config.bastion_key_path:
        try:
            from sshtunnel import SSHTunnelForwarder  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("sshtunnel is required for bastion access") from exc

        tunnel = SSHTunnelForwarder(
            (config.bastion_host, config.bastion_port),
            ssh_username=config.bastion_user,
            ssh_pkey=config.bastion_key_path,
            remote_bind_address=(config.host, config.port),
            local_bind_address=("127.0.0.1", 0),
        )
        tunnel.start()
        host = "127.0.0.1"
        port = int(tunnel.local_bind_port)

    connection = pymysql.connect(
        host=host,
        port=port,
        user=config.user,
        password=config.password,
        database=config.database,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        yield connection
    finally:
        connection.close()
        if tunnel is not None:
            tunnel.stop()


def _FetchOneDict(cursor: Any) -> dict[str, Any]:
    row = cursor.fetchone()
    return row if row else {}


def _GetLatestPeriodForUser(user_id: str) -> Optional[str]:
    config = _GetMysqlConfig()
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
    with _MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"user_id": user_id})
            row = cursor.fetchone()
            if not row:
                return None
            return row.get("period")


def GetPricingSummaryFromDb(user_id: str, period: Optional[str]) -> dict[str, Any]:
    config = _GetMysqlConfig()
    resolved_period = period or _GetLatestPeriodForUser(user_id)
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
    with _MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"user_id": user_id, "period": resolved_period})
            return _FetchOneDict(cursor)


def GetUsageSummaryFromDb(user_id: str, period: Optional[str]) -> dict[str, Any]:
    config = _GetMysqlConfig()
    resolved_period = period or _GetLatestPeriodForUser(user_id)
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
    with _MysqlConnection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(summary_query, {"user_id": user_id, "period": resolved_period})
            summary = _FetchOneDict(cursor)

            cursor.execute(peak_query, {"user_id": user_id, "period": resolved_period})
            peak_rows = cursor.fetchall()
            peak_hours = [
                f"{int(row['hour_bucket']):02d}:00-{int(row['hour_bucket']):02d}:59"
                for row in peak_rows
                if row.get("hour_bucket") is not None
            ]
            summary["peak_hours"] = peak_hours
            return summary
