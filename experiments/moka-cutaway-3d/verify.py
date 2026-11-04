"""Contact sheet before the render, measurements of the rendered MP4 after it. Needs Node deps, npx and ffmpeg only.

  python experiments/moka-cutaway-3d/verify.py --stills   # 10 stills (incl. the steam event) -> contact-sheet.jpg
  python experiments/moka-cutaway-3d/verify.py            # measure out/moka-cutaway-3d/final.mp4
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "out" / "moka-cutaway-3d"
SCRIPT = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
FRAMES = SCRIPT["stillFrames"]


def sheet(paths, target):
    """Two rows of five, 432x768 each, with ffmpeg xstack."""
    inputs = [a for p in paths for a in ("-i", str(p))]
    scale = ";".join(f"[{i}]scale=432:768[a{i}]" for i in range(len(paths)))
    layout = "|".join(f"{'+'.join(['w0'] * (i % 5)) or '0'}_{'h0' if i >= 5 else '0'}" for i in range(len(paths)))
    chain = "".join(f"[a{i}]" for i in range(len(paths)))
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", f"{scale};{chain}xstack=inputs={len(paths)}:layout={layout}", str(target)], check=True)


def stills():
    npx = shutil.which("npx")
    folder = OUT / "stills"
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for fr in FRAMES:
        path = folder / f"f{fr:03}.png"
        subprocess.run([npx, "remotion", "still", "index.tsx", "MokaCutaway", str(path), f"--frame={fr}", "--gl=angle"], cwd=HERE, check=True, capture_output=True)
        paths.append(path)
    sheet(paths, OUT / "contact-sheet.jpg")
    print("frames", FRAMES, "->", OUT / "contact-sheet.jpg")


def measure():
    video = OUT / "final.mp4"
    info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate", "-of", "json", str(video)], text=True))
    picture = next(s for s in info["streams"] if s["codec_type"] == "video")
    duration = float(info["format"]["duration"])
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    assert abs(duration - SCRIPT["durationFrames"] / SCRIPT["fps"]) < 0.05, duration
    assert (picture["width"], picture["height"], picture["r_frame_rate"]) == (1080, 1920, "30/1")
    assert picture["codec_name"] == "h264" and not has_audio
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True, check=True)
    assert not decode.stderr.strip(), decode.stderr
    black = subprocess.run(["ffmpeg", "-i", str(video), "-vf", "blackdetect=d=0.05", "-an", "-f", "null", "-"], capture_output=True, text=True, check=True).stderr.count("black_start")
    verify = OUT / "verify"
    verify.mkdir(exist_ok=True)
    paths = []
    for fr in FRAMES:
        path = verify / f"f{fr:03}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"select=eq(n\\,{fr})", "-frames:v", "1", str(path)], check=True)
        paths.append(path)
    sheet(paths, OUT / "contact-sheet-final.jpg")
    report = {"duration_seconds": duration, "video": picture, "has_audio": has_audio, "black_frames": black, "decode_errors": False,
              "sha256": hashlib.sha256(video.read_bytes()).hexdigest(), "review_status": "Measurements complete; the final contact sheet still needs a visual review."}
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--stills", action="store_true")
    stills() if parser.parse_args().stills else measure()
