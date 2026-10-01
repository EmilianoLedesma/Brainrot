"""Route supabase-py `rpc()` calls into a real Postgres connection.

Lets the thin wrappers in brainrot/db.py run against the actual SQL functions,
so a renamed argument or a wrong return shape fails a test instead of the
first deploy. Results are JSON-shaped the way PostgREST returns them: a list of
row dicts for set-returning functions, the bare value for scalar ones.
"""

from types import SimpleNamespace


class PgRpcClient:
    def __init__(self, conn):
        self.conn = conn

    def rpc(self, fn: str, params: dict | None = None):
        params = params or {}
        args = ", ".join(f"{name} => %({name})s" for name in params)
        returns_set = self.conn.execute(
            "select proretset from pg_proc where proname = %s", (fn,)
        ).fetchone()["proretset"]
        if returns_set:
            rows = self.conn.execute(f"select to_jsonb(r) as row from {fn}({args}) r", params).fetchall()
            data = [r["row"] for r in rows]
        else:
            data = self.conn.execute(f"select to_jsonb({fn}({args})) as value", params).fetchone()["value"]
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=data))
