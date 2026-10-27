"""An original Lemo-directed procrastination film; no queue or publication."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request

from pydantic import BaseModel

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from brainrot import llm,render,script,tts

HERE=Path(__file__).resolve().parent
OUT=ROOT/'out/lemo-procrastination'
LEMO=ROOT/'experiments/coffee-comparison/vendor/lemo-opuscar'
SHA='413a6bd6d78ebd3bdd5abaec9538a26867f890df'

TOPIC="""Why Does Your Brain Make You Procrastinate? Procrastination isn't always
about laziness. Your brain often prioritizes immediate emotional relief over
long-term rewards, making even simple tasks feel overwhelming. Understanding
this mechanism explains why starting can be harder than doing the work."""

REFERENCES="""Write original, grounded English narration, 300-340 words including title.
Explain a common psychological mechanism, not a diagnosis or a universal brain circuit.
When an intended task feels aversive (uncertain, boring, frustrating, fear of failure),
avoiding it can prioritize short-term mood repair over later goals. This is one
influential account of procrastination, not the sole cause of all delay. Deliberate
rest and sensible rescheduling are not automatically procrastination.
Source: Sirois & Pychyl 2013, https://doi.org/10.1111/spc3.12011
Source: Pychyl & Sirois 2016, https://doi.org/10.1016/B978-0-12-802862-9.00008-6
Research links emotion-regulation difficulties and academic procrastination; avoid
treating an association as proof of a universal cause or calling every delay laziness.
Source: https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2020.524588/full
Use an explicitly illustrative everyday example: someone avoiding a blank document
by checking a phone. The momentary relief leaves the task unfinished and can add
later pressure. This is not a report of an experiment or a real named person.
Source: https://doi.org/10.1111/bjso.12243
Practical implication, qualified not promised: identifying discomfort and choosing
a very small concrete next action can make beginning feel more approachable.
Do not promise that starting makes work effortless, cures a condition, or works
for everyone. No fabricated dopamine claims, amygdala-versus-cortex battles,
brain scans, countdowns, percentages, study results or medical advice. Explain
starting as approaching the discomfort as well as doing the task. Earn the ending.
"""


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    os.environ['BRAINROT_LLM_TIMEOUT_SECONDS']='900'
    if not (OUT/'story.json').exists():
        print('Generating Grounded English narration with Brainrot storytelling skill',flush=True)
        story=script.write_story(TOPIC+' Write in English.',provider='codex',brainrot_level=0,reference_context=REFERENCES)
        save(OUT/'story.json',story.model_dump())
    story=script.Story.model_validate_json((OUT/'story.json').read_text(encoding='utf-8'))
    count=len((story.title+' '+story.script).split())
    if not 280<=count<=380:raise ValueError(f'Review word count: {count}')
    print(f'Script cached: {count} words',flush=True)
    if not (OUT/'narration.mp3').exists():
        for attempt in range(3):
            try:
                audio,words=tts.narrate(story.script,voice='en-US-GuyNeural',title=story.title)
                break
            except Exception:
                if attempt==2:raise
                print('Retrying same saved text after speech service failure',flush=True)
                time.sleep(2)
        save(OUT/'words.json',words)
        (OUT/'narration.mp3').write_bytes(audio)
        (OUT/'captions.srt').write_text(render.build_srt(words),encoding='utf-8')
    seconds=render.check_media(str(OUT/'narration.mp3'))
    render.check_captions(json.loads((OUT/'words.json').read_text()),seconds)
    save(OUT/'manifest.json',{'duration':seconds,'word_count':count,'provider':'codex',
        'brainrot_level':0,'language':'en','voice':'en-US-GuyNeural','publication':'off',
        'audio_sha256':hashlib.sha256((OUT/'narration.mp3').read_bytes()).hexdigest(),
        'references':REFERENCES,'progress_bar':False,'persistent_header':False})
    print(f'Speech ready: {seconds:.2f}s',flush=True)


class Candidate(BaseModel):
    slug:str
    reason:str


class StyleChoice(BaseModel):
    candidates:list[Candidate]
    selected_slug:str
    rationale:str
    visual_thesis:str


def choose():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'style-choice.json').exists():return
    os.environ['BRAINROT_LLM_TIMEOUT_SECONDS']='900'
    index=urllib.request.urlopen(f'https://raw.githubusercontent.com/lemomo-ai/lemo-opuscar/{SHA}/styles/README.md',timeout=30).read().decode()
    story=(OUT/'story.json').read_text(encoding='utf-8') if (OUT/'story.json').exists() else TOPIC
    system="""Choose the most appropriate Lemo-Opuscar visual style for this English
