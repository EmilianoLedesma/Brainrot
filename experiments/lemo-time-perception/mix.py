"""Narration with Lemo pencil foley and sonification of verified count anchors."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[2];out=Path(sys.argv[1]).resolve()
spec=importlib.util.spec_from_file_location('sfx',ROOT/'experiments/coffee-comparison/vendor/lemo-opuscar/core/audio/sfx.py')
sfx=importlib.util.module_from_spec(spec);spec.loader.exec_module(sfx)
pcm=subprocess.run(['ffmpeg','-v','error','-i',str(out/'narration.mp3'),'-ar','48000','-ac','1','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
voice=np.frombuffer(pcm,dtype='<f4').copy();buf=np.column_stack((voice,voice));sr=48000
events=json.loads((out/'events.json').read_text())['ev'];used=0
for e in events:
    at=float(e['t']);kind=str(e.get('type','tap')).lower()
    if at<0 or at>=len(voice)/sr or 'silence' in kind:continue
    value=e.get('value')
    if isinstance(value,(int,float)) and value in [499,293,263,262,120,20]:
        midi=48+np.log2(1+value)*2.4;f=440*2**((midi-69)/12)
        t=np.arange(round(sr*.48))/sr
        note=np.sin(2*np.pi*f*t+.25*np.sin(2*np.pi*f*2*t)*np.exp(-t*8))*np.exp(-t*8)*np.minimum(1,t/.006)
        sfx.add(buf,note,at,gain=.012)
    elif any(w in kind for w in ['sweep','morph','fold','stretch','ruler','whoosh']):
        sfx.add(buf,sfx.whoosh(.25),at,gain=.013)
    elif any(w in kind for w in ['scratch','write','pencil','graphite']):
        n=sfx.lp(sfx.noise(.18),2600)*np.sin(np.linspace(0,np.pi,round(sr*.18)))**2
        sfx.add(buf,sfx.norm(n),at,gain=.006)
    elif any(w in kind for w in ['flip','click','ratchet','strike']):sfx.add(buf,sfx.clack(.8),at,gain=.014)
    else:sfx.add(buf,sfx.click(.8),at,gain=.012)
    used+=1
sf.write(out/'mix.wav',buf,sr,subtype='PCM_24')
print(f'Mixed {used} event cues, unchanged voice; pitches only for verified count values')
