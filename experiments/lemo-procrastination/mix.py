"""Original sparse jazz-like synthesis and event-timed Lemo foley under narration."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[2];out=Path(sys.argv[1]).resolve()
spec=importlib.util.spec_from_file_location('lemo_sfx',ROOT/'experiments/coffee-comparison/vendor/lemo-opuscar/core/audio/sfx.py')
sfx=importlib.util.module_from_spec(spec);spec.loader.exec_module(sfx)
pcm=subprocess.run(['ffmpeg','-v','error','-i',str(out/'narration.mp3'),'-ar','48000','-ac','1','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
voice=np.frombuffer(pcm,dtype='<f4').copy();buf=np.column_stack((voice,voice))
data=json.loads((out/'data.json').read_text());sr=48000

def note(midi,duration=1.1):
    t=np.arange(round(sr*duration))/sr;f=440*2**((midi-69)/12)
    # Soft vibraphone-like partials, not a sampled melody from the library.
    y=(np.sin(2*np.pi*f*t)*np.exp(-t*3)+.23*np.sin(2*np.pi*f*4*t)*np.exp(-t*9))
    return y*np.minimum(1,t/.008)

for i,beat in enumerate(data['beats']):
    start=beat['start'];length=beat['end']-start
    if i not in [6,14,15]:
        for j,midi in enumerate([60,67,70] if i<15 else [62,69,72]):
            sfx.add(buf,note(midi),start+.8+j*.21,gain=.0045,pan=(j-1)*.25)
    # Gentle room tone is omitted entirely for the two turning-point pauses.
    if i not in [6,14]:
        tone=sfx.lp(sfx.noise(length),400)
        sfx.add(buf,sfx.norm(tone),start,gain=.0007)

for e in data['events']:
    at=e['t'];kind=e['type']
    if kind in ['swish','iris']:
        sfx.add(buf,sfx.whoosh(.26),at,gain=.012 if kind=='iris' else .008)
    elif kind=='buzz':
        t=np.arange(round(sr*.28))/sr
        y=np.sin(2*np.pi*125*t)*np.sin(np.pi*t/.28)**2
        sfx.add(buf,y,at,gain=.008)
    elif kind=='paper':sfx.add(buf,sfx.creak(),at,gain=.008)
    elif kind in ['key','tap']:sfx.add(buf,sfx.click(.7 if kind=='key' else .5),at,gain=.014)
    else:sfx.add(buf,sfx.clack(.6),at,gain=.005)

sf.write(out/'mix.wav',buf,sr,subtype='PCM_24')
print(f'Mixed unchanged voice, {len(data["events"])} restrained cues and original sparse motifs')
