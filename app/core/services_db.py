from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from app.config import GetSettings


@dataclass(frozen=True)
class OracleDBConfig:
    host: str
    port: int
    user: str
    password: str
    service: str
    dsn: str
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


def GetMysqlConfig() -> OracleDBConfig:
    settings = GetSettings()
    return OracleDBConfig(
        host=settings.oracle_host,
        port=settings.oracle_port,
        user=settings.oracle_user,
        password=settings.oracle_password,
        service=settings.oracle_service,
        dsn=settings.oracle_dsn,
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


def _ValidateMysqlConfig(config: OracleDBConfig) -> None:
    missing = [
        name
        for name, value in {
            "ORACLE_HOST": config.host,
            "ORACLE_USER": config.user,
            "ORACLE_PASSWORD": config.password,
            "ORACLE_SERVICE": config.service,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Oracle settings are missing: {', '.join(missing)}")


def _ToDictRow(cursor: Any, row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    if cursor.description:
        columns = [col[0].lower() for col in cursor.description]
        return dict(zip(columns, row))
    return {}


def _ToDictRows(cursor: Any, rows: Any) -> list[dict[str, Any]]:
    if not rows:
        return []
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        return list(rows)
    if cursor.description:
        columns = [col[0].lower() for col in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    return []


@contextmanager
def MysqlConnection() -> Iterator[Any]:
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

    try:
        import oracledb  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("oracledb is required for Oracle access") from exc
    dsn = config.dsn
    if tunnel is not None or not dsn:
        dsn = oracledb.makedsn(host, port, service_name=config.service)
    connection = oracledb.connect(
        user=config.user,
        password=config.password,
        dsn=dsn,
    )
    try:
        yield connection
    finally:
        connection.close()
        if tunnel is not None:
            tunnel.stop()


def FetchOneDict(cursor: Any) -> dict[str, Any]:
    row = cursor.fetchone()
    return _ToDictRow(cursor, row)


def FetchAllDicts(cursor: Any) -> list[dict[str, Any]]:
    rows = cursor.fetchall()
    return _ToDictRows(cursor, rows)

