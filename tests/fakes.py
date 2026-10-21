"""An in-memory stand-in for the slice of supabase-py that brainrot uses.

It covers the query-builder calls the modules make (select/insert/update/upsert/
delete, the filters, order, limit, single), rpc, and Storage. Column lists and
embedded selects like `stories(title)` are ignored: every row comes back whole.
Declared unique keys are enforced, so tests catch duplicate inserts the real
database would reject.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace


class UniqueViolation(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _Query:
    def __init__(self, fake: "FakeSupabase", table: str):
        self.fake = fake
        self.table = table
        self.op = "select"
        self.payload = None
        self.filters: list = []
        self.orders: list = []
        self.limit_n: int | None = None
        self.single_row = False
        self.on_conflict = ""
        self.ignore_duplicates = False
        self._negate = False

    # operations ------------------------------------------------------------
    def select(self, *_columns, **_kwargs):
        self.op = "select"
        return self

    def insert(self, rows, **_kwargs):
        self.op, self.payload = "insert", rows
        return self

    def update(self, patch, **_kwargs):
        self.op, self.payload = "update", patch
        return self

    def upsert(self, rows, *, on_conflict: str = "", ignore_duplicates: bool = False, **_kwargs):
        self.op, self.payload = "upsert", rows
        self.on_conflict, self.ignore_duplicates = on_conflict, ignore_duplicates
        return self

    def delete(self):
        self.op = "delete"
        return self

    # filters ---------------------------------------------------------------
    def _add(self, test):
        negate, self._negate = self._negate, False
        self.filters.append((lambda row: not test(row)) if negate else test)
        return self

    @property
    def not_(self):
        self._negate = True
        return self

    def eq(self, column, value):
        return self._add(lambda r: r.get(column) == value)

    def neq(self, column, value):
        return self._add(lambda r: r.get(column) != value)

    def in_(self, column, values):
        values = list(values)
        return self._add(lambda r: r.get(column) in values)

    def lte(self, column, value):
        return self._add(lambda r: r.get(column) is not None and r.get(column) <= value)

    def lt(self, column, value):
        return self._add(lambda r: r.get(column) is not None and r.get(column) < value)

    def gte(self, column, value):
        return self._add(lambda r: r.get(column) is not None and r.get(column) >= value)

    def is_(self, column, value):
        assert value == "null", "fake only supports is_(col, 'null')"
        return self._add(lambda r: r.get(column) is None)

    def order(self, column, desc: bool = False):
        self.orders.append((column, desc))
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def single(self):
        self.single_row = True
        return self

    # execution -------------------------------------------------------------
    def _matching(self) -> list[dict]:
        rows = [r for r in self.fake.tables.setdefault(self.table, []) if all(f(r) for f in self.filters)]
        for column, desc in reversed(self.orders):
            rows.sort(key=lambda r: (r.get(column) is None, r.get(column)), reverse=desc)
        if self.limit_n is not None:
            rows = rows[: self.limit_n]
        return rows

    def execute(self):
        self.fake.calls.append((self.table, self.op))
        data = getattr(self, f"_{self.op}")()
        if self.single_row:
            if len(data) != 1:
                raise LookupError(f"single() matched {len(data)} rows in {self.table}")
            data = data[0]
        return SimpleNamespace(data=data)

    def _select(self):
        return [dict(r) for r in self._matching()]

    def _insert(self):
        rows = self.payload if isinstance(self.payload, list) else [self.payload]
        stored = []
        for row in rows:
            row = {"id": str(uuid.uuid4()), "created_at": _now(), **self.fake.defaults.get(self.table, {}), **row}
            self.fake.check_unique(self.table, row)
            self.fake.tables.setdefault(self.table, []).append(row)
            stored.append(dict(row))
        return stored

    def _update(self):
        changed = []
        for row in self._matching():
            row.update(self.payload)
            changed.append(dict(row))
        return changed

    def _upsert(self):
        rows = self.payload if isinstance(self.payload, list) else [self.payload]
        keys = [c.strip() for c in self.on_conflict.split(",") if c.strip()]
        written = []
        for row in rows:
            existing = self.fake.find_conflict(self.table, keys, row) if keys else None
            if existing is None:
                self.payload = row
                written.extend(self._insert())
            elif not self.ignore_duplicates:
                existing.update(row)
                written.append(dict(existing))
        return written

    def _delete(self):
        doomed = self._matching()
        self.fake.tables[self.table] = [r for r in self.fake.tables[self.table] if r not in doomed]
        return [dict(r) for r in doomed]


class _Bucket:
    def __init__(self, store: dict):
        self.store = store

    def upload(self, path, data, _options=None):
        self.store[path] = data

    def download(self, path):
        return self.store[path]

    def create_signed_url(self, path, _expires):
        return {"signedURL": f"https://storage.test/{path}?token=t"}

    def remove(self, paths):
        for path in paths:
            self.store.pop(path, None)


class FakeSupabase:
    def __init__(self, unique: dict[str, list[tuple[str, ...]]] | None = None,
                 defaults: dict[str, dict] | None = None):
        self.tables: dict[str, list[dict]] = {}
        self.unique = unique or {}
        self.defaults = defaults or {}
        self.files: dict[str, bytes] = {}
        self.functions: dict = {}
        self.calls: list = []
        self.storage = SimpleNamespace(from_=lambda _bucket: _Bucket(self.files))

    def table(self, name: str) -> _Query:
        return _Query(self, name)

    def rpc(self, fn: str, params: dict | None = None):
        result = self.functions[fn](**(params or {}))
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=result))

    def find_conflict(self, table: str, keys: list[str], row: dict) -> dict | None:
        if any(row.get(k) is None for k in keys):
            return None  # NULLs never conflict in Postgres
        for existing in self.tables.get(table, []):
            if all(existing.get(k) == row.get(k) for k in keys):
                return existing
        return None

    def check_unique(self, table: str, row: dict) -> None:
        for keys in self.unique.get(table, []):
            if self.find_conflict(table, list(keys), row) is not None:
                raise UniqueViolation(f"duplicate key on {table}{keys}")

    def rows(self, table: str) -> list[dict]:
        return self.tables.get(table, [])


# Unique keys from migrations/001_init.sql and 002_job_execution.sql.
SCHEMA_UNIQUE = {
    "stories": [("reddit_post_id",), ("job_id",)],
    "source_videos": [("job_id",)],
    "story_chapters": [("story_id", "chapter_index")],
    "publications": [("chapter_id", "platform"), ("clip_id", "platform")],
    "jobs": [("idempotency_key",)],
}
SCHEMA_DEFAULTS = {
    "jobs": {"status": "pending", "error": None},
    "stories": {"status": "pending"},
    "story_chapters": {"status": "pending", "audio_path": None, "video_path": None},
    "clips": {"status": "pending", "storage_path": None},
    "publications": {"status": "scheduled", "clip_id": None, "chapter_id": None,
                     "published_at": None, "platform_post_id": None, "url": None, "error": None},
}


def fake_supabase() -> FakeSupabase:
    fake = FakeSupabase(unique=SCHEMA_UNIQUE, defaults=SCHEMA_DEFAULTS)

    # Minimal RPC behavior for pipeline unit tests; rotation/concurrency itself
    # is verified against the real migration in test_background_rotation.py.
    def assign_background(p_story):
        story = next((s for s in fake.rows("stories") if s["id"] == p_story), None)
        if story is None:
            return None
        clips = fake.rows("background_clips")
        if story.get("background_clip_id"):
            return next(c["storage_path"] for c in clips if c["id"] == story["background_clip_id"])
        active = [c for c in clips if c.get("active", True)]
        if not active:
            return None
        chosen = min(active, key=lambda c: (c.get("last_used_order", 0), c.get("rotation_order", 0), c["created_at"], c["id"]))
        chosen["last_used_order"] = max((c.get("last_used_order", 0) for c in clips), default=0) + 1
        story["background_clip_id"] = chosen["id"]
        return chosen["storage_path"]

    fake.functions["assign_story_background"] = assign_background
    return fake
