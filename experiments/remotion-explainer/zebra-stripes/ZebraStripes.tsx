import React from 'react';
import {AbsoluteFill,interpolate,spring,staticFile,useCurrentFrame} from 'remotion';
import {evolvePath,interpolatePath} from '@remotion/paths';
import {noise2D} from '@remotion/noise';
import {CameraMotionBlur} from '@remotion/motion-blur';
import script from './script.json';
import {Dial,EZ,FPS,Glyphs,H,Halftone,W,camAt,clip,ez,mono,pts,seg,toD,Tube} from '../coffee-sci/kit';

// Silent explainer built from docs/motion-graphics-recipe.md: pastel phases, one hero (a zebra coat patch) that
// draws on, morphs, shrinks, splits into a comparison and returns. Driven by script.json. No frame, no film filters.
export const ZEBRA_STRIPES_FRAMES=Math.round(script.duration*FPS);
const P={ink:'#2a2433',dim:'#7d7788',coral:'#ff6b5e',coralHi:'#ffc6bd',green:'#1f9d63',white:'#ffffff',mintG:'#6fd39a',
  cream:'#fdf7ee',butter:'#fff3c4',sky:'#d9ecff',lilac:'#e6defc',dot:'#f0b999',stripeHi:'#8a8296'};
const TXT:Record<string,string>={ink:P.ink,coral:P.coral,green:P.green};
const BG=[P.cream,P.butter,P.sky,P.lilac];
const CX=540,CY=960,R=230,N=240,S=11;
const RING=toD(pts(N,t=>{const a=t*Math.PI*2;return [CX+R*Math.cos(a),CY+R*Math.sin(a)];}));
const RINGPLAIN=toD(pts(N,t=>[300+170*Math.cos(t*Math.PI*2),880+170*Math.sin(t*Math.PI*2)]));
const STRAIGHT=Array.from({length:S},(_,i)=>toD(pts(60,t=>[CX-250+i*50,CY-260+520*t])));
const WAVY=Array.from({length:S},(_,i)=>toD(pts(60,t=>[CX-250+i*50+30*Math.sin(t*7+i*1.1)*(1-.3*Math.abs(2*t-1))+12*Math.sin(t*19+i),CY-260+520*t])));
const IDEAS=['camouflage','confuse predators','stay cool','social signals','dodge biting flies'];
const BOUNDS=Object.values(script.phases).map(p=>p[0]).slice(1);
const K1=(t:number,a:number[],b:number[])=>interpolate(t,a,b,{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});
const rnd=(i:number,s:number)=>{const v=Math.sin(i*127.1+s*311.7)*43758.5453;return v-Math.floor(v);};

