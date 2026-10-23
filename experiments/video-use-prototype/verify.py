"""Inspect the finished file with video-use filmstrips and media measurements."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from PIL import Image,ImageDraw

from build import HERE,ROOT,upstream
from visual import font,INK,BG

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--edit-dir',type=Path,default=ROOT/'out/video-use-prototype/edit');args=p.parse_args()
    edit=args.edit_dir.resolve(); verify=edit/'verify';verify.mkdir(exist_ok=True)
    final=edit/'final.mp4';plan=json.loads((edit/'scene-plan.json').read_text(encoding='utf-8'))
    probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate','-of','json',str(final)],capture_output=True,text=True,check=True)
    info=json.loads(probe.stdout);duration=float(info['format']['duration'])
    video=next(s for s in info['streams'] if s['codec_type']=='video');audio=next(s for s in info['streams'] if s['codec_type']=='audio')
    assert 90<=duration<=180
    assert (video['width'],video['height'])==(1080,1920)
    assert video['codec_name']=='h264' and audio['codec_name']=='aac'
    assert int(info['format']['size'])<=45_000_000
    assert abs(duration-plan['duration'])<.25
    decoded=subprocess.run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'],capture_output=True,text=True,check=True)
    assert not decoded.stderr.strip(),decoded.stderr
    loudness=subprocess.run(['ffmpeg','-hide_banner','-i',str(final),'-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True,check=True)
    (verify/'audio-levels.log').write_text(loudness.stderr,encoding='utf-8')
    summary=loudness.stderr[loudness.stderr.rfind('Summary:'):]
    # Upstream visual inspection helper; supply our bundled font instead of
    # relying on whatever fonts a particular computer happens to have installed.
    timeline=upstream('timeline_view');timeline.load_font=font
    for scene in plan['scenes'][1:]:
        boundary=scene['start'];end=min(duration-.05,boundary+1.5)
        out=verify/f'cut-{scene["index"]:02d}.png'
        timeline.render_timeline(final,max(0,boundary-1.5),end,out,6,edit/'transcripts/base.json')
    # Inspect the opening and ending, in addition to every scene boundary.
    # Container duration can outlast the last video frame because of AAC padding.
    # Stay two frames inside it when asking FFmpeg for an actual decoded still.
    for name,start,end in [('opening',0,2),('ending',duration-2,duration-2/24)]:
        timeline.render_timeline(final,start,end,verify/(name+'.png'),6,edit/'transcripts/base.json')
    sheet=Image.new('RGB',(1620,1240),BG);draw=ImageDraw.Draw(sheet)
    for i,scene in enumerate(plan['scenes']):
        at=scene['start']+.8*scene['duration'];path=verify/f'scene-{i+1:02d}.jpg'
        subprocess.run(['ffmpeg','-y','-v','error','-ss',str(at),'-i',str(final),'-frames:v','1',str(path)],check=True)
        image=Image.open(path).convert('RGB');image.thumbnail((324,576))
        x=(i%5)*324;y=(i//5)*620
        sheet.paste(image,(x,y+30));draw.text((x+12,y+5),f'{i+1:02d} / {scene["start"]:.1f}s',font=font(18),fill=INK)
    sheet.save(edit/'contact-sheet.jpg',quality=94)
    report={'duration_seconds':duration,'narration_duration_seconds':plan['duration'],'size_bytes':int(info['format']['size']),'video':video,'audio':audio,'decode_errors':False,'scene_boundary_filmstrips':9,'loudness_summary':summary,'audio_listened_to':False,'inspection_status':'Measurements complete; filmstrips require agent review.','source_footage':'Original programmatic illustrations, not recorded experiments.','word_timing_source':'Edge TTS; no ElevenLabs ASR call'}
    (edit/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