Grounded short film on procrastination. You are the directing agent; make the
choice yourself from the entire supplied index. Compare three suitable candidates
and select one. It must help explain immediate emotional relief, avoidance and the
difficulty of starting through original actions, characters or transformations.
Do not default to the coffee film's isometric template; judge this topic afresh.
User constraints: no progress bar, no persistent top header or series branding,
no slideshow layout of heading/cards. Compose a continuous animated film, where
scenes develop and transform rather than static lecture slides. Word-timed bottom
captions are allowed. The user additionally requests much stronger editing: use
motivated camera pushes/pulls, lateral follows, genuine framing changes, parallax,
action-driven transitions, anticipation/overshoot and restrained timed sound
effects. Select a style that can express these while keeping narration readable.
All visuals are illustrative psychological metaphors, not
brain scans or neuroscience measurements. No external video/image model or paid
API. Choose the style on editorial fit, not resemblance to the library demo.
Use exact folder slugs from the index. Return only the typed JSON choice.
"""
    result=llm.generate(system,index+'\n\nNarration:\n'+story,StyleChoice,max_tokens=3000,provider='codex')
    allowed=set(re.findall(r'\]\(([^/]+)/STYLE.md\)',index))
    if result.selected_slug not in allowed:raise ValueError('Style not in pinned library index')
    save(OUT/'style-choice.json',result.model_dump())
    target=HERE/'guidance'/result.selected_slug/'STYLE.md'
    target.parent.mkdir(parents=True,exist_ok=True)
    source=f'https://raw.githubusercontent.com/lemomo-ai/lemo-opuscar/{SHA}/styles/{result.selected_slug}/STYLE.md'
    target.write_bytes(urllib.request.urlopen(source,timeout=30).read())
    save(HERE/'guidance/provenance.json',{'repository':'https://github.com/lemomo-ai/lemo-opuscar',
        'revision':SHA,'style':result.selected_slug,'source':source,
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'license':'MIT'})
    print('Agent chose:',result.selected_slug,flush=True)


class Beat(BaseModel):
    id:str
    cue:str
    action:str
    framing:str
    camera:str
    transition:str
    sound:str
    label:str


class Direction(BaseModel):
    visual_arc:str
    palette:list[str]
    beats:list[Beat]


def direct():
    if (OUT/'direction.json').exists():return
    os.environ['BRAINROT_LLM_TIMEOUT_SECONDS']='900'
    choice=json.loads((OUT/'style-choice.json').read_text())
    style=(HERE/'guidance'/choice['selected_slug']/'STYLE.md').read_text(encoding='utf-8')
    guide=(LEMO/'DIRECTOR.md').read_text(encoding='utf-8')
    story=(OUT/'story.json').read_text(encoding='utf-8')
    system="""Direct an original animated short from the supplied existing narration.
