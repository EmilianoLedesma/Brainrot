import os
import pathlib
import shutil
import socket
import subprocess
import tempfile

import pytest

from brainrot import db
from tests.fakes import fake_supabase


@pytest.fixture
def fake_db(monkeypatch):
    """Point every `db.client()` call at an in-memory fake for the test."""
    fake = fake_supabase()
    monkeypatch.setattr(db, "client", lambda: fake)
    return fake


# --- throwaway Postgres -------------------------------------------------------
# SQL that only matters inside Postgres (atomic claims, leases, unique keys) is
# tested against a real server rather than the fake. Tests using `pg` skip when
# the binaries are missing.

ROOT = pathlib.Path(__file__).resolve().parent.parent
PG_BIN = pathlib.Path(os.getenv("PG_BIN", "/usr/lib/postgresql/16/bin"))
MIGRATIONS = sorted((ROOT / "migrations").glob("*.sql"))


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def pg_server():
    psycopg = pytest.importorskip("psycopg")
    if not (PG_BIN / "initdb").exists():
        pytest.skip(f"no Postgres binaries in {PG_BIN}")

    # Postgres refuses to run as root, so under root it runs as `postgres`.
    as_user = ["runuser", "-u", "postgres", "--"] if os.geteuid() == 0 else []
    root = pathlib.Path(tempfile.mkdtemp(prefix="brainrot-pg-"))
    root.chmod(0o755)
    if as_user:
        shutil.chown(root, "postgres", "postgres")
    data, port = root / "data", _free_port()

    def run(*args):
        subprocess.run([*as_user, *args], check=True, capture_output=True)

    run(str(PG_BIN / "initdb"), "-D", str(data), "-U", "postgres", "--auth=trust", "-E", "UTF8")
    run(str(PG_BIN / "pg_ctl"), "-D", str(data), "-l", str(root / "log"), "-w",
        "-o", f"-p {port} -k {root} -c listen_addresses=''", "start")
    dsn = f"host={root} port={port} user=postgres"
    try:
        with psycopg.connect(f"{dsn} dbname=postgres", autocommit=True) as conn:
            conn.execute("create database template_brainrot")
        with psycopg.connect(f"{dsn} dbname=template_brainrot", autocommit=True) as conn:
            conn.execute((ROOT / "tests" / "supabase_stub.sql").read_text())
            for migration in MIGRATIONS:
                conn.execute(migration.read_text())
        yield dsn
    finally:
        run(str(PG_BIN / "pg_ctl"), "-D", str(data), "-m", "immediate", "stop")
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def pg(pg_server, request):
    """A fresh database with every migration applied, as a dict-row connection."""
    import psycopg
    from psycopg.rows import dict_row

    name = "t_" + format(abs(hash(request.node.nodeid)), "x")
    with psycopg.connect(f"{pg_server} dbname=postgres", autocommit=True) as admin:
        admin.execute(f"drop database if exists {name}")
        admin.execute(f"create database {name} template template_brainrot")
    conn = psycopg.connect(f"{pg_server} dbname={name}", autocommit=True, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()
        with psycopg.connect(f"{pg_server} dbname=postgres", autocommit=True) as admin:
            admin.execute(f"drop database {name} with (force)")
