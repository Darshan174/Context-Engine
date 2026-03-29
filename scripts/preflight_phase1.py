from __future__ import annotations

import argparse
import asyncio
import socket
import sys
from pathlib import Path
from urllib import error, request
from urllib.parse import urlparse, urlunparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
EXPECTED_ALEMBIC_REVISION = "20260328_0001"
EXPECTED_TABLES = {
    "workspaces",
    "knowledge_models",
    "components",
    "relationships",
    "source_documents",
    "component_sources",
}


def check_env_file() -> tuple[bool, str]:
    if ENV_FILE.exists():
        return True, f".env found at {ENV_FILE}"
    return False, f".env not found at {ENV_FILE}"


def make_sync_postgres_url(database_url: str) -> str:
    if "+asyncpg" not in database_url:
        return database_url
    parts = urlparse(database_url)
    return urlunparse(parts._replace(scheme=parts.scheme.replace("+asyncpg", "")))


def check_postgres(database_url: str) -> tuple[bool, str]:
    try:
        import psycopg
    except ImportError:
        psycopg = None

    if psycopg is not None:
        sync_url = make_sync_postgres_url(database_url)
        try:
            with psycopg.connect(sync_url, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    result = _collect_postgres_metadata_sync(cur)
            return _format_postgres_check(result)
        except Exception as exc:  # pragma: no cover - CLI script
            return False, f"Postgres check failed: {exc}"

    try:
        import asyncpg
    except ImportError as exc:  # pragma: no cover - CLI script
        return False, (
            "Postgres check unavailable: install project dependencies first "
            f"({exc})"
        )

    try:
        result = asyncio.run(_collect_postgres_metadata_async(database_url, asyncpg))
        return _format_postgres_check(result)
    except Exception as exc:  # pragma: no cover - CLI script
        return False, f"Postgres check failed: {exc}"


def _collect_postgres_metadata_sync(cur) -> dict[str, object]:
    cur.execute("select current_database(), current_user")
    db_name, user = cur.fetchone()
    cur.execute("select extname from pg_extension where extname = 'vector'")
    has_vector = cur.fetchone() is not None
    cur.execute(
        """
        select table_name
        from information_schema.tables
        where table_schema = 'public'
        """
    )
    tables = {row[0] for row in cur.fetchall()}
    revision = None
    if "alembic_version" in tables:
        cur.execute("select version_num from alembic_version limit 1")
        row = cur.fetchone()
        revision = row[0] if row else None
    return {
        "db_name": db_name,
        "user": user,
        "has_vector": has_vector,
        "tables": tables,
        "revision": revision,
    }


async def _collect_postgres_metadata_async(
    database_url: str,
    asyncpg_module,
) -> dict[str, object]:
    conn = await asyncpg_module.connect(database_url.replace("+asyncpg", ""), timeout=5)
    try:
        row = await conn.fetchrow("select current_database(), current_user")
        db_name = row[0]
        user = row[1]
        has_vector = (
            await conn.fetchval("select exists(select 1 from pg_extension where extname = 'vector')")
        )
        rows = await conn.fetch(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'public'
            """
        )
        tables = {row[0] for row in rows}
        revision = None
        if "alembic_version" in tables:
            revision = await conn.fetchval("select version_num from alembic_version limit 1")
        return {
            "db_name": db_name,
            "user": user,
            "has_vector": bool(has_vector),
            "tables": tables,
            "revision": revision,
        }
    finally:
        await conn.close()


def _format_postgres_check(result: dict[str, object]) -> tuple[bool, str]:
    tables = result["tables"]
    assert isinstance(tables, set)
    missing_tables = sorted(EXPECTED_TABLES - tables)
    revision = result["revision"]
    suffix = "with pgvector" if result["has_vector"] else "without pgvector"

    if missing_tables:
        return (
            False,
            "Postgres reachable but schema is incomplete: missing tables "
            f"{', '.join(missing_tables)}. Run 'alembic upgrade head'.",
        )
    if revision != EXPECTED_ALEMBIC_REVISION:
        return (
            False,
            "Postgres reachable but alembic revision is "
            f"{revision or 'missing'} (expected {EXPECTED_ALEMBIC_REVISION}). "
            "Run 'alembic upgrade head'.",
        )
    return True, (
        f"Postgres reachable: db={result['db_name']}, user={result['user']}, {suffix}, "
        f"schema={revision}"
    )


def check_redis(redis_url: str) -> tuple[bool, str]:
    try:
        from redis import Redis
    except ImportError as exc:  # pragma: no cover - CLI script
        return False, f"Redis check unavailable: install project dependencies first ({exc})"

    try:
        client = Redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5)
        try:
            client.ping()
        finally:
            client.close()
        return True, f"Redis reachable at {redis_url}"
    except Exception as exc:  # pragma: no cover - CLI script
        return False, f"Redis check failed: {exc}"


def check_port(host: str, port: int) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True, f"{host}:{port} is already in use"
    except OSError:
        return False, f"{host}:{port} is free"


def check_http(url: str) -> tuple[bool, str]:
    try:
        with request.urlopen(url, timeout=5) as response:
            return True, f"{url} responded with HTTP {response.status}"
    except error.HTTPError as exc:  # pragma: no cover - CLI script
        body = exc.read().decode("utf-8", errors="replace").strip()
        detail = f" body={body}" if body else ""
        return False, f"{url} responded with HTTP {exc.code}.{detail}"
    except error.URLError as exc:  # pragma: no cover - CLI script
        return False, f"{url} unreachable: {exc.reason}"
    except Exception as exc:  # pragma: no cover - CLI script
        return False, f"{url} check failed: {exc}"


def load_settings() -> tuple[str, str]:
    sys.path.insert(0, str(PROJECT_ROOT))
    from app.config import settings  # pylint: disable=import-outside-toplevel

    return settings.database_url, settings.redis_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Phase 1 preflight checks.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to check for the API port")
    parser.add_argument("--port", type=int, default=8000, help="API port to check")
    parser.add_argument(
        "--require-api",
        action="store_true",
        help="Fail if the FastAPI server is not running and healthy",
    )
    args = parser.parse_args()

    database_url, redis_url = load_settings()

    failures = 0
    infra_checks = [
        ("Env file", *check_env_file()),
        ("Postgres", *check_postgres(database_url)),
        ("Redis", *check_redis(redis_url)),
    ]

    for name, ok, message in infra_checks:
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {name}: {message}")
        if not ok:
            failures += 1

    port_in_use, port_message = check_port(args.host, args.port)
    if port_in_use:
        print(f"[INFO] API port: {port_message}")
        health_ok, health_message = check_http(f"http://{args.host}:{args.port}/health")
        ready_ok, ready_message = check_http(f"http://{args.host}:{args.port}/health/ready")
        print(f"[{'OK' if health_ok else 'FAIL'}] Health: {health_message}")
        print(f"[{'OK' if ready_ok else 'FAIL'}] Ready: {ready_message}")
        if not health_ok or not ready_ok:
            failures += 1
    else:
        label = "FAIL" if args.require_api else "INFO"
        print(f"[{label}] API port: {port_message}")
        if args.require_api:
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
