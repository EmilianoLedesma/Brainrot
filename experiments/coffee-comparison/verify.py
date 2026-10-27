"""Verify actual rendered media and create local comparison artifacts."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"out/coffee-comparison"


def call(args, timeout=900):
    result=subprocess.run([str(a) for a in args],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout)
    if result.returncode:raise RuntimeError(result.stderr[-1200:])
    return result.stdout,result.stderr


def sheet(folder, files, dest, columns=4, width=270):
    height=round(width*1920/1080)
    image=Image.new('RGB',(columns*width,((len(files)+columns-1)//columns)*(height+30)),'#ddd7cb')
    draw=ImageDraw.Draw(image)
    for i,file in enumerate(files):
        frame=Image.open(file).convert('RGB');frame.thumbnail((width,height))
        x=i%columns*width;y=i//columns*(height+30)
        image.paste(frame,(x,y+30));draw.text((x+10,y+8),file.stem,fill='#302b27')
    image.save(dest,quality=90)


def verify():
    report={"files":{},"review":{
        "scope":"Actual final files: full decode, black-frame scan, loudness, scene/boundary contact sheets.",
        "limitations":"No claim of a human-equivalent full-speed audiovisual watch/listen. Review the supplied player.",
        "comparison":"Same saved Brainrot script, 0 Grounded, English Guy voice, MP3 and word times; Lemo final adds quiet procedural effects. Lemo voice-only is supplied as an audio control.",
        "integration":"Local experiment using actual Brainrot generation/TTS/production Remotion and actual pinned Lemo renderer/isometric engine/readcheck/sfx. No queue integration or publishing."}}
    for name in ['baseline/final.mp4','lemo/final.mp4','lemo/voice-only.mp4']:
        path=OUT/name;folder=path.parent
        probe=json.loads(call(['ffprobe','-v','error','-show_streams','-show_format','-of','json',path])[0])
        duration=float(probe['format']['duration']);video=next(x for x in probe['streams'] if x['codec_type']=='video')
        audio=next(x for x in probe['streams'] if x['codec_type']=='audio')
        assert 90<=duration<=180 and (video['width'],video['height'])==(1080,1920)
        assert video['codec_name']=='h264' and audio['codec_name']=='aac' and path.stat().st_size<45_000_000
        _,diagnostic=call(['ffmpeg','-hide_banner','-nostats','-i',path,'-vf','blackdetect=d=0.15:pix_th=0.10',
             '-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'])
        (folder/(path.stem+'-analysis.log')).write_text(diagnostic,encoding='utf-8')
        assert not re.search(r'black_start:',diagnostic),f'Black interval in {name}'
        assert not re.search(r'Error while decoding|Invalid data found|corrupt decoded frame',diagnostic,re.I)
        block=re.findall(r'\{\s*"input_i".*?\}',diagnostic,re.S)[-1]
        loudness=json.loads(block)
        measured=float(loudness['input_i'])
        assert -17<=measured<=-15,f'Loudness {measured} in {name}'
        assert float(loudness['input_tp'])<=-1.0
        report['files'][name]={"duration":duration,"bytes":path.stat().st_size,
             "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
             "width":video['width'],"height":video['height'],"fps":video['r_frame_rate'],
             "video_codec":video['codec_name'],"audio_codec":audio['codec_name'],"loudness":loudness,
             "decode":"passed","black_intervals":[]}
    plan=json.loads((OUT/'lemo/data.json').read_text(encoding='utf-8'))
    # Two final-file review passes: regular timeline samples, then shot boundaries.
    for name in ['baseline','lemo']:
        folder=OUT/name;stills=folder/'review';stills.mkdir(exist_ok=True)
        times=[float(t) for t in range(0,128,8)]+[128.0]
        for t in times:call(['ffmpeg','-y','-v','error','-ss',t,'-i',folder/'final.mp4','-frames:v','1',stills/f'{t:06.1f}.jpg'])
        sheet(folder,sorted(stills.glob('*.jpg')),folder/'contact-final.jpg')
    boundaries=OUT/'lemo/boundaries';boundaries.mkdir(exist_ok=True)
    for shot in plan['shots'][1:]:
        t=shot['start']
        for delta in [-.4,-.2,0,.2,.4]:
            sample=t+delta
            call(['ffmpeg','-y','-v','error','-ss',sample,'-i',OUT/'lemo/final.mp4','-frames:v','1',boundaries/f'{sample:07.2f}.jpg'])
    sheet(boundaries,sorted(boundaries.glob('*.jpg')),OUT/'lemo/contact-boundaries.jpg',columns=5,width=180)
    # Balanced overview: A on the left, B on the right at matching timestamps.
    for t in [2,22,43,65,88,111,125]:
        target=OUT/f'compare-{t:03d}.jpg'
        call(['ffmpeg','-y','-v','error','-ss',t,'-i',OUT/'baseline/final.mp4','-ss',t,'-i',OUT/'lemo/final.mp4',
             '-filter_complex','[0:v]scale=540:960[a];[1:v]scale=540:960[b];[a][b]hstack=inputs=2[v]',
             '-map','[v]','-frames:v','1',target])
    (OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:{'duration':v['duration'],'bytes':v['bytes'],'lufs':v['loudness']['input_i']} for k,v in report['files'].items()},indent=2))


def preview():
    call(['ffmpeg','-y','-v','error','-i',OUT/'baseline/final.mp4','-i',OUT/'lemo/final.mp4',
          '-filter_complex',"[0:v]scale=540:960[a];[1:v]scale=540:960[b];[a][b]hstack=inputs=2,pad=1080:1080:0:60:color=0x20262b,drawtext=fontfile=motion/DMSans.ttf:text='A - CURRENT REMOTION':fontcolor=white:fontsize=22:x=20:y=18,drawtext=fontfile=motion/DMSans.ttf:text='B - BRAINROT + LEMO':fontcolor=white:fontsize=22:x=560:y=18[v]",
          '-map','[v]','-map','0:a','-c:v','libx264','-crf','23','-preset','veryfast','-maxrate','1800k','-bufsize','3600k',
          '-c:a','copy','-movflags','+faststart','-shortest',OUT/'comparison.mp4'])
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Coffee: A/B comparison</title>
<style>body{background:#182028;color:#f4eddf;font:16px system-ui;margin:30px auto;max-width:1100px;padding:0 20px}h1{font-size:28px}main{display:flex;gap:20px}section{flex:1;min-width:0}video{width:100%;max-height:70vh;background:#000}button,select{font:inherit;padding:10px;margin:8px 8px 18px 0}a{color:#83d6e4}.note{color:#c6c9c9}input{width:100%}</style>
<h1>The science of coffee — same script, two edits</h1>
<p>English · Grounded · same 128.5-second Brainrot narration. Local unpublished experiment.</p>
<button id="play">Play / pause both</button><button id="restart">Restart</button>
<label>Audio <select id="audio"><option value="a">A: current Remotion</option><option value="b">B: Lemo + quiet effects</option><option value="control">B: same voice only</option></select></label>
<main><section><h2>A · Current Brainrot / Remotion</h2><video id="a" controls preload="metadata" src="baseline/final.mp4"></video><p><a href="baseline/final.mp4">Open A</a></p></section>
<section><h2>B · Brainrot + Lemo-Opuscar</h2><video id="b" controls muted preload="metadata" src="lemo/final.mp4"></video><p><a href="lemo/final.mp4">Open B</a> · <a href="lemo/voice-only.mp4">Voice-only control</a></p></section></main>
<input id="seek" type="range" min="0" max="128.5" step=".1" value="0" aria-label="Seek both videos">
<p class="note">A uses the unchanged production composition and model-selected devices. B uses a model-generated shot plan, original coffee geometry and pinned Lemo isometric/render tools. B is a directed prototype; this does not demonstrate arbitrary-topic unattended editing. The technical checks and contact-sheet review do not replace watching and listening.</p>
<p><a href="verification.json">Technical verification</a> · <a href="shared/story.json">Shared script</a> · <a href="lemo/contact-final.jpg">B contact sheet</a> · <a href="baseline/contact-final.jpg">A contact sheet</a></p>
<script>const a=document.querySelector('#a'),b=document.querySelector('#b'),seek=document.querySelector('#seek');let audioVersion=0;
const play=async v=>{try{await v.play()}catch(e){if(e.name!=='AbortError')throw e}};
document.querySelector('#play').onclick=async()=>{if(!a.paused){a.pause();b.pause()}else{b.currentTime=a.currentTime;await Promise.all([play(a),play(b)])}};
document.querySelector('#restart').onclick=()=>{a.currentTime=0;b.currentTime=0};
seek.oninput=()=>{a.currentTime=+seek.value;b.currentTime=+seek.value};
a.ontimeupdate=()=>{seek.value=a.currentTime;if(!a.paused&&b.readyState>0&&Math.abs(b.currentTime-a.currentTime)>.18)b.currentTime=a.currentTime};
document.querySelector('#audio').onchange=async e=>{const version=++audioVersion;const control=e.target.value==='control';a.muted=e.target.value!=='a';b.muted=!a.muted;
const src=control?'lemo/voice-only.mp4':'lemo/final.mp4';if(b.getAttribute('src')!==src){b.pause();b.src=src;b.load();await new Promise(resolve=>b.addEventListener('loadedmetadata',resolve,{once:true}));if(version!==audioVersion)return;b.currentTime=a.currentTime;if(!a.paused)await play(b)}};</script></html>'''
    (OUT/'comparison.html').write_text(html,encoding='utf-8')
    print('Comparison player and side-by-side MP4 ready')


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='preview':preview()
    else:verify()
