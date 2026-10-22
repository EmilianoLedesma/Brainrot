from io import BytesIO
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from brainrot import media, portable, models, render, dev


@pytest.fixture
def computer(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAINROT_MEDIA_STORAGE", "local")
    monkeypatch.setenv("BRAINROT_MEDIA_ROOT", str(tmp_path / "computer-a" / "media"))
    return tmp_path


def test_media_roundtrip_between_different_computers_and_repeated_import(computer, monkeypatch):
    media.save("backgrounds/parkour.mp4", b"background")
    media.save("stories/story/01.mp4", b"finished output")
    media.save("stories/story/01.srt", b"captions")
    media.save("library/nasa/item.json", b'{"credit":"NASA"}')
    # Project credentials and OAuth state are outside the transferable media tree.
    (media.root() / ".env").write_text("SECRET=not-media")
    archive = computer / "handoff.zip"
    assert portable.export_bundle(archive)["files"] == 4
    monkeypatch.setenv("BRAINROT_MEDIA_ROOT", str(computer / "computer-b" / "media"))
    assert portable.import_bundle(archive)["files"] == 4
    assert media.path("stories/story/01.mp4").read_bytes() == b"finished output"
    assert media.path("stories/story/01.srt").read_bytes() == b"captions"
    assert not (media.root() / ".env").exists()
    assert portable.import_bundle(archive)["files"] == 4


def test_handoff_conflicts_require_explicit_authoritative_copy(computer, monkeypatch):
    media.save("clips/one.mp4", b"new")
    archive = computer / "handoff.zip"
    portable.export_bundle(archive)
    media.save("clips/one.mp4", b"local work")
    with pytest.raises(FileExistsError):
        portable.import_bundle(archive)
    assert media.path("clips/one.mp4").read_bytes() == b"local work"
    portable.import_bundle(archive, overwrite=True)
    assert media.path("clips/one.mp4").read_bytes() == b"new"


@pytest.mark.parametrize("relative", ["../outside.mp4", "clips/../../outside.mp4", "clips\\outside.mp4", "clips//one.mp4", "clips/CON.mp4", "clips/bad. ", ".env", "models/.env", *[f"clips/bad{character}.mp4" for character in '<>"|?*']])
def test_handoff_rejects_nonportable_paths_before_writing(computer, relative):
    archive = computer / "bad.zip"
    content = b"bad"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("manifest.json", json.dumps({"format": 1, "project": portable.project_id(), "files": [{"path": relative, "size": len(content), "sha256": hashlib.sha256(content).hexdigest()}]}))
        output.writestr("files/" + relative, content)
    with pytest.raises(ValueError):
        portable.import_bundle(archive)
    assert not (computer / "outside.mp4").exists()


def test_transfer_corruption_and_wrong_project_do_not_replace_local_files(computer, monkeypatch):
    archive = computer / "bad.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("manifest.json", json.dumps({"format": 1, "project": portable.project_id(), "files": [{"path": "clips/one.mp4", "size": 3, "sha256": "0" * 64}]}))
        output.writestr("files/clips/one.mp4", b"bad")
    media.save("clips/one.mp4", b"good")
    with pytest.raises(ValueError, match="checksum"):
        portable.import_bundle(archive, overwrite=True)
    assert media.path("clips/one.mp4").read_bytes() == b"good"
    monkeypatch.setenv("SUPABASE_URL", "https://another-project.example")
    with pytest.raises(ValueError, match="different"):
        portable.import_bundle(archive)


def test_media_audit_paginates_all_references(computer, fake_db):
    fake_db.table("clips").insert([{"storage_path": f"clips/{i}.mp4"} for i in range(1005)]).execute()
    media.save("clips/0.mp4", b"one")
    result = portable.check_media()
    assert result["referenced"] == 1005 and len(result["missing"]) == 1004


def test_stream_checksum_failure_preserves_existing_output(computer):
    media.save("clips/one.mp4", b"good")
    with pytest.raises(ValueError):
        media.save_stream("clips/one.mp4", BytesIO(b"bad"), expected_hash="0" * 64)
    assert media.path("clips/one.mp4").read_bytes() == b"good"


def test_fresh_computer_bootstraps_verified_face_model_in_its_media_folder(computer, fake_db, monkeypatch):
    content = b"verified detector"
    monkeypatch.setattr(models, "FACE_MODEL_SHA256", hashlib.sha256(content).hexdigest())
    calls = []
    monkeypatch.setattr(models, "fetch_face_model", lambda: calls.append(1) or content)
    first = models.ensure_face_model()
    assert Path(first).is_relative_to(media.root())
    assert models.ensure_face_model() == first and len(calls) == 1


def test_captions_use_bundled_font_and_copy_it_to_render_workdir(tmp_path):
    render.install_fonts(tmp_path)
    assert (tmp_path / "fonts" / render.CAPTION_FONT.name).read_bytes() == render.CAPTION_FONT.read_bytes()
    assert "Style: Pop,Anton," in render.build_captions([])


def test_checkout_env_loading_ignores_unrelated_current_directory(tmp_path):
    root = Path(__file__).resolve().parents[1]
    checkout, other = tmp_path / "checkout", tmp_path / "other"
    (checkout / "brainrot").mkdir(parents=True)
    other.mkdir()
    for name in ("config.py", "media.py", "__init__.py"):
        shutil.copyfile(root / "brainrot" / name, checkout / "brainrot" / name)
    (checkout / ".env").write_text("BRAINROT_MEDIA_ROOT=portable-media\n")
    (other / ".env").write_text("BRAINROT_MEDIA_ROOT=wrong-folder\n")
    environment = {key: value for key, value in os.environ.items() if key != "BRAINROT_MEDIA_ROOT"}
    environment["PYTHONPATH"] = str(checkout)
    result = subprocess.run([sys.executable, "-c", "from brainrot import media; print(media.root())"], cwd=other, env=environment, capture_output=True, text=True, check=True)
    assert Path(result.stdout.strip()) == checkout / "portable-media"


def test_bootstrap_preserves_existing_secrets_and_settings(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("bootstrap_test", root / "scripts/bootstrap.py")
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    (tmp_path / "web").mkdir()
    (tmp_path / ".env.example").write_text("DASHBOARD_API_KEY=\n")
    bootstrap.configure()
    original = (tmp_path / ".env").read_text()
    assert len(original.strip().split("=", 1)[1]) > 30
    (tmp_path / "web/.env").write_text("custom frontend")
    bootstrap.configure()
    assert (tmp_path / ".env").read_text() == original
    assert (tmp_path / "web/.env").read_text() == "custom frontend"


def test_launcher_uses_own_checkout_and_injects_matching_frontend_settings(monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_KEY", "private-local-key")
    environment = dev.environment(8123, 5199)
    assert environment["VITE_API_URL"] == "http://127.0.0.1:8123"
    assert environment["VITE_API_KEY"] == "private-local-key"
    assert "http://localhost:5199" in environment["DASHBOARD_ORIGINS"]
    assert dev.commands(8123, 5199)["api"][-1] == "8123"


def test_local_media_host_fences_other_computers_and_expired_claims(pg):
    first, second = "a" * 64, "b" * 64
    assert pg.execute("select acquire_local_media_host(%s) as acquired", (first,)).fetchone()["acquired"]
    assert not pg.execute("select acquire_local_media_host(%s) as acquired", (second,)).fetchone()["acquired"]
    job = pg.execute("insert into jobs(kind) values('brainrot') returning id").fetchone()["id"]
    assert not pg.execute("select * from claim_job_on_local_host('worker-b',%s)", (second,)).fetchall()
    assert pg.execute("select * from claim_job_on_local_host('worker-a',%s)", (first,)).fetchone()["id"] == job
    pg.execute("update local_media_host set expires_at=now()-interval '1 minute'")
    assert not pg.execute("select acquire_local_media_host(%s) as acquired", (second,)).fetchone()["acquired"]
    pg.execute("select complete_job(%s,'worker-a')", (job,))
    assert pg.execute("select acquire_local_media_host(%s) as acquired", (second,)).fetchone()["acquired"]
    assert not pg.execute("select * from claim_job_on_local_host('worker-a',%s)", (first,)).fetchall()
    assert not pg.execute("select has_function_privilege('anon','acquire_local_media_host(text)','execute') as allowed").fetchone()["allowed"]


def test_worker_stops_publishing_if_host_is_lost_during_generation(monkeypatch):
    from brainrot import worker
    from types import SimpleNamespace

    confirmations = iter((True, False))
    keeper = SimpleNamespace(valid=lambda: next(confirmations))
    monkeypatch.setattr(worker, "run_once", lambda **kwargs: True)
    publications = []
    monkeypatch.setattr(worker, "housekeeping", lambda: publications.append(1))
    with pytest.raises(RuntimeError, match="lost its local-media"):
        worker._loop("a" * 64, keeper)
    assert not publications
