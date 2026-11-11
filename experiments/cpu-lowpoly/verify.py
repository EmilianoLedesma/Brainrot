"""Measure the rendered MP4 and pull two contact sheets from it (no Remotion needed): a dense one across the whole duration, and a
high-fps one (a run of frames every 5 = 6 fps) inside one shot of each type to check fluidity within a single shot.

  python experiments/cpu-lowpoly/verify.py
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "out" / "cpu-lowpoly"
SCRIPT = json.loads((HERE / "script.json").read_text(encoding="utf-8"))


def frame_to(video, n, path, size=None):
    vf = f"select=eq(n\\,{n})" + (f",scale={size}" if size else "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", vf, "-frames:v", "1", str(path)], check=True)


def sheet(paths, target, cols, cell):
    w, h = cell
    inputs = [a for p in paths for a in ("-i", str(p))]
    scale = ";".join(f"[{i}]scale={w}:{h}[a{i}]" for i in range(len(paths)))
    layout = "|".join(f"{'+'.join(['w0'] * (i % cols)) or '0'}_{'+'.join(['h0'] * (i // cols)) or '0'}" for i in range(len(paths)))
    chain = "".join(f"[a{i}]" for i in range(len(paths)))
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", f"{scale};{chain}xstack=inputs={len(paths)}:layout={layout}", str(target)], check=True)


def main() -> None:
    video = OUT / "final.mp4"
    info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate", "-of", "json", str(video)], text=True))
    picture = next(s for s in info["streams"] if s["codec_type"] == "video")
    duration = float(info["format"]["duration"])
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    assert abs(duration - SCRIPT["durationFrames"] / SCRIPT["fps"]) < 0.05, duration
    assert 90 <= duration <= 180, duration
    assert (picture["width"], picture["height"], picture["r_frame_rate"]) == (1080, 1920, "30/1")
    assert picture["codec_name"] == "h264" and not has_audio
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True, check=True)
    assert not decode.stderr.strip(), decode.stderr
    black = subprocess.run(["ffmpeg", "-i", str(video), "-vf", "blackdetect=d=0.05", "-an", "-f", "null", "-"], capture_output=True, text=True, check=True).stderr.count("black_start")
    md5 = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", "scale=108:192", "-f", "framemd5", "-"], capture_output=True, text=True, check=True).stdout
    hashes = [line.split(",")[-1].strip() for line in md5.splitlines() if line and not line.startswith("#")]
    repeats = sum(1 for a, b in zip(hashes, hashes[1:]) if a == b)
    longest = run = 0
    for a, b in zip(hashes, hashes[1:]):
        run = run + 1 if a == b else 0
        longest = max(longest, run)
    d = OUT / "verify"
    d.mkdir(parents=True, exist_ok=True)
    dense = []
    for n in SCRIPT["stillFrames"]:
        p = d / f"f{n:04}.png"
        frame_to(video, n, p)
        dense.append(p)
    sheet(dense, OUT / "contact-sheet-dense.jpg", 6, (180, 320))
    fluid = []
    for r in SCRIPT["fluidityRuns"]:
        for k in range(r["count"]):
            n = r["start"] + k * r["step"]
            p = d / f"x{n:04}.png"
            frame_to(video, n, p)
            fluid.append(p)
    sheet(fluid, OUT / "contact-sheet-fluidity.jpg", 12, (135, 240))
    report = {"duration_seconds": duration, "video": picture, "has_audio": has_audio, "black_frames": black, "decode_errors": False,
              "identical_consecutive_frames": repeats, "longest_identical_run": longest, "frames_checked": len(hashes),
              "dense_stills": len(dense), "fluidity_runs": SCRIPT["fluidityRuns"],
              "sha256": hashlib.sha256(video.read_bytes()).hexdigest(), "review_status": "Measurements complete; both contact sheets still need a visual review."}
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
