"""Measure the actual rendered Remotion file and extract review evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/video-use-prototype'))
from build import upstream
from visual import font
from PIL import Image,ImageDraw

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--edit-dir',type=Path,default=ROOT/'out/remotion-explainer/edit');args=p.parse_args()
    edit=args.edit_dir.resolve();out=edit/'verify';out.mkdir(parents=True,exist_ok=True)
    video=edit/'final.mp4'
    raw=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate','-of','json',str(video)],text=True)
    info=json.loads(raw);duration=float(info['format']['duration']);picture=next(s for s in info['streams'] if s['codec_type']=='video');audio=next(s for s in info['streams'] if s['codec_type']=='audio')
    assert 90<=duration<=180
    assert (picture['width'],picture['height'])==(1080,1920)
    assert picture['codec_name']=='h264' and audio['codec_name']=='aac'
    assert int(info['format']['size'])<45_000_000
    decode=subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True,check=True,timeout=180)
    assert not decode.stderr.strip(),decode.stderr
    measured=subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True,check=True,timeout=180)
    (out/'audio-levels.log').write_text(measured.stderr,encoding='utf-8')
    timeline=upstream('timeline_view');timeline.load_font=font
    plan=json.loads((ROOT/'out/video-use-prototype/edit/scene-plan.json').read_text())
    for scene in plan['scenes'][1:]:
        t=scene['start'];timeline.render_timeline(video,max(0,t-1),min(duration-.15,t+1),out/f'cut-{scene["index"]:02}.png',4,None)
    # Two positions per scene reveal changes within shots, rather than only
    # sampling the frame with the most labels already visible.
    beats_path=edit/'visual-beats.json'
    beats=json.loads(beats_path.read_text()) if beats_path.exists() else []
    samples=[((b['start']+b['end'])/2,f'beat-{i+1:02}') for i,b in enumerate(beats)] if beats else [(s['start']+s['duration']*f,f'scene-{i+1:02}-{j}') for i,s in enumerate(plan['scenes']) for j,f in enumerate((.25,.75))]
    sheet=Image.new('RGB',(1620,((len(samples)+4)//5)*610),'#11151c');draw=ImageDraw.Draw(sheet)
    for i,(at,label) in enumerate(samples):
            path=out/(label+'.jpg')
            subprocess.run(['ffmpeg','-v','error','-y','-ss',str(at),'-i',str(video),'-frames:v','1',str(path)],check=True,timeout=30)
            im=Image.open(path);im.thumbnail((324,576));x=i%5*324;y=i//5*610
            sheet.paste(im,(x,y+30));draw.text((x+10,y+4),f'{label} / {at:.1f}s',font=font(18),fill='white')
    sheet.save(edit/'contact-sheet.jpg',quality=93)
    timeline.render_timeline(video,duration-2,duration-.15,out/'ending.png',4,None)
    report={'duration_seconds':duration,'size_bytes':int(info['format']['size']),'video':picture,'audio':audio,'decode_errors':False,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'loudness_summary':measured.stderr[measured.stderr.rfind('Summary:'):].split('[out#')[0].strip(),'audio_listened_to':False,'review_status':'Measurements complete; sampled visuals require review.'}
    (edit/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
