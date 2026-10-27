"""Actual-file checks for the Opus-authored Data Storytelling film."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/lemo-time-perception'
spec=importlib.util.spec_from_file_location('review_helpers',ROOT/'experiments/coffee-comparison/verify.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
call=helper.call

if __name__=='__main__':
    final=OUT/'final.mp4'
    probe=json.loads(call(['ffprobe','-v','error','-show_streams','-show_format','-of','json',final])[0])
    v=next(s for s in probe['streams'] if s['codec_type']=='video');a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    duration=float(probe['format']['duration'])
    assert 90<=duration<=180 and (v['width'],v['height'])==(1080,1920)
    assert v['codec_name']=='h264' and a['codec_name']=='aac' and final.stat().st_size<45_000_000
    _,log=call(['ffmpeg','-hide_banner','-nostats','-i',final,'-vf','blackdetect=d=0.15:pix_th=0.10',
               '-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'])
    (OUT/'media-analysis.log').write_text(log,encoding='utf-8')
    assert 'black_start:' not in log
    assert not re.search(r'Error while decoding|corrupt decoded frame|Invalid data found',log,re.I)
    loudness=json.loads(re.findall(r'\{\s*"input_i".*?\}',log,re.S)[-1])
    assert -17<=float(loudness['input_i'])<=-15 and float(loudness['input_tp'])<=-1
    audit=json.loads((OUT/'provider-audit.json').read_text())
    assert len(audit)>=3 and all(r['reported_models']==['claude-opus-5-5'] and r['success'] for r in audit)
    data=json.loads((OUT/'data.json').read_text())
    stills=OUT/'review';stills.mkdir(exist_ok=True)
    for t in [float(i) for i in range(0,int(duration),7)]+[duration-.3]:
        call(['ffmpeg','-y','-v','error','-ss',t,'-i',final,'-frames:v','1',stills/f'{t:06.1f}.jpg'])
    helper.sheet(stills,sorted(stills.glob('*.jpg')),OUT/'contact-final.jpg',columns=5,width=230)
    actions=OUT/'actions';actions.mkdir(exist_ok=True)
    for i,b in enumerate(data['beats'][1:],start=1):
        if i%2==0:
            for dt in [-.2,0,.2,.4]:
                t=b['start']+dt;call(['ffmpeg','-y','-v','error','-ss',t,'-i',final,'-frames:v','1',actions/f'{i:02d}-{t:07.2f}.jpg'])
    helper.sheet(actions,sorted(actions.glob('*.jpg')),OUT/'contact-actions.jpg',columns=4,width=190)
    call(['ffmpeg','-y','-v','error','-ss','55','-i',final,'-frames:v','1',OUT/'poster.jpg'])
    report={'duration':duration,'bytes':final.stat().st_size,'width':v['width'],'height':v['height'],
        'fps':v['r_frame_rate'],'video_codec':v['codec_name'],'audio_codec':a['codec_name'],
        'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'loudness':loudness,
        'decode':'passed','black_intervals':[],'provider':'claude-code','model':'claude-opus-5-5',
        'model_audit_calls':len(audit),'style':'dataviz','progress_bar':False,'persistent_header':False,
        'limits':'Directed original film; study counts are not memories or time-speed measurements. Technical review does not establish sensory assessment or audience retention.'}
    (OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (OUT/'watch.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Why Your Years Seem to Shrink</title>
<style>body{margin:0;background:#252421;display:grid;place-items:center;min-height:100vh}video{max-width:100%;height:96vh}</style>
<video controls preload="metadata" poster="poster.jpg" src="final.mp4"></video></html>''',encoding='utf-8')
    print(json.dumps(report,indent=2))
