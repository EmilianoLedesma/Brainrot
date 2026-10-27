"""Vendor a small audited subset, at a fixed upstream revision; never install globally."""
import hashlib
import json
from pathlib import Path
import urllib.request

SHA = "413a6bd6d78ebd3bdd5abaec9538a26867f890df"
DEST = Path(__file__).resolve().parent / "vendor" / "lemo-opuscar"
FILES = ["LICENSE", "DIRECTOR.md", "TECHNIQUE.md", "core/README.md", "core/lib.js",
         "styles/iso-infographic/STYLE.md", "styles/iso-infographic/DEMO.md",
         "styles/iso-infographic/demo/engine.js", "core/audio/sfx.py",
         *["core/render/" + name for name in
           ["browser.mjs", "events.mjs", "page.mjs", "readcheck.mjs", "serve.mjs",
            "sheet.py", "slot.mjs", "srt.py", "still.mjs", "video.mjs"]]]

if __name__ == "__main__":
    hashes = {}
    for name in FILES:
        url = f"https://raw.githubusercontent.com/lemomo-ai/lemo-opuscar/{SHA}/{name}"
        data = urllib.request.urlopen(url, timeout=30).read()
        target = DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    (DEST / "provenance.json").write_text(json.dumps({
        "repository": "https://github.com/lemomo-ai/lemo-opuscar", "revision": SHA,
        "license": "MIT", "files": hashes}, indent=2) + "\n", encoding="utf-8")
    print(f"Vendored {len(hashes)} files at {SHA}")
