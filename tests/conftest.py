import pytest

from brainrot import db
from tests.fakes import fake_supabase


@pytest.fixture
def fake_db(monkeypatch):
    """Point every `db.client()` call at an in-memory fake for the test."""
    fake = fake_supabase()
    monkeypatch.setattr(db, "client", lambda: fake)
    return fake
