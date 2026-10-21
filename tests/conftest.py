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
_pg_ctl = shutil.which("pg_ctl")
PG_BIN = pathlib.Path(os.getenv(
    "PG_BIN", str(pathlib.Path(_pg_ctl).parent) if _pg_ctl else "/usr/lib/postgresql/16/bin"
))
PG_EXE = ".exe" if os.name == "nt" else ""
MIGRATIONS = sorted((ROOT / "migrations").glob("*.sql"))


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def pg_server():
    psycopg = pytest.importorskip("psycopg")
    if not (PG_BIN / f"initdb{PG_EXE}").exists():
        pytest.skip(f"no Postgres binaries in {PG_BIN}")

    # Postgres refuses to run as root, so under root it runs as `postgres`.
    as_user = ["runuser", "-u", "postgres", "--"] if os.name != "nt" and os.geteuid() == 0 else []
    root = pathlib.Path(tempfile.mkdtemp(prefix="brainrot-pg-"))
    root.chmod(0o755)
    if as_user:
        shutil.chown(root, "postgres", "postgres")
    data, port = root / "data", _free_port()

    def run(*args):
        # A daemon on Windows can inherit a PIPE and keep communicate() waiting
        # after pg_ctl exits. A file captures diagnostics without waiting on it.
        with tempfile.TemporaryFile() as output:
            result = subprocess.run(
                [*as_user, *args], stdin=subprocess.DEVNULL,
                stdout=output, stderr=subprocess.STDOUT,
            )
            if result.returncode:
                output.seek(0)
                raise RuntimeError(f"Postgres command failed: {output.read().decode(errors='replace')}")

    run(str(PG_BIN / f"initdb{PG_EXE}"), "-D", str(data), "-U", "postgres", "--auth=trust", "-E", "UTF8", "--no-locale")
    # Windows uses loopback TCP; Unix keeps the private socket directory.
    options = f"-p {port} -h 127.0.0.1" if os.name == "nt" else f"-p {port} -k {root} -c listen_addresses=''"
    host = "127.0.0.1" if os.name == "nt" else str(root)
    run(str(PG_BIN / f"pg_ctl{PG_EXE}"), "-D", str(data), "-l", str(root / "log"), "-w",
        "-o", options, "start")
    dsn = f"host={host} port={port} user=postgres"
    try:
        with psycopg.connect(f"{dsn} dbname=postgres", autocommit=True) as conn:
            conn.execute("create database template_brainrot")
        with psycopg.connect(f"{dsn} dbname=template_brainrot", autocommit=True) as conn:
            conn.execute((ROOT / "tests" / "supabase_stub.sql").read_text())
            for migration in MIGRATIONS:
                conn.execute(migration.read_text())
        yield dsn
    finally:
        run(str(PG_BIN / f"pg_ctl{PG_EXE}"), "-D", str(data), "-m", "immediate", "stop")
        assert root.resolve().parent == pathlib.Path(tempfile.gettempdir()).resolve()
        assert root.name.startswith("brainrot-pg-")
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
