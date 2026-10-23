"""Master narration through video-use without re-encoding the Remotion picture."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/video-use-prototype'))
from build import upstream

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser()
    parser.add_argument('--edit-dir',type=Path,default=ROOT/'out/remotion-explainer/edit')
    edit=parser.parse_args().edit_dir.resolve()
    final=edit/'final.mp4';record=edit/'audio-finish.json'
    current=digest(final)
    if record.exists() and json.loads(record.read_text())['output_sha256']==current:
        print('Reusing mastered output.');return
    renderer=upstream('render')
    renderer.LOUDNORM_I=-16
    renderer.LOUDNORM_TP=-1.5
    renderer.LOUDNORM_LRA=11
    target=edit/'audio-mastered.mp4'
    renderer.apply_loudnorm_two_pass(final,target)
    original=edit/'remotion-unmastered.mp4'
    final.replace(original)
    target.replace(final)
    record.write_text(json.dumps({'input_sha256':current,'output_sha256':digest(final),'integrated_target_lufs':-16,'true_peak_target_dbtp':-1.5,'video_encoding':'copied unchanged','method':'video-use two-pass loudnorm'},indent=2)+'\n',encoding='utf-8')
    print('Mastered audio; original Remotion render retained.')

if __name__=='__main__':main()
