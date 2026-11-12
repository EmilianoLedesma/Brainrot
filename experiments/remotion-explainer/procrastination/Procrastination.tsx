import React from 'react';
import {AbsoluteFill,interpolate,spring,staticFile,useCurrentFrame} from 'remotion';
import {evolvePath,interpolatePath} from '@remotion/paths';
import {noise2D} from '@remotion/noise';
import {CameraMotionBlur} from '@remotion/motion-blur';
import script from './script.json';
import {Dial,EZ,FPS,Glyphs,H,Halftone,W,camAt,clip,ez,mono,pts,seg,toD,Tube} from '../coffee-sci/kit';

// Silent explainer built from docs/motion-graphics-recipe.md for the saved story "Your Brain Is Cooked, Not Lazy".
// Hero: a task-mountain that draws on, shrinks, morphs into a small pile once the work starts, and returns on the answer card.
// Driven by script.json. No frame, no film filters. The dread chart is schematic and captioned as illustrative.
export const PROCRASTINATION_FRAMES=Math.round(script.duration*FPS);
const P={ink:'#2a2433',dim:'#7d7788',coral:'#ff6b5e',coralHi:'#ffc6bd',green:'#1f9d63',white:'#ffffff',mintG:'#6fd39a',
  cream:'#fdf7ee',peach:'#ffe3d6',mint:'#dcf5e6',lilac:'#e6defc',dot:'#f0b999',hi:'#8a8296',zoneA:'#ffd9cc',zoneB:'#cdeedd'};
const TXT:Record<string,string>={ink:P.ink,coral:P.coral,green:P.green};
const BG=[P.cream,P.peach,P.mint,P.lilac];
const CX=540,CY=960,N=240;
const poly=(v:[number,number][],n:number)=>{const c=[...v,v[0]];
  return toD(pts(n,t=>{const f=t*(c.length-1),i=Math.min(c.length-2,Math.floor(f)),k=f-i;return [CX+c[i][0]+(c[i+1][0]-c[i][0])*k,CY+c[i][1]+(c[i+1][1]-c[i][1])*k];}));};
const MOUNT=poly([[-300,220],[-120,-80],[-60,-10],[0,-260],[130,-60],[190,-120],[300,220]],N);
const PILE=poly([[-300,220],[-220,140],[-150,95],[-70,110],[10,55],[120,95],[300,220]],N);
const TRIG=['boring','scary','confusing'];
const RELIEF=['your phone','a snack','cleaning the kitchen'];
const BOUNDS=Object.values(script.phases).map(p=>p[0]).slice(1);
const K1=(t:number,a:number[],b:number[])=>interpolate(t,a,b,{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});

// chart: x 130..950, y 1220 (dread 0) .. 800 (dread 100); illustrative curve, peak at "start"
const CHX0=130,CHX1=950,CHY=1220,CHK=4.2,START=540;
const dread=(u:number)=>u<.5?18+77*Math.pow(u/.5,1.6):95-60*(1-Math.pow(1-(u-.5)/.5,2));
const curveAt=(a:number,b:number)=>toD(pts(60,t=>{const u=a+(b-a)*t;return [CHX0+(CHX1-CHX0)*u,CHY-dread(u)*CHK];}));
const CURVE_A=curveAt(0,.5),CURVE_B=curveAt(.5,1);
const AXES='M130 1220H950M130 1220V780';
const cursorU=(T:number)=>T<10.2?0:T<12.2?.5*EZ.inout(seg(T,10.2,2.0)):T<12.9?.5:.5+.5*EZ.inout(seg(T,12.9,1.7));

