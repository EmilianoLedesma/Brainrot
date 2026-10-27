"""Claude Opus 5.5 authored Data Storytelling film, using Brainrot voice/Lemo tools."""
from __future__ import annotations
import argparse
import asyncio
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
import urllib.parse
import urllib.request
from pydantic import BaseModel

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from brainrot import llm,script,tts,render
HERE=Path(__file__).resolve().parent;OUT=ROOT/'out/lemo-time-perception'
LEMO=ROOT/'experiments/coffee-comparison/vendor/lemo-opuscar'
SHA='413a6bd6d78ebd3bdd5abaec9538a26867f890df'
MODEL='claude-opus-5-5'
TOPIC="""Why Does Time Feel Faster as You Get Older? When you're young, almost
everything is a new experience, giving your brain more distinctive memories.
As routines become repetitive, fewer moments stand out, potentially making
entire years feel like they passed in the blink of an eye."""

REFERENCES="""Write an original English Grounded explainer, 300-340 words including
the short spoken title. Explain retrospective time versus time while experiencing
it. Novelty/routine and distinctive contextual landmarks are one plausible account;
do not assert a proven direct chain from older age to fewer memories to faster years.
No literal brain clock, fake brain scans, invented quantitative data, dopamine,
universal age curve or promise that novelty slows aging. Equal clock time remains
equal. Use an explicitly qualitative illustration of a new trip versus a familiar
week; any memory sketch is an illustration, not a measured dataset.
Sources and permitted quantitative facts:
1) Wittmann & Lehnhoff 2005 surveyed 499 people, ages 14-94. Reported age effects
were small/moderate, accounting for at most 10 percent of variance in their measures.
This supports an age association, not causation or a curve to fabricate.
https://pubmed.ncbi.nlm.nih.gov/16512313/ DOI 10.2466/pr0.97.3.921-935
2) Kosak & Hilbert 2021 examined three samples, N=293,263,262, evaluating the last
five years. The number of reported life events/memories did not predict passage-
of-time judgments in their analyses. These are sample sizes, NOT counts of memories.
No synthetic point cloud or fabricated correlation values.
https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.744551/full
3) Teghil et al. 2026 studied 120 adults, 20 per group: 20-29,30-39,40-49,50-59,
60-69,70+ (last group ranged 70-91). Observational, not preregistered. Encoding new
information was associated with reported passage of the past decade; unconstrained
autobiographical recall did not explain the age effect. Age relationship no longer
significant after exploratory exclusion of youngest group. Not proof of causation.
https://doi.org/10.3758/s13421-026-01879-1
4) Life-tempo review: these are retrospective autobiographical judgments, not a
literal perception of physical time moving faster; no unified mechanism settled.
https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1747171/full
Use no more than two numerical anchors in spoken narration; don't narrate a list
of studies. Keep the focus on the user's mechanism with a proportionate caveat.
Other effects include attention, emotional engagement and time pressure. Closing
can suggest noticing/distinguishing experiences as a way to enrich recollection,
not a guaranteed slowing of time. No likes, questions for engagement or quote card.
"""


def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def setup_provider():
    os.environ['BRAINROT_LLM_PROVIDER']='claude-code'
    os.environ['BRAINROT_CLAUDE_MODEL']=MODEL
    os.environ['BRAINROT_LLM_TIMEOUT_SECONDS']='1200'
    original=llm._run
    def observed(command,**options):
        if '--print' in command and os.environ.get('BRAINROT_COMPACT_AUTHOR')=='1':
            command=[*command,'--effort','low']
        raw=original(command,**options)
        if '--print' in command:
            envelope=json.loads(raw)
            names=list((envelope.get('modelUsage') or {}).keys())
            audit=OUT/'provider-audit.json'
            records=json.loads(audit.read_text()) if audit.exists() else []
            records.append({'requested':MODEL,'reported_models':names,
                'success':not envelope.get('is_error',False),'provider':'claude-code',
                'transport':'subscription CLI; no API fallback'})
            save(audit,records)
            if names and any(not n.startswith(MODEL) for n in names):
                raise RuntimeError('CLI reported a different model; refusing silent fallback')
        return raw
    llm._run=observed


