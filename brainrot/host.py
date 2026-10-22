"""Prevent two independent local-media computers from consuming the same queue."""
import hashlib
import socket
import threading
import time

from . import db, media
from .observability.logging import event


def key():
    return hashlib.sha256(f"{socket.gethostname()}:{media.root()}".encode()).hexdigest()


def acquire(host_key):
    return bool(db.client().rpc("acquire_local_media_host", {"p_host": host_key}).execute().data)


class Keeper(threading.Thread):
    def __init__(self, host_key):
        super().__init__(daemon=True, name="local-media-host")
        self.host_key = host_key
        self.halt = threading.Event()
        self.confirmed_at = time.monotonic()
        self.lost = False

    def run(self):
        while not self.halt.wait(30):
            try:
                if not acquire(self.host_key):
                    self.lost = True
                    return
                self.confirmed_at = time.monotonic()
            except Exception as error:
                event("local_media_host_renewal_failed", error_type=type(error).__name__)

    def valid(self):
        return not self.lost and time.monotonic() - self.confirmed_at < 90

    def stop(self):
        self.halt.set()
        self.join(timeout=10)