Follow the chosen style's material, palette, limited character animation and
smooth camera. User overrides: NO progress bar, NO fixed top/series header, NO
chapter/step headers, NO numbered lecture cards, NO slideshow. A continuous
character story, where phone/document/hand actions motivate visual transitions.
Use the same adult and desk throughout. The selected style is midcentury-toon,
adapt its printed cels and limited acting without the library demo's step cards.
Return 14-18 chronological beats. Each cue is a unique EXACT contiguous phrase
of 4-8 words in the existing title/script (first is the full spoken title).
Each beat needs an action, motivated camera and framing change, transition and
specific subtle sound. Vary wide/medium/extreme close-up/top view. Avoid constant
zoom drift: include purposeful track, push, pull, parallax, match cuts, object
wipes and circle reveals, plus settled holds for important words. Close-ups of
hands/props should be redrawn at native line width. Labels optional, <=18 chars,
diegetic on a document/phone/calendar, not headings. No new narrated text or
new neuroscience/facts, no literal brain simulation or diagnosis. Emotional
clouds/obstacles are explicitly illustrative. Finishing work is NOT the payoff;
the first imperfect action while discomfort remains is the payoff. End with
movement continuing, not a motivational quote card. Grounded, warm, not slapstick.
Treat music/foley as supporting narration. Output only the typed JSON plan.
"""
    result=llm.generate(system+'\n\n'+style+'\n\n'+guide,
        'Agent style choice:\n'+json.dumps(choice)+'\n\nExisting narration:\n'+story,
        Direction,max_tokens=6500,provider='codex')
    save(OUT/'direction.json',result.model_dump())
    print(f'Direction ready: {len(result.beats)} beats',flush=True)


def common():
    spec=importlib.util.spec_from_file_location('coffee_tools',ROOT/'experiments/coffee-comparison/run.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def fetch_style():
    choice=json.loads((OUT/'style-choice.json').read_text())
    slug=choice['selected_slug']
    if slug!='midcentury-toon':
        raise ValueError('This original film was authored for the agent-selected midcentury-toon style')
    files={}
    for name in ['STYLE.md','DEMO.md','demo/engine/toon.js']:
        target=HERE/'guidance'/slug/name
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(urllib.request.urlopen(f'https://raw.githubusercontent.com/lemomo-ai/lemo-opuscar/{SHA}/styles/{slug}/{name}',timeout=30).read())
        files[slug+'/'+name]=hashlib.sha256(target.read_bytes()).hexdigest()
    shutil.copyfile(LEMO/'LICENSE',HERE/'guidance/LICENSE')
    save(HERE/'guidance/provenance.json',{'repository':'https://github.com/lemomo-ai/lemo-opuscar',
        'revision':SHA,'license':'MIT','files':files})


def build():
    fetch_style()
    manifest=json.loads((OUT/'manifest.json').read_text())
    words=json.loads((OUT/'words.json').read_text())
    direction=Direction.model_validate_json((OUT/'direction.json').read_text(encoding='utf-8'))
    if [b.id for b in direction.beats]!=[f'b{i:02d}' for i in range(1,19)]:
        raise ValueError('This authored film requires its saved eighteen-beat direction; review a newly generated plan before rendering')
    clean=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
    spoken=[clean(w['text']) for w in words];beats=[]
    for beat in direction.beats:
        target=[clean(w) for w in beat.cue.split()]
        positions=[i for i in range(len(words)-len(target)+1) if spoken[i:i+len(target)]==target]
        if len(positions)!=1:raise ValueError(f'Cue must match exactly once: {beat.cue}')
        start=0.0 if not beats else words[positions[0]]['start']
        if beats and start<=beats[-1]['start']:raise ValueError('Nonchronological direction')
        beats.append({**beat.model_dump(),'start':start})
    for i,beat in enumerate(beats):
        beat['end']=beats[i+1]['start'] if i+1<len(beats) else manifest['duration']
        if beat['end']-beat['start']<2:raise ValueError('Too short to stage a complete action')
    captions=[];group=[]
    for word in words:
        if group and (len(group)>=9 or word['start']-group[0]['start']>3.5 or word['start']-group[-1]['end']>.65):
            captions.append({'start':group[0]['start'],'end':min(word['start'],group[-1]['end']+.6),'words':group});group=[]
        group.append(word)
    if group:captions.append({'start':group[0]['start'],'end':manifest['duration'],'words':group})
    events=[]
    for i,beat in enumerate(beats):
        if i:
            events.append({'t':beat['start']+.05,'type':'iris' if i in [4,5,6,11,15] else 'swish'})
        kind='tap' if i in [5,15,16,17] else 'buzz' if i in [2,6,7] else 'paper' if i in [9,12] else 'soft'
        events.append({'t':beat['start']+min(1.3,(beat['end']-beat['start'])/3),'type':kind})
        if i in [15,16,17]:
            for t in [beat['start']+1.5+j*.62 for j in range(10)]:
                if t<beat['end']-.2:events.append({'t':t,'type':'key'})
    save(OUT/'data.json',{'duration':manifest['duration'],'beats':beats,'captions':captions,'events':events})
    for name in ['index.html','drawing.js','film.js']:shutil.copyfile(HERE/'film'/name,OUT/name)
    shutil.copyfile(HERE/'guidance/midcentury-toon/demo/engine/toon.js',OUT/'toon.js')
    shutil.copyfile(ROOT/'motion/DMSans.ttf',OUT/'DMSans.ttf')
    shutil.copyfile(ROOT/'motion/OFL-DMSans.txt',OUT/'OFL-DMSans.txt')
    for name in ['TREATMENT.md','CREDITS','FACTS.md']:
        if (HERE/name).exists():shutil.copyfile(HERE/name,OUT/name)
    tools=common();tools.browser_environment()
    times=[str(round((b['start']+b['end'])/2,2)) for b in beats]
    tools.run(['node',LEMO/'core/render/still.mjs',OUT,*times,'--size','1080x1920','--out',OUT/'stills'],cwd=LEMO,log=OUT/'stills.log')
    tools.run(['node',LEMO/'core/render/readcheck.mjs',OUT,'--size','1080x1920'],cwd=LEMO,log=OUT/'readcheck.log')
    tools.run(['node',LEMO/'core/render/events.mjs',OUT,'--size','1080x1920'],cwd=LEMO,log=OUT/'events.log')
    print(f'Built {len(beats)} original animated beats',flush=True)


def produce():
    tools=common();tools.browser_environment()
    if not (OUT/'raw.mp4').exists():
        tools.run(['node',LEMO/'core/render/video.mjs',OUT,'--size','1080x1920','--fps','30','--workers','2','--out',OUT/'raw.mp4'],cwd=LEMO,log=OUT/'render.log')
    python=ROOT/'experiments/coffee-comparison/.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    tools.run([python,HERE/'mix.py',OUT],log=OUT/'mix.log')
    tools.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',OUT/'raw.mp4','-i',OUT/'mix.wav',
      '-map','0:v','-map','1:a','-c:v','libx264','-crf','23','-preset','veryfast',*render.VIDEO_RATE_OPTIONS,
      '-af',render.VOICE_FILTER,'-c:a','aac','-b:a','128k','-movflags','+faststart','-shortest',OUT/'final.mp4'],log=OUT/'master.log')
    render.check_video(str(OUT/'final.mp4'))
    print('Final film ready',flush=True)


def playback():
    tools=common();tools.browser_environment()
    tools.run(['node',HERE/'playback.mjs',OUT],log=OUT/'playback.log',timeout=240)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','choose','direct','build','produce','playback'])
    args=parser.parse_args();{'prepare':prepare,'choose':choose,'direct':direct,'build':build,'produce':produce,'playback':playback}[args.stage]()
