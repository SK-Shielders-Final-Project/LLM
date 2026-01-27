from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from app.config import GetSettings


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
    files_table: str
    notices_table: str
    inquiries_table: str
    chat_table: str
    bastion_host: str
    bastion_port: int
    bastion_user: str
    bastion_key_path: str


def GetMysqlConfig() -> MySQLDBConfig:
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
        files_table=settings.files_table,
        notices_table=settings.notices_table,
        inquiries_table=settings.inquiries_table,
        chat_table=settings.chat_table,
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
def MysqlConnection() -> Iterator[Any]:
    try:
        import pymysql  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("pymysql is required for MySQL access") from exc

    config = GetMysqlConfig()
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


def FetchOneDict(cursor: Any) -> dict[str, Any]:
    row = cursor.fetchone()
    return row if row else {}


def FetchAllDicts(cursor: Any) -> list[dict[str, Any]]:
    rows = cursor.fetchall()
    return list(rows) if rows else []