export const Procrastination=()=>{
  const frame=useCurrentFrame(),T=frame/FPS;
  const {zoom,cy}=camAt(T,script.cam),roll=noise2D('r',T*.3,0)*.5;
  const phase=Object.entries(script.phases).find(([,[a,b]])=>T>=a&&T<b)?.[0]??'card';
  const bgIdx=BOUNDS.filter(b=>T>=b).length;
  const morph=ez(EZ.inout,T,12.9,1.4);
  const heroD=interpolatePath(morph,MOUNT,PILE);
  const heroDash=evolvePath(ez(EZ.inout,T,.2,1.0),MOUNT);
  const kT=[0,4.3,5.2,9.5,10.3,14.9,15.8,20];
  const gx=K1(T,kT,[CX,CX,CX,CX,230,230,CX,CX]),gy=K1(T,kT,[1000,1000,500,500,560,560,1560,1560]),gs=K1(T,kT,[1,1,.3,.3,.3,.3,.4,.4]);
  const card=spring({frame:frame-15*FPS,fps:FPS,config:{damping:14,stiffness:90}}),chips=ez(EZ.out,T,16.0,.7);
  const u=cursorU(T),cx=CHX0+(CHX1-CHX0)*u,cyy=CHY-dread(u)*CHK,dv=dread(u);
  const curveA=evolvePath(Math.max(.0001,Math.min(1,u/.5)),CURVE_A),curveB=evolvePath(Math.max(.0001,(u-.5)/.5),CURVE_B);
  const badge=ez(EZ.out,T,1.8,.4)*(1-seg(T,13.0,.9));
  const check=evolvePath(ez(EZ.inout,T,17.4,.5),'M-55 10L-15 50L60 -40');
  const dl=script.dial;

  const content=<AbsoluteFill style={{background:BG[bgIdx]}}>
    {BOUNDS.map((b,i)=>{const p=(T-(b-.25))/.5;if(p<0||p>1)return null;const w=W*1.5;
      return <div key={i} style={{position:'absolute',top:-50,height:H+100,width:w,left:W-ez(EZ.inout,p,0,1)*(W+w),background:BG[i+1],transform:'skewX(-12deg)'}}/>;})}
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{position:'absolute',inset:0}}>
      <g transform={`translate(540 960) rotate(${roll}) scale(${zoom}) translate(-540 ${-cy})`}>
        {/* alarm: three triggers fill a threat bar, then three quick reliefs take over */}
        {phase==='alarm'&&TRIG.map((name,i)=>{const a=ez(EZ.out,T,4.7+i*.3,.5)*(1-seg(T,6.7,.3));
          return <g key={name} transform={`translate(90 ${790+i*180+(1-a)*60})`} opacity={a}>
            <rect width={900} height={140} rx={26} fill={P.white} stroke={P.ink} strokeOpacity={.12} strokeWidth={3}/>
            <text x={34} y={48} fontSize={17} fill={P.dim} style={{...mono,letterSpacing:2}}>the task feels</text>
            <text x={34} y={110} fontSize={52} fontWeight={800} fill={P.ink}>{name}</text>
            <rect x={470} y={50} width={380} height={34} rx={17} fill="rgba(42,36,51,.1)"/>
            <rect x={470} y={50} width={380*ez(EZ.out,T,5.0+i*.3,.9)} height={34} rx={17} fill={P.coral}/>
            <text x={470} y={118} fontSize={16} fill={P.coral} style={{...mono,letterSpacing:2}}>small threat</text>
          </g>;})}
        {phase==='alarm'&&RELIEF.map((name,i)=>{const a=ez(EZ.out,T,7.0+i*.3,.5),dim=1-.5*ez(EZ.out,T,8.4,.4);
          const mark=evolvePath(ez(EZ.inout,T,7.4+i*.3,.35),'M0 22L16 38L44 0');
          return <g key={name} transform={`translate(90 ${790+i*180+(1-a)*60})`} opacity={a*dim}>
            <rect width={900} height={140} rx={26} fill={P.white} stroke={P.ink} strokeOpacity={.12} strokeWidth={3}/>
            <text x={34} y={48} fontSize={17} fill={P.dim} style={{...mono,letterSpacing:2}}>fastest relief</text>
            <text x={34} y={110} fontSize={52} fontWeight={800} fill={P.ink}>{name}</text>
            <rect x={540} y={42} width={300} height={56} rx={28} fill={P.mintG} opacity={seg(T,7.5+i*.3,.3)}/>
            <text x={566} y={79} fontSize={22} fontWeight={800} fill={P.ink} style={{...mono,letterSpacing:2}} opacity={seg(T,7.6+i*.3,.3)}>relief now</text>
            <g transform="translate(760 36)"><path d="M0 22L16 38L44 0" fill="none" stroke={P.green} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" {...mark}/></g>
          </g>;})}
        {/* dread chart: schematic, with a cursor that rides the curve */}
        {phase==='dread'&&<g opacity={ez(EZ.out,T,9.9,.4)}>
          <rect x={CHX0} y={780} width={START-CHX0} height={CHY-780} fill={P.zoneA} opacity={.8}/>
          <rect x={START} y={780} width={CHX1-START} height={CHY-780} fill={P.zoneB} opacity={.9}/>
          <text x={CHX0+20} y={818} fontSize={20} fill={P.coral} style={{...mono,letterSpacing:2}}>imagining it</text>
          <text x={CHX1-20} y={818} textAnchor="end" fontSize={20} fill={P.green} style={{...mono,letterSpacing:2}}>doing it</text>
          <path d={AXES} fill="none" stroke={P.ink} strokeWidth={5} strokeLinecap="round" {...evolvePath(ez(EZ.inout,T,9.9,.7),AXES)}/>
          <path d={`M${START} 780V1220`} stroke={P.ink} strokeWidth={3} strokeDasharray="10 12" opacity={.35*seg(T,10.0,.3)}/>
          <Tube d={CURVE_A} w={14} color={P.coral} light={P.coralHi} outline={P.ink} dash={curveA}/>
          {u>.5&&<Tube d={CURVE_B} w={14} color={P.green} light="#b8ecd0" outline={P.ink} dash={curveB}/>}
          {T>10.2&&[3,2,1].map(k=>{const uu=cursorU(T-k*.06);return <circle key={k} cx={CHX0+(CHX1-CHX0)*uu} cy={CHY-dread(uu)*CHK} r={16-k*3} fill={uu<.5?P.coral:P.green} opacity={.35-k*.07}/>;})}
          <circle cx={cx} cy={cyy} r={20} fill={u<.5?P.coral:P.green} stroke={P.ink} strokeWidth={5}/>
          <g transform={`translate(${START} 1262) scale(${ez(EZ.out,T,12.2,.4)})`} opacity={ez(EZ.out,T,12.2,.4)}>
            <rect x={-70} y={-26} width={140} height={52} rx={26} fill={P.ink}/><text y={8} textAnchor="middle" fontSize={22} fontWeight={800} fill={P.white} style={{...mono,letterSpacing:3}}>start</text>
          </g>
        </g>}
        {/* hero: the task mountain draws on, shrinks, becomes a small pile once work starts, returns on the answer card */}
        <g transform={`translate(${gx} ${gy}) scale(${gs}) translate(${-CX} ${-CY})`}>
          <Halftone cx={CX} cy={CY-20} rx={330} ry={430} appear={ez(EZ.out,T,.1,1)*(phase==='hook'?1:.5)} t={0} color={P.dot}/>
          <path d={heroD} fill={P.coralHi} opacity={seg(T,.7,.6)}/>
          <Tube d={heroD} w={18} color={P.ink} light={P.hi} outline={P.ink} dash={heroDash}/>
          <text x={CX} y={CY+140} textAnchor="middle" fontSize={44} fontWeight={700} fill={P.ink} style={mono} opacity={seg(T,.9,.4)*(1-seg(T,4.0,.4))}>the task</text>
          <g transform={`translate(${CX} ${CY-345}) scale(${badge*(1+.08*Math.sin(T*9))})`} opacity={badge}>
            <circle r={52} fill={P.coral} stroke={P.ink} strokeWidth={6}/><text y={22} textAnchor="middle" fontSize={68} fontWeight={900} fill={P.white}>!</text>
          </g>
          <path d="M-55 10L-15 50L60 -40" transform={`translate(${CX} ${CY+130})`} fill="none" stroke={P.green} strokeWidth={22} strokeLinecap="round" strokeLinejoin="round" {...check}/>
        </g>
        {/* source card */}
        <g transform={`translate(0 ${(1-card)*2300}) rotate(${-4*(1-card)} 540 790)`}>
          <rect x={90} y={358} width={900} height={900} rx={32} fill="#c9bdf0"/>
          <rect x={90} y={340} width={900} height={900} rx={32} fill={P.white}/>
          <text x={140} y={405} fontSize={20} fill={P.dim} style={mono}>what the research says</text>
          <path d="M140 430H940" stroke={P.ink} strokeWidth={3}/>
          <text x={136} y={595} fontSize={150} fontWeight={900} fill={P.ink} letterSpacing={-2}>DODGING</text>
          <text x={136} y={745} fontSize={150} fontWeight={900} fill={P.coral} letterSpacing={-2}>A FEELING</text>
          <text x={140} y={825} fontSize={38} fontWeight={700} fill={P.ink}>the dread is often worse than the task,</text>
          <text x={140} y={877} fontSize={38} fontWeight={700} fill={P.ink}>and starting often quiets the alarm.</text>
          <g transform="translate(140 940)" opacity={chips}>
            <rect width={380*chips} height={62} rx={31} fill={P.mintG}/><text x={30} y={40} fontSize={22} fontWeight={800} fill={P.ink} style={{...mono,letterSpacing:2}} opacity={chips>.6?1:0}>tiny first step</text>
            <rect x={400} width={400*chips} height={62} rx={31} fill="none" stroke={P.ink} strokeWidth={3}/><text x={426} y={40} fontSize={22} fontWeight={800} fill={P.ink} style={{...mono,letterSpacing:2}} opacity={chips>.6?1:0}>forgive yourself</text>
          </g>
          <text x={140} y={1075} fontSize={18} fill={P.dim} style={{...mono,letterSpacing:2}}>the brain-scan link is a correlation, not a diagnosis</text>
          <path d="M140 1110H940" stroke={P.ink} strokeWidth={2} opacity={.2}/>
          <text x={140} y={1200} fontSize={14} fill={P.dim} style={{...mono,letterSpacing:1}}>source: pychyl &amp; sirois · 2018 german imaging study · self-forgiveness study</text>
        </g>
        <g opacity={seg(T,9.9,.4)*(1-seg(T,dl.until,.3))}>
          {phase==='dread'&&<Dial x={dl.x} y={dl.y} label={dl.label} unit={dl.unit} value={dv} max={dl.max} decimals={dl.decimals} appear={ez(EZ.out,T,dl.at,.5)} color={u<.5?P.coral:P.green} fg={P.ink} track="rgba(42,36,51,.15)"/>}
        </g>
      </g>
    </svg>
    {script.texts.map((tx,i)=>{const v=(T>=tx.at-.05&&T<tx.until+.3)?1-seg(T,tx.until,.25):0;
      return v>0?<div key={i} style={{position:'absolute',inset:0,opacity:v}}><Glyphs text={tx.text} frame={frame} startS={tx.at} size={tx.size} color={TXT[tx.color]} y={tx.y} font={tx.font} ca={false} wave={(tx as {wave?:number}).wave??0}/></div>:null;})}
    {T>=8.3&&T<9.6?<div style={{...mono,position:'absolute',top:1690,width:W,textAlign:'center',fontSize:20,color:P.dim,letterSpacing:2,opacity:seg(T,8.4,.3)}}>pychyl &amp; sirois: a mood problem, not a time problem</div>:null}
    {phase==='alarm'||phase==='dread'?<div style={{...mono,position:'absolute',bottom:100,width:W,textAlign:'center',fontSize:18,color:P.dim,letterSpacing:3}}>bars and values are illustrative, not measurements</div>:null}
  </AbsoluteFill>;
  return <AbsoluteFill style={{background:BG[0],fontFamily:'DM Sans, Arial, sans-serif'}}>
    <style>{`@font-face{font-family:'DM Sans';src:url('${staticFile('DMSans.ttf')}')}`}</style>
    <CameraMotionBlur shutterAngle={140} samples={4}>{content}</CameraMotionBlur>
  </AbsoluteFill>;
};
