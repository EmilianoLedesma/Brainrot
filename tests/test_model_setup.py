from argparse import Namespace
from types import SimpleNamespace

import pytest

from brainrot import cli, models, repurpose
from brainrot.domain.jobs import PermanentError


def test_setup_uploads_the_verified_model_to_the_expected_bucket_path(fake_db, monkeypatch):
    monkeypatch.setattr(models, "fetch_face_model", lambda: b"verified-model")
    cli.setup_face_model(Namespace())
    assert fake_db.files[repurpose.FACE_MODEL_PATH] == b"verified-model"


def test_fetch_rejects_a_wrong_digest_before_upload(monkeypatch):
    monkeypatch.setattr(models.requests, "get", lambda *a, **kw: SimpleNamespace(
        content=b"wrong-model", raise_for_status=lambda: None))
    with pytest.raises(PermanentError, match="checksum"):
        models.fetch_face_model()


def test_failed_download_does_not_poison_the_local_model_cache(fake_db, tmp_path, monkeypatch):
    monkeypatch.setattr(repurpose.tempfile, "gettempdir", lambda: str(tmp_path))
    with pytest.raises(KeyError):
        repurpose.face_model_path()
    assert not (tmp_path / "yunet.onnx").exists()
