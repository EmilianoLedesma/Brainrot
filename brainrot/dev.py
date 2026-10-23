"""Start this checkout's local API, worker and frontend without OS-specific shells."""
import argparse
import os
import signal
import shutil
import subprocess
import sys
import time

from . import media, portable
from .config import PROJECT_ROOT
from .render import CAPTION_FONT


def commands(api_port=8001, web_port=5173):
    node = shutil.which("node")
    vite = PROJECT_ROOT / "web/node_modules/vite/bin/vite.js"
    return {"api": [sys.executable, "-m", "uvicorn", "brainrot.api:app", "--host", "127.0.0.1", "--port", str(api_port)],
            "worker": [sys.executable, "-m", "brainrot.worker"],
            "web": [node or "node", str(vite), "--host", "127.0.0.1", "--port", str(web_port), "--strictPort"]}


def environment(api_port, web_port):
    value = os.environ.copy()
    value["VITE_API_URL"] = f"http://127.0.0.1:{api_port}"
    value["VITE_API_KEY"] = os.getenv("DASHBOARD_API_KEY", "")
    origins = set(filter(None, value.get("DASHBOARD_ORIGINS", "").split(",")))
    origins.update((f"http://localhost:{web_port}", f"http://127.0.0.1:{web_port}"))
    value["DASHBOARD_ORIGINS"] = ",".join(sorted(origins))
    return value


def stop(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name != "nt": os.killpg(process.pid, signal.SIGKILL)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("service", nargs="?", choices=("all", "api", "worker", "web"), default="all")
    parser.add_argument("--api-port", type=int, default=8001)
    parser.add_argument("--web-port", type=int, default=5173)
    parser.add_argument("--check", action="store_true", help="validate local prerequisites without starting processes")
    args = parser.parse_args(argv)
    if not all(1 <= port <= 65535 for port in (args.api_port, args.web_port)):
        parser.error("Ports must be between 1 and 65535")
    services = ("api", "worker", "web") if args.service == "all" else (args.service,)
    if not all(os.getenv(key) for key in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "DASHBOARD_API_KEY")):
        raise SystemExit("Fill in SUPABASE_URL, SUPABASE_SERVICE_KEY and DASHBOARD_API_KEY in this checkout's .env")
    if "worker" in services and (not shutil.which("ffmpeg") or not shutil.which("ffprobe") or not CAPTION_FONT.is_file()):
        raise SystemExit("Install FFmpeg/ffprobe and restore the bundled caption font before starting the worker")
    if "web" in services and (not shutil.which("node") or not (PROJECT_ROOT / "web/node_modules/vite/bin/vite.js").is_file()):
        raise SystemExit("Run scripts/bootstrap.py to install frontend dependencies")
    if args.check:
        print("Local prerequisites available; no processes started")
        return 0
    if "worker" in services and media.local():
        report = portable.check_media()
        if report["missing"]:
            raise SystemExit(f"{len(report['missing'])} referenced media files are missing on this computer. Import your handoff archive, or run doctor --check-media for details.")
    processes = []
    try:
        for service in services:
            process = subprocess.Popen(commands(args.api_port, args.web_port)[service],
                cwd=PROJECT_ROOT / "web" if service == "web" else PROJECT_ROOT,
                env=environment(args.api_port, args.web_port), creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if os.name == "nt" else 0,
                start_new_session=os.name != "nt")
            processes.append(process)
        print(f"Dashboard: http://localhost:{args.web_port} · API: http://127.0.0.1:{args.api_port}", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        return next((process.returncode for process in processes if process.returncode), 0)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in reversed(processes): stop(process)


if __name__ == "__main__":
    raise SystemExit(main())