def common():
    s=importlib.util.spec_from_file_location('coffee_tools',ROOT/'experiments/coffee-comparison/run.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def prepare():
    OUT.mkdir(parents=True,exist_ok=True);setup_provider()
    if not (OUT/'story.json').exists():
        print('Claude Opus 5.5: generating Grounded English story',flush=True)
        story=script.write_story(TOPIC+' English narration.',provider='claude-code',brainrot_level=0,reference_context=REFERENCES)
        save(OUT/'story.json',story.model_dump())
    story=script.Story.model_validate_json((OUT/'story.json').read_text(encoding='utf-8'))
    n=len((story.title+' '+story.script).split())
    if not 280<=n<=380:raise ValueError(f'Review script word count: {n}')
    if not (OUT/'narration.mp3').exists():
        # Retry/cache individual utterances, keeping Brainrot's original TTS,
        # pacing and voice. A flaky later stream must not repeat earlier speech.
        original_synthesize=tts._synthesize
        async def cached_synthesize(text,voice,rate):
            digest=hashlib.sha256((voice+'\n'+rate+'\n'+text).encode()).hexdigest()
            folder=OUT/'tts-cache';folder.mkdir(exist_ok=True)
            audio_path=folder/(digest+'.mp3');word_path=folder/(digest+'.json')
            if audio_path.exists() and word_path.exists():
                return audio_path.read_bytes(),json.loads(word_path.read_text())
            for trial in range(3):
                try:
                    print('Synthesizing utterance',digest[:8],flush=True)
                    audio,words=await original_synthesize(text,voice,rate)
                    save(word_path,words);audio_path.write_bytes(audio);return audio,words
                except Exception:
                    if trial==2:raise
                    await asyncio.sleep(3)
        tts._synthesize=cached_synthesize
        for attempt in range(3):
            try:audio,words=tts.narrate(story.script,voice='en-US-GuyNeural',title=story.title);break
            except Exception:
                if attempt==2:raise
                print('Retrying same cached text after TTS failure',flush=True);time.sleep(2)
        save(OUT/'words.json',words);(OUT/'narration.mp3').write_bytes(audio)
        (OUT/'captions.srt').write_text(render.build_srt(words),encoding='utf-8')
    duration=render.check_media(str(OUT/'narration.mp3'))
    render.check_captions(json.loads((OUT/'words.json').read_text()),duration)
    save(OUT/'manifest.json',{'duration':duration,'word_count':n,'provider':'claude-code','model':MODEL,
        'brainrot_level':0,'language':'en','voice':'en-US-GuyNeural','publication':'off','style':'dataviz',
        'progress_bar':False,'persistent_header':False,'references':REFERENCES,
        'audio_sha256':hashlib.sha256((OUT/'narration.mp3').read_bytes()).hexdigest()})
    print(f'Saved Opus script/voice: {n} words, {duration:.2f}s',flush=True)


class Beat(BaseModel):
    cue:str
    operation:str
    camera:str
    annotation:str
    sound:str


class Direction(BaseModel):
    premise:str
    data_policy:str
    beats:list[Beat]


def direct():
    if (OUT/'direction.json').exists():return
    setup_provider()
    guide=(LEMO/'DIRECTOR.md').read_text(encoding='utf-8')
    style=(HERE/'guidance/dataviz/STYLE.md').read_text(encoding='utf-8')
    story=(OUT/'story.json').read_text(encoding='utf-8')
    result=llm.generate("""Direct an original Data Storytelling animated film on one
continuous cream sheet. User explicitly selected this style. Respect actual
Lemo pencil/chart grammar, with purposeful camera changes, data-space notes,
reveals, restrained sonification and transitions through chart operations.
NO progress bar, NO persistent top header, NO step cards, no dashboard/slides.
Bottom spoken captions allowed. A chart-local label can move with its chart;
never an always-on headline. Use only the supplied real numerical facts. Counts
of participants are NOT counts of memories. Never fabricate individual points,
age curves, effect sizes, chart values or percentages. Display study design as
design, not evidence of a trend. Illustrative memories can use nonnumeric icons
explicitly labelled ILLUSTRATION; don't encode invented memory counts on an axis.
The film should explain memory landmarks and retrospective judgement, not turn
into a list of papers. Keep the cue to numbers aligned with what narration says.
Return 12-16 chronological beats; each cue is a unique EXACT contiguous 4-8 word
phrase in title/script. First cue is full title. State chart operation, motivated
camera, a short optional annotation and sound. Leave long readable holds during
important empirical caveats. End on a memory mark, not a quote card.
"""+'\n'+guide+'\n'+style,'Research notes:\n'+REFERENCES+'\nNarration:\n'+story,
        Direction,max_tokens=6500,provider='claude-code')
    save(OUT/'direction.json',result.model_dump());print('Opus direction saved',flush=True)


class FilmSource(BaseModel):
    javascript:str
    editorial_notes:str


def author():
    if (HERE/'film/film.js').exists():return
    setup_provider()
    style=(HERE/'guidance/dataviz/STYLE.md').read_text(encoding='utf-8')
    engine=(HERE/'guidance/dataviz/demo/engine.js').read_text(encoding='utf-8')
    direction=(OUT/'direction.json').read_text(encoding='utf-8')
    story=(OUT/'story.json').read_text(encoding='utf-8')
    system="""You are Claude Opus 5.5, the film's coding director. Write COMPLETE
production-ready JavaScript for the requested original 1080x1920 Data Storytelling
film. Return only the typed JSON with javascript and editorial_notes. No markdown
fences in javascript. This is an authorized local film, no server actions.

Build contract:
- ES module film.js, imports * as E from './engine.js'; may also import easing
  from '/core/lib.js'. NO other dependencies/imports/network/CDN/tools.
- document has canvas id film; set actual width/height from innerWidth/innerHeight.
- const data=await(await fetch('./data.json')).json(). Data has duration, beats
  [{cue,operation,camera,annotation,sound,start,end}], words[{text,start,end}],
  captions[{start,end,words:[...]}], dataset. Final beat is retimed to start at
  'So novelty will not stretch the clock' so the entire ending has time to land.
- dataset: survey2005 {n:499,min_age:14,max_age:94}; samples2021 [293,263,262];
  design2026 {n:120,per_group:20,groups:['20–29','30–39','40–49','50–59','60–69','70+']}.
  Numeric chart marks must use these exact data fields. Don't fetch a dataset.
- Three self-hosted font faces are available: Newsreader './newsreader.ttf',
  Caveat './caveat.ttf', 'IBM Plex Mono' './ibmplexmono.ttf'. Load with FontFace
  or document.fonts.load before window.READY=true. No external font requests.
- Expose window.DUR=data.duration, window.render(t), window.READY, window.EV
  [{t,type,value?}], window.TEXTS(t). All visible non-caption labels need declared
  actual bounding boxes {id,text,x0,y0,x1,y1} in SCREEN PIXELS from the current
  transform. Use stable IDs per label; at least one readable real label remains
  in frame long enough. Render is deterministic for any t, no inter-frame state.
- Bottom captions from data.captions, max two readable lines, ~46px Newsreader,
  y1650-1820, hairline separator not a progress line; full phrase shown with
  active word emphasis. No fixed top header, no progress bar, no branding,
  no slide cards. Do not put text in the upper margin across the whole film.
- No audio element; local finishing adds unchanged Brainrot narration and foley.
- One physical sheet/world. Smooth intentional pan/push/pull/roll (<=.025 rad),
  camera follows pencil/marks; chart operations draw/morph/stretch instead of
  crossfading flat slides. Real data records and memory illustrations must be
  distinguishable. 'ILLUSTRATION' must be present during qualitative diagrams.
  Every real participant dot is one person; never draw fictitious ages/ratings.
- Labels short, mostly <=20 chars; give >=3 seconds readable hold. Dense study
  details can stay in pinned margin; avoid many simultaneous competing labels.
  Prevent tiny text and note/plot/caption overlaps. Zero baseline for count bars.
- Original art, no demo story/climate chart. Minimal helpers, 300-500 clear lines.

ENGINE CAVEAT: E.W=1920,E.H=1080 are LANDSCAPE constants. Do NOT call E.drawPaper,
applyCam,w2s,s2w,viewRect or caption directly for the vertical film. Draw your own
seeded paper/grid and vertical camera transform while using real E.pencilStroke,
E.inkShape, E.handText, E.dataDot, E.morphMark etc. E.drawPencil uses internal
1920x1080 buffers and resets the transform; to support a tip anywhere vertically,
draw it into a separate 1920x1080 OffscreenCanvas with tip [960,540], then composite
that canvas into the main canvas translated so [960,540] lands on your screen tip.
Clear that scratch canvas every frame. Use pencil s around0.6, angle fromlower-right;
keep its body away from freshly written text. Do not alter the upstream engine.

Editorial overrides to the supplied plan: no always-on title; a brief title can
be absent because the voice already reads it. Silence means effects/music pause,
not cutting the voice. Do not sonify imaginary memory counts: illustrative icons
get ordinary pencil foley; value sonification only for real numeric anchors.
End visually as a possibility, not proof that memories mechanically slow time.
"""
    # Large reference sources go through stdin, not Windows argv's size limit.
    result=llm.generate(system,
        'STYLE:\n'+style+'\nENGINE SOURCE/API:\n'+engine+'\nResearch notes:\n'+REFERENCES+'\nSPOKEN SCRIPT:\n'+story+'\nDIRECTION:\n'+direction,
        FilmSource,max_tokens=16000,provider='claude-code')
    target=HERE/'film/film.js';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(result.javascript,encoding='utf-8')
    save(OUT/'authorship.json',{'provider':'claude-code','model':MODEL,
        'javascript_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'editorial_notes':result.editorial_notes,'review_required_before_render':True})
    print('Opus-authored film source saved for review',flush=True)


def author_compact():
    """Only the chart/art layer; the established renderer handles the film shell."""
    target=HERE/'film/scenes.js'
    if target.exists():return
    os.environ['BRAINROT_COMPACT_AUTHOR']='1';setup_provider()
    os.environ['BRAINROT_LLM_TIMEOUT_SECONDS']='300'
    prompt="""Write ONLY a compact ES module of 100-160 lines, no full film shell.
Export function draw(g,i,p,len,d,h) returning a pencil tip [x,y] in local chart
coordinates. i is 0..15, p local seconds, len beat seconds, d.dataset contains
survey2005 {n:499,min_age:14,max_age:94}, samples2021 [293,263,262], design2026
{n:120,per_group:20,groups:['20–29','30–39','40–49','50–59','60–69','70+']}.
Helpers: h.label(id,text,x,y,size=38,color='#2B2723',font='Newsreader') draws
left-aligned at alphabetic baseline and registers bounds; h.line(points,color,
width=3,progress=1) uses actual Lemo pencilStroke; h.dot(x,y,r,color) uses Lemo
dataDot; h.shape(points,fill) uses Lemo inkShape. You may import * as E from
'./engine.js' but only use these known helpers for safe API. No imports otherwise.
All local artwork must fit x=-360..360,y=-490..490. Text <=24 chars, size>=30,
no title/header except chart labels. Return tip inside bounds. No fetch/audio,
DOM/camera/timing: caller handles everything. Every frame independent, deterministic.
No fakes: empirical unit counts exclusively from d.dataset. Memory sketches have
ILLUSTRATION prominently and NO measured memory-count axis. No progress bar.
Design 16 stages on continuous paper: 0 equal calendar cells;1 trip remembered
band widens over same fixed cell;2 equal hours;3 two lanes lived/looking back;
4 memory judgement;5 illustration blank before drawing;6 station,bowl,street
distinct icons;7 illustrative band spreads;8 repetitive commute/desk/dinner
icons;9 illustration collapses above same fixed week;10 hold the illustration
qualification;11 499 survey participants unit chart (n real dots) with ages14-94;
12 three study sample bars (293,263,262), baseline0, label SAMPLE SIZES, no causal
arrow/claim from counts;13 six equal study design groups20per, labelledDESIGN,
not outcome;14 empty mechanism cell and attention/emotion/pressure notes;
15 ordinary calendar cell plus one blue qualitative landmark, ending on it.
Use cream-paper blue/red graphite aesthetic, marks written/morphed via progress,
not slide cards. Warm and legible. Keep functions short and return a tip matching
the current write/draw action. Implement all16 stages with grouped branches.
Return requested JSON with javascript (raw source, no fences) and brief notes.
"""
    result=llm.generate(prompt,(OUT/'direction.json').read_text(encoding='utf-8'),FilmSource,max_tokens=6000,provider='claude-code')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(result.javascript,encoding='utf-8')
    save(OUT/'authorship.json',{'provider':'claude-code','model':MODEL,'scope':'Chart artwork/transformations; local wrapper handles render/camera/captions',
        'javascript_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'editorial_notes':result.editorial_notes,
        'earlier_full_film_request':'timed out after 1200 seconds, no usable output'})
    print('Compact Opus chart source ready',flush=True)


def build():
    source=HERE/'film/film.js'
    review=json.loads((OUT/'source-review.json').read_text())
    if not review.get('reviewed') or review['sha256']!=hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError('Review generated source before running it')
    manifest=json.loads((OUT/'manifest.json').read_text())
    words=json.loads((OUT/'words.json').read_text())
    direction=Direction.model_validate_json((OUT/'direction.json').read_text(encoding='utf-8'))
    norm=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
    spoken=[norm(w['text']) for w in words];beats=[]
    for i,beat in enumerate(direction.beats):
        cue='So novelty will not stretch the clock' if i==len(direction.beats)-1 else beat.cue
        target=[norm(w) for w in cue.split()]
        found=[j for j in range(len(words)-len(target)+1) if spoken[j:j+len(target)]==target]
        if len(found)!=1:raise ValueError('Cue must occur exactly once: '+cue)
        start=0 if not beats else words[found[0]]['start']
        if beats and start<=beats[-1]['start']:raise ValueError('Nonchronological cues')
        beats.append({**beat.model_dump(),'cue':cue,'start':start})
    for i,b in enumerate(beats):b['end']=beats[i+1]['start'] if i+1<len(beats) else manifest['duration']
    captions=[];group=[]
    for w in words:
        if group and (len(group)>=9 or w['start']-group[0]['start']>3.5 or w['start']-group[-1]['end']>.65):
            captions.append({'start':group[0]['start'],'end':min(w['start'],group[-1]['end']+.6),'words':group});group=[]
        group.append(w)
    if group:captions.append({'start':group[0]['start'],'end':manifest['duration'],'words':group})
    dataset=json.loads((HERE/'dataset.json').read_text(encoding='utf-8'))
    save(OUT/'data.json',{'duration':manifest['duration'],'beats':beats,'words':words,'captions':captions,'dataset':dataset})
    if review.get('scenes_sha256')!=hashlib.sha256((HERE/'film/scenes.js').read_bytes()).hexdigest():
        raise ValueError('Review the chart source before rendering')
    for name in ['index.html','film.js','scenes.js']:shutil.copyfile(HERE/'film'/name,OUT/name)
    shutil.copyfile(HERE/'guidance/dataviz/demo/engine.js',OUT/'engine.js')
    for font in (HERE/'fonts').glob('*'):shutil.copyfile(font,OUT/font.name)
    for name in ['CREDITS','FACTS.md','TREATMENT.md']:
        if (HERE/name).exists():shutil.copyfile(HERE/name,OUT/name)
    tools=common();tools.browser_environment()
    times=[str(round((b['start']+b['end'])/2,2)) for b in beats]
    tools.run(['node',LEMO/'core/render/still.mjs',OUT,*times,'--size','1080x1920','--out',OUT/'stills'],cwd=LEMO,log=OUT/'stills.log')
    tools.run(['node',LEMO/'core/render/readcheck.mjs',OUT,'--size','1080x1920'],cwd=LEMO,log=OUT/'readcheck.log')
    tools.run(['node',LEMO/'core/render/events.mjs',OUT,'--size','1080x1920'],cwd=LEMO,log=OUT/'events.log')
    print('Actual style frames, reading checks and sound events ready',flush=True)


def produce():
    tools=common();tools.browser_environment()
    if not (OUT/'raw.mp4').exists():
        tools.run(['node',LEMO/'core/render/video.mjs',OUT,'--size','1080x1920','--fps','30','--workers','2','--out',OUT/'raw.mp4'],cwd=LEMO,log=OUT/'render.log')
    python=ROOT/'experiments/coffee-comparison/.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    tools.run([python,HERE/'mix.py',OUT],log=OUT/'mix.log')
    tools.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',OUT/'raw.mp4','-i',OUT/'mix.wav',
        '-map','0:v','-map','1:a','-c:v','libx264','-preset','veryfast','-crf','23',*render.VIDEO_RATE_OPTIONS,
        '-af',render.VOICE_FILTER,'-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',OUT/'final.mp4'],log=OUT/'master.log')
    render.check_video(str(OUT/'final.mp4'));print('Final Data Storytelling film ready',flush=True)


def playback():
    tools=common();tools.browser_environment()
    tools.run(['node',HERE/'playback.mjs',OUT],log=OUT/'playback.log',timeout=240)


def repair_finish():
    tools=common();r=json.loads((OUT/'repair.json').read_text())
    start,end=r['from'],r['to']
    graph=f'[0:v]split=2[h][t];[h]trim=end={start},setpts=PTS-STARTPTS[a];[t]trim=start={end},setpts=PTS-STARTPTS[c];[1:v]setpts=PTS-STARTPTS[b];[a][b][c]concat=n=3:v=1:a=0[v]'
    tools.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',OUT/'raw.mp4','-i',OUT/'repair.mp4','-i',OUT/'mix.wav',
        '-filter_complex',graph,'-map','[v]','-map','2:a','-c:v','libx264','-preset','veryfast','-crf','23',*render.VIDEO_RATE_OPTIONS,
        '-af',render.VOICE_FILTER,'-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',OUT/'final.mp4'],log=OUT/'repair-master.log')
    render.check_video(str(OUT/'final.mp4'));print('Corrected frame window assembled into final film',flush=True)


if __name__=='__main__':
    stages={'prepare':prepare,'direct':direct,'author':author,'author-compact':author_compact,'build':build,'produce':produce,'playback':playback,'repair-finish':repair_finish}
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=stages)
    args=parser.parse_args();stages[args.stage]()
