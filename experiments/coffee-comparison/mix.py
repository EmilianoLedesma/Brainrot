"""Mix the unchanged Brainrot voice with quiet Lemo procedural sounds."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import soundfile as sf

HERE=Path(__file__).resolve().parent
out=Path(sys.argv[1]).resolve()
spec=importlib.util.spec_from_file_location("lemo_sfx",HERE/"vendor/lemo-opuscar/core/audio/sfx.py")
sfx=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sfx)
pcm=subprocess.run(["ffmpeg","-v","error","-i",str(out/"shared/narration.mp3"),
                    "-f","f32le","-ar","48000","-ac","1","pipe:1"],capture_output=True,check=True).stdout
voice=np.frombuffer(pcm,dtype='<f4').copy()
buf=np.column_stack((voice,voice))
events=json.loads((out/"lemo/events.json").read_text(encoding="utf-8"))["ev"]
for e in events:
    at=e["t"]
    if e["type"]=="pour":
        sound=sfx.lp(sfx.noise(1.4),1800)*np.sin(np.linspace(0,np.pi,round(48000*1.4)))**2
        sound=sfx.norm(sound)
        sfx.add(buf,sound,at,gain=.008)
    elif e["type"]=="grind":
        for i in range(5):sfx.add(buf,sfx.clack(.7+i*.12),at+i*.14,gain=.018)
    elif e["type"]=="heat":
        sfx.add(buf,sfx.pop(),at,gain=.018)
    else:
        sfx.add(buf,sfx.click(.6),at,gain=.018)
sf.write(out/"lemo/mix.wav",buf,48000,subtype="PCM_24")
print(f"Mixed {len(events)} low-level cues under unchanged voice; no music bed")
