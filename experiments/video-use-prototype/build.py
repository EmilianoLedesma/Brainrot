"""Render original scenes, then finish through the pinned video-use helpers."""
import argparse
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
HELPERS=HERE/'vendor/video-use/helpers'

def upstream(name):
    sys.path.insert(0,str(HELPERS))
    spec=importlib.util.spec_from_file_location('video_use_'+name,HELPERS/(name+'.py'))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def run(cmd, log):
    with log.open('w',encoding='utf-8') as f:
        subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)

def slot(scene, edit, fps, stills=False):
    from visual import W,H
    module=importlib.import_module(scene['module'])
    module.CUES=scene.get('cues',{})
    folder=edit/'animations'/('slot_'+str(scene['index']+1).zfill(2));folder.mkdir(parents=True,exist_ok=True)
    count=round(scene['end']*fps)-round(scene['start']*fps)
    duration=count/fps
    output=folder/'render.mp4'
    source_files=[HERE/(scene['module']+'.py'),HERE/'visual.py',HERE/'assets/DMSans.ttf']
    fingerprint=hashlib.sha256(json.dumps({'scene':scene,'fps':fps},sort_keys=True).encode()+b''.join(p.read_bytes() for p in source_files)).hexdigest()
    manifest=folder/'cache.json'
    if not stills and output.exists() and manifest.exists() and json.loads(manifest.read_text()).get('fingerprint')==fingerprint:
        print('Reusing scene',scene['index']+1,flush=True);return output
    for fraction,label in ((.08,'early'),(.50,'middle'),(.90,'late')):
        module.render(scene['index'],duration*fraction,duration).save(folder/(label+'.jpg'),quality=90)
    (folder/'reasoning.json').write_text(json.dumps({'scene':scene,'frame_count':count,'fps':fps,'fingerprint':fingerprint},indent=2),encoding='utf-8')
    if stills:return output
    command=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','20','-maxrate','1800k','-bufsize','3600k','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    with (folder/'render.log').open('w') as log:
        proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
        try:
            for frame_index in range(count):
                # Draw once per encoded frame; keep narration and diagrams on the
                # same global frame grid so rounding cannot accumulate across cuts.
                image=module.render(scene['index'],frame_index/fps,duration)
                proc.stdin.write(image.tobytes())
            proc.stdin.close()
            code=proc.wait(timeout=60)
            if code:raise RuntimeError(f'Scene {scene["index"]+1} encoder failed; see render.log')
        except BaseException:
            proc.kill();proc.wait();raise
    manifest.write_text(json.dumps({'fingerprint':fingerprint},indent=2))
    print('Rendered scene',scene['index']+1,f'({duration:.2f}s)',flush=True)
    return output

def main():
    os.environ['PYTHONUTF8']='1'
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--edit-dir',type=Path,default=ROOT/'out/video-use-prototype/edit');p.add_argument('--fps',type=int,default=24);p.add_argument('--stills',action='store_true');p.add_argument('--scene',type=int)
    args=p.parse_args();edit=args.edit_dir.resolve()
    plan=json.loads((edit/'scene-plan.json').read_text(encoding='utf-8'))
    scenes=plan['scenes']
    if args.scene is not None:scenes=[s for s in scenes if s['index']==args.scene-1]
    if not scenes:raise ValueError('No matching scenes')
    paths=[slot(scene,edit,args.fps,args.stills) for scene in scenes]
    if args.stills or args.scene is not None:return
    renderer=upstream('render')
    # Use video-use's concat implementation for matching encoded visual clips.
    renderer.concat_segments(paths,edit/'visuals.mp4',edit)
    run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(edit/'visuals.mp4'),'-i',str(edit/'narration.mp3'),'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(edit/'source.mp4')],edit/'mux.log')
    edl={'version':1,'sources':{'base':'source.mp4'},'ranges':[{'source':'base','start':0,'end':plan['duration'],'beat':'CONTINUOUS_NARRATION','quote':plan['title'],'reason':'Keep generated narration intact. Visual cuts follow the saved scene plan without cutting speech.'}],'grade':'none','overlays':[],'total_duration_s':plan['duration'],'scene_plan':'scene-plan.json','caption_policy':'Selective labels rendered inside original scenes; complete word-timed sidecar provided separately.'}
    (edit/'edl.json').write_text(json.dumps(edl,indent=2))
    # The unmodified upstream CLI performs extraction, concatenation, boundary
    # fades, final compositing and two-pass loudness normalization.
    command=[sys.executable,str(HELPERS/'render.py'),str(edit/'edl.json'),'-o',str(edit/'final.mp4'),'--no-subtitles','--fps',str(args.fps)]
    print('Finishing with pinned video-use renderer...',flush=True)
    run(command,edit/'video-use-render.log')
    # Retain the existing project's output contract without relying on an
    # unconstrained CRF encode to stay under the media size limit.
    if (edit/'final.mp4').stat().st_size>45_000_000:
        (edit/'final.mp4').replace(edit/'final-unconstrained.mp4')
        run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(edit/'final-unconstrained.mp4'),'-c:v','libx264','-threads','2','-preset','fast','-crf','23','-maxrate','1800k','-bufsize','3600k','-c:a','copy','-movflags','+faststart',str(edit/'final.mp4')],edit/'size-limit.log')
    print('Finished:',edit/'final.mp4',flush=True)

if __name__=='__main__':main()
