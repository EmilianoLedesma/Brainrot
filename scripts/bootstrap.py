"""Repeatable local setup. Run with Python; never overwrites existing settings."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def npm_command():
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("Install Node.js with npm before running setup")
    if os.name == "nt":
        entry = Path(npm).parent / "node_modules/npm/bin/npm-cli.js"
        node = shutil.which("node")
        if not node or not entry.is_file():
            raise RuntimeError("The Node/npm installation is incomplete")
        return [node, str(entry)]
    return [npm]


def configure():
    env = ROOT / ".env"
    if not env.exists():
        content = (ROOT / ".env.example").read_text(encoding="utf-8")
        content = content.replace("DASHBOARD_API_KEY=\n", "DASHBOARD_API_KEY=" + secrets.token_urlsafe(32) + "\n")
        env.write_text(content, encoding="utf-8")
    frontend = ROOT / "web/.env"
    if not frontend.exists():
        frontend.write_text("VITE_API_URL=http://127.0.0.1:8001\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="show setup steps without installing or writing settings")
    args = parser.parse_args()
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("Install uv first: https://docs.astral.sh/uv/getting-started/installation/")
    commands = [[uv, "sync", "--locked", "--python", "3.14"], [*npm_command(), "ci", "--prefix", "web"]]
    if args.check:
        print("Setup available: locked Python environment, npm ci, missing settings templates only")
        return
    environment = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(ROOT / ".venv")}
    for command in commands:
        subprocess.run(command, cwd=ROOT, env=environment, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    configure()
    print("Setup complete. Fill in root .env or securely copy it from your other computer.")
    print("Restore media, then run: uv run --locked python -m brainrot.dev")


if __name__ == "__main__":
    main()
