"""Portable local media files; the database stores only POSIX relative paths."""
import hashlib
import hmac
import os
from pathlib import Path, PurePosixPath
import tempfile
import threading
import time
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_locks = {}
_guard = threading.Lock()


def file_lock(relative: str):
    key = str(path(relative))
    with _guard:
        return _locks.setdefault(key, threading.RLock())


def local() -> bool:
    mode = os.getenv("BRAINROT_MEDIA_STORAGE", "local")
    if mode not in {"local", "supabase"}:
        raise ValueError("BRAINROT_MEDIA_STORAGE must be local or supabase")
    return mode == "local"


def root() -> Path:
    configured = Path(os.getenv("BRAINROT_MEDIA_ROOT", "media"))
    return (configured if configured.is_absolute() else PROJECT_ROOT / configured).resolve()


def path(relative: str) -> Path:
    parts = PurePosixPath(relative)
    if not relative or "\\" in relative or ":" in relative or parts.is_absolute() or any(p in {".", ".."} for p in relative.split("/")):
        raise ValueError("Invalid media path")
    target = (root() / relative).resolve()
    if not target.is_relative_to(root()) or target == root():
        raise ValueError("Invalid media path")
    return target


def save(relative: str, data: bytes) -> str:
    target = path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(data)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return relative


def signature(relative: str, expires: int) -> str:
    secret = os.getenv("DASHBOARD_API_KEY", "")
    if not secret:
        raise ValueError("Dashboard authentication must be configured")
    path(relative)
    return hmac.new(secret.encode(), f"media:{relative}:{expires}".encode(), hashlib.sha256).hexdigest()


def signed_url(relative: str, seconds: int = 3600) -> str:
    expires = int(time.time()) + min(max(seconds, 1), 86400)
    return f"/media/{quote(relative, safe='/')}?expires={expires}&signature={signature(relative, expires)}"


def verify(relative: str, expires: int, supplied: str) -> bool:
    try:
        return int(time.time()) <= expires <= int(time.time()) + 86400 and hmac.compare_digest(signature(relative, expires), supplied)
    except ValueError:
        return False
