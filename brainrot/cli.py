"""Small operator commands. Run with: python -m brainrot.cli <command>"""

import argparse
import pathlib
import subprocess
import sys

from . import db, publish, reddit, scheduler


def duration_seconds(path: pathlib.Path) -> float | None:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def add_background(args: argparse.Namespace) -> None:
    path = pathlib.Path(args.file)
    label = args.label or path.stem
    storage_path = f"backgrounds/{path.name}"
    db.upload(storage_path, path.read_bytes(), "video/mp4")
    db.client().table("background_clips").insert(
        {
            "label": label,
            "storage_path": storage_path,
            "duration_seconds": duration_seconds(path),
            "tags": args.tags.split(",") if args.tags else [],
        }
    ).execute()
    print(f"added background {label} at {storage_path}")


def scan_reddit(args: argparse.Namespace) -> None:
    job_ids = reddit.scan(max_jobs=args.max)
    print(f"queued {len(job_ids)} reddit jobs" if job_ids else "no qualifying posts")
    for job_id in job_ids:
        print(f"  {job_id}")


def tick(args: argparse.Namespace) -> None:
    for chapter_id in scheduler.tick():
        print(f"scheduled chapter {chapter_id}")
    pending = scheduler.due()
    print(f"{len(pending)} publication(s) due now")
    for row in pending:
        target = row["chapter_id"] or row["clip_id"]
        print(f"  {row['platform']} {target} at {row['scheduled_at']}")


def publish_due(args: argparse.Namespace) -> None:
    sent = publish.run_due(limit=args.max)
    print(f"published {len(sent)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brainrot")
    sub = parser.add_subparsers(dest="command", required=True)

    background = sub.add_parser("add-background", help="upload a looping background clip")
    background.add_argument("file")
    background.add_argument("--label")
    background.add_argument("--tags", help="comma separated")
    background.set_defaults(func=add_background)

    scan = sub.add_parser("scan-reddit", help="queue jobs for qualifying subreddit posts")
    scan.add_argument("--max", type=int, default=3)
    scan.set_defaults(func=scan_reddit)

    ticker = sub.add_parser("tick", help="advance chapter pacing and list due publications")
    ticker.set_defaults(func=tick)

    poster = sub.add_parser("publish", help="upload every publication that is due")
    poster.add_argument("--max", type=int, default=5)
    poster.set_defaults(func=publish_due)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