// flies: ten per coat. Plain coat: they slow down and land. Striped coat: they keep their speed and bounce or fly past.
const NF=10,LAND:Record<string,(i:number)=>boolean>={plain:i=>i!==3,striped:i=>i===6};
const fly=(i:number,side:'plain'|'striped',T:number)=>{
  const cx=side==='plain'?300:780,cy=880,r=170,ts=10.3+i*.3,dur=.9,uu=(T-ts)/dur;
  const a=rnd(i,side==='plain'?1:2)*Math.PI*2,dx=Math.cos(a),dy=Math.sin(a),start:[number,number]=[cx+560*dx,cy+560*dy];
  if(uu<0)return null;
  if(LAND[side](i)){
    const tr=rnd(i,7)*r*.55,tp=rnd(i,8)*Math.PI*2,tg:[number,number]=[cx+tr*Math.cos(tp),cy+tr*Math.sin(tp)],p=1-Math.pow(1-clip(uu),3);
    return {x:start[0]+(tg[0]-start[0])*p+(uu>=1?Math.sin(T*9+i)*1.5:0),y:start[1]+(tg[1]-start[1])*p,landed:uu>=1};
  }
  const edge:[number,number]=[cx+(r+8)*dx,cy+(r+8)*dy];
  if(i%2===0){ // bounce back out
    if(uu<.75){const p=uu/.75;return {x:start[0]+(edge[0]-start[0])*p,y:start[1]+(edge[1]-start[1])*p,landed:false};}
    const q=EZ.out(clip((uu-.75)/.9));return {x:edge[0]+dx*300*q-dy*70*Math.sin(q*3),y:edge[1]+dy*300*q+dx*70*Math.sin(q*3),landed:false};
  }
  const far:[number,number]=[cx-560*dx-dy*140,cy-560*dy+dx*140],p=clip(uu/1.8); // fly straight past
  return {x:start[0]+(far[0]-start[0])*p,y:start[1]+(far[1]-start[1])*p,landed:false};
};
const landedCount=(side:'plain'|'striped',T:number)=>Array.from({length:NF}).filter((_,i)=>LAND[side](i)&&T>=10.3+i*.3+.9).length;
function Fly({x,y,i,T,o=1}:{x:number,y:number,i:number,T:number,o?:number}){
  const w=30+26*Math.sin(T*70+i*2);
  return <g transform={`translate(${x} ${y}) scale(1.7)`} opacity={o}>
    <ellipse cx={-5} cy={-6} rx={11} ry={4.5} transform={`rotate(${-w})`} fill={P.white} stroke={P.ink} strokeWidth={1.6} opacity={.85}/>
    <ellipse cx={5} cy={-6} rx={11} ry={4.5} transform={`rotate(${w})`} fill={P.white} stroke={P.ink} strokeWidth={1.6} opacity={.85}/>
    <ellipse rx={9} ry={6} fill={P.ink}/><circle cx={8} cy={-1} r={3.5} fill={P.coral}/>
  </g>;
}

