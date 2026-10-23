"""Save narration once and map editorial scenes onto its measured word boundaries.

Runs outside the database/worker. Uses Brainrot's existing TTS implementation.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from brainrot import tts
from brainrot.duration import check_media
from brainrot.render import build_srt, check_captions

def normalize(s):
    return re.sub(r'[^a-z0-9]','',s.lower())

def main():
    p=argparse.ArgumentParser(); p.add_argument('--edit-dir',type=Path,default=ROOT/'out/video-use-prototype/edit'); p.add_argument('--story',type=Path,default=HERE/'story.json')
    args=p.parse_args(); edit=args.edit_dir.resolve(); edit.mkdir(parents=True,exist_ok=True)
    story=json.loads(args.story.read_text(encoding='utf-8'))
    script='\n\n'.join(s['text'] for s in story['scenes'])
    fingerprint=hashlib.sha256(json.dumps({'title':story['title'],'script':script,'voice':story['voice'],'tts_source':hashlib.sha256((ROOT/'brainrot/tts.py').read_bytes()).hexdigest()},sort_keys=True).encode()).hexdigest()
    manifest=edit/'narration-cache.json'; audio_path=edit/'narration.mp3'; words_path=edit/'words.json'
    cached=json.loads(manifest.read_text()) if manifest.exists() else {}
    if cached.get('fingerprint')==fingerprint and audio_path.exists() and words_path.exists():
        words=json.loads(words_path.read_text()); print('Reusing saved narration.',flush=True)
    else:
        audio,words=tts.narrate(script,title=story['title'],voice=story['voice'])
        audio_path.write_bytes(audio); words_path.write_text(json.dumps(words,indent=2),encoding='utf-8')
        manifest.write_text(json.dumps({'fingerprint':fingerprint},indent=2))
    seconds=check_media(str(audio_path)); check_captions(words,seconds)
    # Match each scene's first words after the preceding scene. The provider can
    # split punctuation differently, so compare normalized concatenated tokens.
    cursor=0; starts=[]
    for scene in story['scenes']:
        target=''.join(normalize(w) for w in scene['text'].split()[:7])
        found=None
        for i in range(cursor,len(words)):
            value=''
            for j in range(i,min(len(words),i+20)):
                value+=normalize(words[j]['text'])
                if value==target: found=i; break
                if len(value)>len(target): break
            if found is not None: break
        if found is None: raise ValueError('Cannot align scene '+scene['id'])
        starts.append(words[found]['start']); cursor=found+1
    plan=[]
    for i,scene in enumerate(story['scenes']):
        start=0 if i==0 else starts[i]-.10
        end=starts[i+1]-.10 if i+1<len(starts) else seconds
        cues={}
        for name,token in scene.get('cue_after',{}).items():
            matches=[w for w in words if start<=w['start']<end and normalize(w['text'])==normalize(token)]
            if not matches:raise ValueError('Cannot align visual cue '+name)
            cues[name]=round(matches[0]['end']-start+.12,4)
        entry={**scene,'index':i,'start':round(start,4),'end':round(end,4),'duration':round(end-start,4)}
        if cues:entry['cues']=cues
        plan.append(entry)
    (edit/'scene-plan.json').write_text(json.dumps({'title':story['title'],'duration':seconds,'scenes':plan,'sources':story['sources']},indent=2),encoding='utf-8')
    (edit/'narration.txt').write_text(story['title']+'\n\n'+script,encoding='utf-8')
    (edit/'narration.srt').write_text(build_srt(words),encoding='utf-8')
    (edit/'transcripts').mkdir(exist_ok=True)
    transcript={'text':script,'words':[{**w,'type':'word'} for w in words],'provenance':'Brainrot TTS word boundaries; no ASR call'}
    (edit/'transcripts/base.json').write_text(json.dumps(transcript,indent=2),encoding='utf-8')
    print(json.dumps({'words':len(script.split()),'duration':seconds,'scenes':len(plan),'output':str(edit)}),flush=True)

if __name__=='__main__': main()
