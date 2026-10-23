"""Original vector-style drawing tools for the isolated explainer prototype."""
from functools import lru_cache
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
ROOT = Path(__file__).resolve().parents[2]
BG = '#101c26'
PANEL = '#192b37'
INK = '#f6f0df'
MUTED = '#9caeb5'
COOL = '#67d9cf'
WARM = '#ff916f'
GOLD = '#ecc97b'
LINE = '#304651'

def ease(t):
    t = max(0., min(1., t))
    return 1 - (1-t)**3

def smooth(t):
    t=max(0.,min(1.,t))
    return t*t*(3-2*t)

def reveal(t, start=0, length=.8):
    return ease((t-start)/length)

@lru_cache(maxsize=64)
def font(size, bold=False):
    path=Path(__file__).parent/'assets'/'DMSans.ttf'
    if not path.exists():
        path=ROOT/'brainrot/assets/fonts/Anton-Regular.ttf'
    f=ImageFont.truetype(str(path),size)
    if hasattr(f,'set_variation_by_axes') and path.name=='DMSans.ttf':
        f.set_variation_by_axes([14,700 if bold else 450])
    return f

def text(im, value, xy, size=42, fill=INK, anchor='mm', bold=False, max_width=None):
    d=ImageDraw.Draw(im)
    while max_width and d.textlength(value,font=font(size,bold))>max_width and size>20:
        size-=1
    d.text(xy,value,font=font(size,bold),fill=fill,anchor=anchor,stroke_width=0)

def multiline(im, lines, xy, size=80, fill=INK, spacing=1.1, bold=True):
    if isinstance(lines,str): lines=lines.split('\n')
    for i,value in enumerate(lines):
        text(im,value,(xy[0],xy[1]+i*size*spacing),size,fill,bold=bold,max_width=930)

def pill(im, label, box, color=COOL, size=32, filled=False):
    d=ImageDraw.Draw(im)
    d.rounded_rectangle(box,radius=(box[3]-box[1])/2,fill=color if filled else PANEL,outline=None if filled else color,width=2)
    text(im,label,((box[0]+box[2])/2,(box[1]+box[3])/2-1),size,BG if filled else color,bold=True,max_width=box[2]-box[0]-32)

def line(im, points, color=LINE, width=3):
    ImageDraw.Draw(im).line(points,fill=color,width=width,joint='curve')

def arrow(im, start, end, color=WARM, width=9, progress=1):
    x=start[0]+(end[0]-start[0])*progress
    y=start[1]+(end[1]-start[1])*progress
    line(im,[start,(x,y)],color,width)
    if progress>.03:
        a=math.atan2(end[1]-start[1],end[0]-start[0]); r=22
        ImageDraw.Draw(im).polygon([(x,y),(x-r*math.cos(a-.48),y-r*math.sin(a-.48)),(x-r*math.cos(a+.48),y-r*math.sin(a+.48))],fill=color)

def frame(index,t,duration,kicker,headline,subhead=''):
    im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im)
    for x in range(0,W,90): d.line((x,500,x,1530),fill='#14232e',width=1)
    for y in range(540,1531,90): d.line((50,y,1030,y),fill='#14232e',width=1)
    d.ellipse((740,-280,1260,240),outline=LINE,width=1)
    text(im,'BRAINROT / FIELD NOTES',(72,92),26,MUTED,anchor='lm',bold=True)
    text(im,f'{index+1:02d} / 10',(1008,92),26,MUTED,anchor='rm')
    line(im,[(72,140),(1008,140)],LINE,2)
    text(im,kicker.upper(),(72,204),30,COOL,anchor='lm',bold=True)
    y=302+18*(1-reveal(t,0,.7))
    multiline(im,headline,(540,y),82,spacing=1.08)
    if subhead: text(im,subhead,(540,465),34,MUTED,max_width=920)
    line(im,[(72,1690),(1008,1690)],LINE,2)
    text(im,'A SMALL SCIENCE STORY',(72,1745),24,MUTED,anchor='lm')
    for i in range(10):
        x=72+i*95
        color=COOL if i<index else (INK if i==index else LINE)
        d.rounded_rectangle((x,1805,x+78,1811),radius=3,fill=color)
        if i==index:
            d.rounded_rectangle((x,1805,x+78*min(1,t/max(duration,.001)),1811),radius=3,fill=COOL)
    return im

def block(im, box, material='metal', accent=COOL):
    d=ImageDraw.Draw(im); x0,y0,x1,y1=box
    d.rounded_rectangle(box,radius=26,fill='#293d49' if material=='metal' else '#614d3e',outline=accent,width=3)
    if material=='metal':
        for x in range(int(x0+28),int(x1-15),24):
            d.line((x,y0+22,x,y1-22),fill='#344c59',width=2)
        d.line((x0+22,y0+12,x1-22,y0+12),fill='#90acae',width=3)
    else:
        for j in range(5):
            yy=y0+26+j*(y1-y0-52)/4
            pts=[(x0+16+k*(x1-x0-32)/20,yy+6*math.sin(k*.7+j)) for k in range(21)]
            d.line(pts,fill='#9a7958',width=3)

def hand(im, cx, cy, scale=1, color=WARM):
    """Stylized fingertip, a diagram rather than an anatomical illustration."""
    d=ImageDraw.Draw(im); s=scale
    d.rounded_rectangle((cx-66*s,cy-160*s,cx+66*s,cy+76*s),radius=65*s,fill=color)
    d.rounded_rectangle((cx-42*s,cy-132*s,cx+42*s,cy-30*s),radius=30*s,outline='#f9c0a2',width=3)
    d.line((cx-28*s,cy+24*s,cx+28*s,cy+24*s),fill='#c96e58',width=3)

def thermometer(im,cx,cy,label='22°',color=COOL):
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((cx-18,cy-110,cx+18,cy+40),radius=18,fill=PANEL,outline=color,width=3)
    d.ellipse((cx-30,cy+15,cx+30,cy+75),fill=color)
    d.rounded_rectangle((cx-6,cy-75,cx+6,cy+35),radius=6,fill=color)
    text(im,label,(cx+55,cy-32),52,color,anchor='lm',bold=True)

def heat_dots(im, start, end, t, speed=1, color=WARM, count=6, radius=7):
    d=ImageDraw.Draw(im)
    for i in range(count):
        p=(t*speed*.2+i/count)%1
        x=start[0]+(end[0]-start[0])*p; y=start[1]+(end[1]-start[1])*p
        d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=color)

def note(im,label,color=MUTED,y=1585,size=34):
    text(im,label,(540,y),size,color,max_width=920)