export const ZebraStripes=()=>{
  const frame=useCurrentFrame(),T=frame/FPS;
  const {zoom,cy}=camAt(T,script.cam),roll=noise2D('r',T*.3,0)*.5;
  const morph=ez(EZ.inout,T,2.4,1.2);
  const ringD=evolvePath(ez(EZ.inout,T,.2,1.0),RING);
  const kT=[0,4.1,5.0,9.3,10.3,14.3,15.2,18];
  const gx=K1(T,kT,[CX,CX,CX,CX,780,780,CX,CX]),gy=K1(T,kT,[CY,CY,560,560,880,880,1540,1540]),gs=K1(T,kT,[1,1,.38,.38,.74,.74,.4,.4]);
  const phase=Object.entries(script.phases).find(([,[a,b]])=>T>=a&&T<b)?.[0]??'card';
  const bgIdx=BOUNDS.filter(b=>T>=b).length;
  const card=spring({frame:frame-14.6*FPS,fps:FPS,config:{damping:14,stiffness:90}}),chips=ez(EZ.out,T,15.6,.7);
  const plainRing=evolvePath(ez(EZ.inout,T,9.6,.8),RINGPLAIN);

  const content=<AbsoluteFill style={{background:BG[bgIdx]}}>
    {BOUNDS.map((b,i)=>{const p=(T-(b-.25))/.5;if(p<0||p>1)return null;const w=W*1.5;
      return <div key={i} style={{position:'absolute',top:-50,height:H+100,width:w,left:W-ez(EZ.inout,p,0,1)*(W+w),background:BG[i+1],transform:'skewX(-12deg)'}}/>;})}
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{position:'absolute',inset:0}}>
      <defs><clipPath id="disc"><circle cx={CX} cy={CY} r={R-8}/></clipPath></defs>
      <g transform={`translate(540 960) rotate(${roll}) scale(${zoom}) translate(-540 ${-cy})`}>
        {/* idea cards: the five hypotheses compared in 2014 */}
        {T<9.6&&IDEAS.map((name,i)=>{const win=i===4,a=ez(EZ.out,T,4.6+i*.3,.5)*(1-seg(T,9.0,.35)),dim=win?1:1-.55*ez(EZ.out,T,8.0,.4),pop=win?1+.04*ez(EZ.out,T,8.2,.4):1;
          const mark=evolvePath(ez(EZ.inout,T,win?8.2:6.5+i*.25,.35),win?'M0 22L16 38L44 0':'M0 0L38 38M38 0L0 38');
          return <g key={name} transform={`translate(90 ${740+i*150+(1-a)*60}) translate(450 65) scale(${pop}) translate(-450 -65)`} opacity={a*dim}>
            <rect width={900} height={130} rx={26} fill={P.white} stroke={win&&T>8.2?P.green:P.ink} strokeOpacity={win&&T>8.2?1:.12} strokeWidth={win&&T>8.2?5:3}/>
            <text x={34} y={50} fontSize={17} fill={P.dim} style={{...mono,letterSpacing:2}}>idea {i+1}</text>
            <text x={34} y={100} fontSize={44} fontWeight={800} fill={P.ink}>{name}</text>
            <g transform="translate(810 40)"><path d={win?'M0 22L16 38L44 0':'M0 0L38 38M38 0L0 38'} fill="none" stroke={win?P.green:P.coral} strokeWidth={9} strokeLinecap="round" strokeLinejoin="round" {...mark}/></g>
            <text x={780} y={112} textAnchor="end" fontSize={17} fill={win?P.green:P.dim} style={{...mono,letterSpacing:2}} opacity={seg(T,win?8.4:6.9+i*.25,.3)}>{win?'best match':'no consistent match'}</text>
          </g>;})}
        {/* landing comparison: a plain coat appears next to the striped hero */}
        {phase==='test'&&<g>
          <circle cx={300} cy={880} r={170} fill={P.white} opacity={seg(T,9.8,.3)}/>
          <Tube d={RINGPLAIN} w={14} color={P.coral} light={P.coralHi} outline={P.ink} dash={plainRing}/>
          <g style={mono} fontSize={24} fontWeight={700} fill={P.ink} textAnchor="middle" opacity={seg(T,9.9,.4)}><text x={300} y={1110}>plain coat</text><text x={780} y={1110}>striped coat</text></g>
          {(['plain','striped'] as const).map(side=>Array.from({length:NF}).map((_,i)=>{
            const p=fly(i,side,T);if(!p)return null;const trail=[1,2,3,4].map(k=>fly(i,side,T-k*.035));
            return <g key={side+i}>{trail.map((q,k)=>q&&!p.landed?<circle key={k} cx={q.x} cy={q.y} r={6-k} fill={P.ink} opacity={.28-k*.05}/>:null)}<Fly x={p.x} y={p.y} i={i} T={T}/></g>;}))}
        </g>}
        {/* hero coat patch: halftone light, stripes draw on and morph straight to wavy, coral ring */}
        <g transform={`translate(${gx} ${gy}) scale(${gs}) translate(${-CX} ${-CY})`}>
          <Halftone cx={CX} cy={CY-20} rx={330} ry={430} appear={ez(EZ.out,T,.1,1)*(phase==='hook'?1:.6)} t={0} color={P.dot}/>
          <circle cx={CX} cy={CY} r={R} fill={P.white} opacity={seg(T,.4,.5)}/>
          <g clipPath="url(#disc)">{STRAIGHT.map((_,i)=>{const d=interpolatePath(morph,STRAIGHT[i],WAVY[i]);
            return <Tube key={i} d={d} w={22} color={P.ink} light={P.stripeHi} outline={P.ink} dash={evolvePath(ez(EZ.inout,T,.9+i*.08,.7),d)}/>;})}</g>
          <Tube d={RING} w={18} color={P.coral} light={P.coralHi} outline={P.ink} dash={ringD}/>
        </g>
        {/* flies bounce off the hero on the answer card */}
        {T>15.3&&[0,1,2].map(k=>{const ang=-Math.PI/2+(k-1)*.9+Math.sin(T*1.3+k)*.25,dist=R*.4+22+60*Math.abs(Math.sin(T*2.6+k*1.9));
          return <Fly key={k} x={540+dist*Math.cos(ang)} y={1540+dist*Math.sin(ang)} i={k} T={T} o={seg(T,15.3,.3)}/>;})}
        {/* source card */}
        <g transform={`translate(0 ${(1-card)*2300}) rotate(${-4*(1-card)} 540 790)`}>
          <rect x={90} y={358} width={900} height={900} rx={32} fill="#c9bdf0"/>
          <rect x={90} y={340} width={900} height={900} rx={32} fill={P.white}/>
          <text x={140} y={405} fontSize={20} fill={P.dim} style={mono}>research summary</text>
          <path d="M140 430H940" stroke={P.ink} strokeWidth={3}/>
          <text x={136} y={595} fontSize={150} fontWeight={900} fill={P.ink} letterSpacing={-2}>BITING</text>
          <text x={136} y={745} fontSize={150} fontWeight={900} fill={P.coral} letterSpacing={-2}>FLIES</text>
          <text x={140} y={825} fontSize={40} fontWeight={700} fill={P.ink}>circle stripes as often as plain coats,</text>
          <text x={140} y={877} fontSize={40} fontWeight={700} fill={P.ink}>but fail to slow down and bounce off.</text>
          <g transform="translate(140 940)" opacity={chips}>
            <rect width={380*chips} height={62} rx={31} fill={P.mintG}/><text x={30} y={40} fontSize={22} fontWeight={800} fill={P.ink} style={{...mono,letterSpacing:2}} opacity={chips>.6?1:0}>best supported idea</text>
            <rect x={400} width={400*chips} height={62} rx={31} fill="none" stroke={P.ink} strokeWidth={3}/><text x={426} y={40} fontSize={20} fontWeight={800} fill={P.ink} style={{...mono,letterSpacing:2}} opacity={chips>.6?1:0}>why? still a hypothesis</text>
          </g>
          <text x={140} y={1075} fontSize={18} fill={P.dim} style={{...mono,letterSpacing:2}}>other benefits are not ruled out</text>
          <path d="M140 1110H940" stroke={P.ink} strokeWidth={2} opacity={.2}/>
          <text x={140} y={1200} fontSize={14} fill={P.dim} style={{...mono,letterSpacing:1}}>source: caro et al. 2014 · caro et al. 2019 · kojima et al. 2019</text>
        </g>
      </g>
      {script.dials.map(dl=><Dial key={dl.id} x={dl.x} y={dl.y} label={dl.label} unit={dl.unit} value={landedCount(dl.id as 'plain'|'striped',T)} max={dl.max} decimals={dl.decimals} appear={ez(EZ.out,T,dl.at,.5)*(1-seg(T,dl.until,.3))} color={P.coral} fg={P.ink} track="rgba(42,36,51,.15)"/>)}
    </svg>
    {script.texts.map((tx,i)=>{const v=(T>=tx.at-.05&&T<tx.until+.3)?1-seg(T,tx.until,.25):0;
      return v>0?<div key={i} style={{position:'absolute',inset:0,opacity:v}}><Glyphs text={tx.text} frame={frame} startS={tx.at} size={tx.size} color={TXT[tx.color]} y={tx.y} font={tx.font} ca={false} wave={(tx as {wave?:number}).wave??0}/></div>:null;})}
    {phase==='test'?<div style={{...mono,position:'absolute',bottom:100,width:W,textAlign:'center',fontSize:18,color:P.dim,letterSpacing:3}}>fly paths and counts are schematic, not data</div>:null}
  </AbsoluteFill>;
  return <AbsoluteFill style={{background:BG[0],fontFamily:'DM Sans, Arial, sans-serif'}}>
    <style>{`@font-face{font-family:'DM Sans';src:url('${staticFile('DMSans.ttf')}')}`}</style>
    <CameraMotionBlur shutterAngle={140} samples={4}>{content}</CameraMotionBlur>
  </AbsoluteFill>;
};
