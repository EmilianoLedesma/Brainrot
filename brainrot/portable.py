"""Verified, credential-free-by-layout media handoff between local checkouts."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

from . import db, media

ROOTS = {"backgrounds", "stories", "clips", "sources", "models", "library"}


def _allowed(relative):
    media.path(relative)
    parts = relative.split("/")
    if parts[0] not in ROOTS or any(part in {".env", ".brainrot", ".locks"} or part.endswith(".incomplete") for part in parts):
        raise ValueError("Transfer contains a non-media path")


def _digest(stream):
    result = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        result.update(chunk)
    return result.hexdigest()


def project_id():
    return hashlib.sha256(os.getenv("SUPABASE_URL", "").rstrip("/").encode()).hexdigest()


def referenced_paths():
    paths = set()
    for table, columns in (("background_clips", ("storage_path",)), ("story_chapters", ("audio_path", "video_path")),
                           ("clips", ("storage_path",)), ("source_videos", ("storage_path",))):
        offset = 0
        while True:
            rows = db.client().table(table).select(",".join(columns)).order("id").range(offset, offset + 499).execute().data
            for row in rows:
                paths.update(row[column] for column in columns if row.get(column))
            if len(rows) < 500:
                break
            offset += 500
    return sorted(paths)


def check_media():
    paths = referenced_paths()
    missing = [path for path in paths if not media.path(path).is_file()]
    return {"referenced": len(paths), "missing": missing}


def require_idle():
    running = db.client().table("jobs").select("id").eq("status", "running").limit(1).execute().data
    uploading = db.client().table("publications").select("id").eq("status", "uploading").limit(1).execute().data
    if running or uploading:
        raise ValueError("Wait for running jobs/uploads to finish and stop workers before transferring media")


def export_bundle(destination):
    if not media.local():
        raise ValueError("Media handoff requires the local storage backend")
    destination = Path(destination).resolve()
    if destination.is_relative_to(media.root()):
        raise ValueError("Save the transfer archive outside the media folder")
    if destination.exists():
        raise FileExistsError("Transfer archive already exists; choose a new filename")
    destination.parent.mkdir(parents=True, exist_ok=True)
    files, aliases = [], set()
    for file in sorted(media.root().rglob("*")):
        if not file.is_file():
            continue
        relative = file.relative_to(media.root()).as_posix()
        if relative.split("/")[0] not in ROOTS or any(part == ".locks" or part.endswith(".incomplete") for part in file.parts):
            continue
        _allowed(relative)
        if relative.casefold() in aliases:
            raise ValueError("Media filenames differ only by case and are not portable")
        aliases.add(relative.casefold())
        files.append((relative, file))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
        manifest = {"format": 1, "project": project_id(), "files": []}
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for relative, file in files:
                # Hash exactly the bytes archived, even if another process replaces the path.
                with file.open("rb") as source, archive.open("files/" + relative, "w", force_zip64=True) as target:
                    digest, size = hashlib.sha256(), 0
                    while chunk := source.read(1024 * 1024):
                        target.write(chunk); digest.update(chunk); size += len(chunk)
                manifest["files"].append({"path": relative, "size": size, "sha256": digest.hexdigest()})
            archive.writestr("manifest.json", json.dumps(manifest))
        os.replace(temporary, destination)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return {"files": len(files), "archive": str(destination)}


def import_bundle(source, *, overwrite=False):
    if not media.local():
        raise ValueError("Media handoff requires the local storage backend")
    with zipfile.ZipFile(source) as archive:
        if archive.getinfo("manifest.json").file_size > 10_000_000:
            raise ValueError("Transfer manifest is too large")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != 1 or manifest.get("project") != project_id():
            raise ValueError("This archive belongs to a different Supabase project or unsupported format")
        expected, aliases, entries = {"manifest.json"}, set(), manifest.get("files", [])
        for entry in entries:
            relative = entry["path"]
            _allowed(relative)
            if relative.casefold() in aliases or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]):
                raise ValueError("Transfer manifest has duplicate paths or invalid checksums")
            aliases.add(relative.casefold())
            name = "files/" + relative
            expected.add(name)
            if archive.getinfo(name).file_size != entry["size"]:
                raise ValueError("Transfer size does not match its manifest")
            with archive.open(name) as stream:
                if _digest(stream) != entry["sha256"]:
                    raise ValueError("Transfer checksum does not match its manifest")
            existing = media.path(relative)
            if existing.is_file() and not overwrite:
                with existing.open("rb") as stream:
                    if _digest(stream) != entry["sha256"]:
                        raise FileExistsError("Local media differs from the transfer; use --overwrite only after choosing the authoritative copy")
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != expected:
            raise ValueError("Transfer archive includes unexpected or duplicate files")
        for entry in entries:
            with archive.open("files/" + entry["path"]) as stream:
                media.save_stream(entry["path"], stream, expected_hash=entry["sha256"])
    return {"files": len(entries), "root": str(media.root())}
