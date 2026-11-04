import React from 'react';
import {AbsoluteFill,spring,useCurrentFrame} from 'remotion';
import {evolvePath} from '@remotion/paths';
import {CameraMotionBlur} from '@remotion/motion-blur';
import script from './script.json';
import {EZ,FPS,H,W,camAt,clip,ez,seg,wiggle} from '../remotion-explainer/coffee-sci/kit';

// Silent 2D explainer built from docs/motion-graphics-recipe.md: one hero (the elevator) on screen the whole shot,
// script in script.json, one shared camera null, no corner brackets, timecode, vignette or film grain.
export const ELEVATOR_FRAMES=script.durationFrames;
const E=script.events;
const K={bg:'#E7EDF3',grid:'#D6E0E9',red:'#E0504B',floor:'#C7D2DC',cable:'#4A5568',cableHi:'#6B778C',gold:'#D4A73B',goldHi:'#F0CB6A',
  blue:'#2F6FED',orange:'#F2994A',cream:'#FBF3DF',bar:'#2D3748',card:'#1B2430',key:'#2F3B4C',keyLine:'#5A6B80',pants:'#334155',shoe:'#1F2937'};
const FONT='Inter, "Segoe UI", Arial, sans-serif';

const X0=260,X1=820,TOP=900,BOT=1280,FLOOR=1268; // cabin box and interior floor, world coordinates
const CABLE_X=(i:number)=>540+(i-3)*18,GOLD=3,BROKEN=1,CUT_Y=645,HOOK_LEN=TOP-CUT_Y;
const SWAY_P=[97,83,113,127,71,101,89];

const PEOPLE=[
  {shirt:'#1C9099',skin:'#F4C9A5',hair:'short',hairC:'#2B2230'},
  {shirt:'#F2A93B',skin:'#C98A5B',hair:'curly',hairC:'#2A1F1A'},
  {shirt:'#8C6FE0',skin:'#F6D9BB',hair:'bun',hairC:'#E8C468'},
  {shirt:'#3FAE6B',skin:'#7A4B33',hair:'afro',hairC:'#1E1612'},
];

// Deterministic blink: no randomness, different interval and phase per character, plus a shared double blink on reaction.
export const blinkAt=(i:number,frame:number)=>{
  const f=Math.floor(frame),period=[70,82,94,100][i],phase=[10,31,47,22][i],len=3+(i%2);
  if(f>=E.reactStart+3&&f<E.reactStart+5)return true;
  if(f>=E.reactStart+8&&f<E.reactStart+10)return true;
  return ((f+phase)%period)<len;
};
const reactAt=(f:number)=>f<E.reactStart?0:f<E.reactStart+8?EZ.inout(seg(f,E.reactStart,8)):f<E.reactEnd?1:1-EZ.inout(seg(f,E.reactEnd,12));
const joltAt=(f:number)=>{if(f<E.cut||f>=E.joltEnd)return 0;const k=(f-E.cut)/(E.joltEnd-E.cut);return 4*Math.sin(k*Math.PI*3)*(1-k);};

function Person({i,f,cx}:{i:number,f:number,cx:number}){
  const p=PEOPLE[i],r=reactAt(f),breathe=1+.015*Math.sin(2*Math.PI*(f+i*12)/50);
  const blink=blinkAt(i,f)?.12:1,eyeR=3*(1+.45*r);
  const mouth=Math.max(.6,Math.min(1.1,.85+.28*Math.sin(f*.37+i*2.1)*Math.sin(f*.11+i)));
  const hip=FLOOR-78,arm=(s:number)=>-s*(8+6*Math.sin(2*Math.PI*(f+i*20)/90+(s>0?0:1.3))+50*r);
  return <g>
    <line x1={cx-13} y1={hip} x2={cx-13} y2={FLOOR-16} stroke={K.pants} strokeWidth={13} strokeLinecap="round"/>
    <line x1={cx+13} y1={hip} x2={cx+13} y2={FLOOR-16} stroke={K.pants} strokeWidth={13} strokeLinecap="round"/>
    <ellipse cx={cx-13} cy={FLOOR-8} rx={15} ry={7} fill={K.shoe}/><ellipse cx={cx+13} cy={FLOOR-8} rx={15} ry={7} fill={K.shoe}/>
    <g transform={`translate(${cx} ${hip}) scale(1 ${breathe}) translate(${-cx} ${-hip})`}>
      {p.hair==='afro'&&<circle cx={cx} cy={FLOOR-216} r={40} fill={p.hairC}/>}
      {p.hair==='curly'&&[-22,-11,0,11,22].map((dx,k)=><circle key={k} cx={cx+dx} cy={FLOOR-228+Math.abs(dx)*.5} r={13} fill={p.hairC}/>)}
      {p.hair==='bun'&&<circle cx={cx} cy={FLOOR-246} r={13} fill={p.hairC}/>}
      {[-1,1].map(s=><g key={s} transform={`translate(${cx+s*38} ${FLOOR-170}) rotate(${arm(s)})`}>
        <line x1={0} y1={0} x2={0} y2={60} stroke={p.shirt} strokeWidth={12} strokeLinecap="round"/><circle cy={66} r={6.5} fill={p.skin}/></g>)}
      <path d={`M${cx-36} ${FLOOR-178}L${cx+36} ${FLOOR-178}L${cx+44} ${hip}L${cx-44} ${hip}Z`} fill={p.shirt} stroke={p.shirt} strokeWidth={6} strokeLinejoin="round"/>
      <rect x={cx-5} y={FLOOR-190} width={10} height={14} fill={p.skin}/>
      <circle cx={cx} cy={FLOOR-208} r={28} fill={p.skin}/>
      {(p.hair==='short'||p.hair==='bun')&&<path d={`M${cx-29} ${FLOOR-208}A29 29 0 0 1 ${cx+29} ${FLOOR-208}Q${cx} ${FLOOR-232} ${cx-29} ${FLOOR-208}Z`} fill={p.hairC}/>}
      {p.hair==='curly'&&<path d={`M${cx-28} ${FLOOR-212}Q${cx} ${FLOOR-236} ${cx+28} ${FLOOR-212}Q${cx} ${FLOOR-224} ${cx-28} ${FLOOR-212}Z`} fill={p.hairC}/>}
      {p.hair==='afro'&&<path d={`M${cx-27} ${FLOOR-214}Q${cx} ${FLOOR-236} ${cx+27} ${FLOOR-214}Q${cx} ${FLOOR-222} ${cx-27} ${FLOOR-214}Z`} fill={p.hairC}/>}
      {[-10,10].map(dx=><g key={dx} transform={`translate(${cx+dx} ${FLOOR-208}) scale(1 ${blink})`}><circle r={eyeR} fill="#0b0b0e"/></g>)}
      <g transform={`translate(${cx} ${FLOOR-195}) scale(1 ${mouth})`}><path d="M-9 0Q0 8 9 0" stroke="#3A2A28" strokeWidth={2.6} fill="none" strokeLinecap="round"/></g>
    </g>
  </g>;
}

const Braid=({id,a,b}:{id:string,a:string,b:string})=>
  <pattern id={id} width={14} height={14} patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><rect width={14} height={14} fill={a}/><rect width={14} height={4.5} fill={b}/></pattern>;

// Frayed strands: short curves drawn on with evolvePath, more of them as the break approaches.
function Strands({f,x}:{f:number,x:number}){
  const fade=1-clip((f-E.cut)/8);
  return <g opacity={fade}>{Array.from({length:8}).map((_,j)=>{
    const dir=j%2?-1:1,y0=CUT_Y+38-j*11,d=`M${x} ${y0}q${dir*24} -10 ${dir*(40+(j*7)%18)} ${-8-(j%3)*8}q${dir*10} -9 ${dir*4} ${-22}`;
    const ev=evolvePath(seg(f,E.frayStart+j*2.4,7),d);
    return seg(f,E.frayStart+j*2.4,7)>0&&<path key={j} d={d} stroke={K.cableHi} strokeWidth={3.6} fill="none" strokeLinecap="round" {...ev}/>;})}</g>;
}

function Caption({c,f}:{c:typeof script.captions[number],f:number}){
  if(f<c.from||f>=c.to)return null;
  const inP=spring({frame:f-c.from,fps:FPS,config:{damping:14,stiffness:120,mass:.8}}),out=ez(EZ.inout,f,c.to-10,10);
  let n=0;
  return <div style={{position:'absolute',top:1500,left:0,width:W,display:'flex',justifyContent:'center',fontFamily:FONT}}>
    <div style={{background:K.card,borderRadius:20,padding:'26px 44px',display:'inline-flex',alignItems:'center',color:'#fff',fontWeight:800,fontSize:56,lineHeight:1.1,
      opacity:(1-out)*clip(inP*2),transform:`translateY(${(1-inP)*160+out*120}px) scale(${.9+.1*inP})`}}>
      {c.parts.map((part,pi)=>{
        const glyphs=part.t.split('').map(ch=>{const sp=spring({frame:f-c.from-4-(n++)*.7,fps:FPS,config:{damping:13,stiffness:170,mass:.7}});
          return <span key={n} style={{display:'inline-block',whiteSpace:'pre',transform:`translateY(${(1-sp)*30}px)`,opacity:sp>.01?1:0}}>{ch}</span>;});
        return 'key' in part&&part.key
          ?<span key={pi} style={{background:K.key,border:`1.5px solid ${K.keyLine}`,borderRadius:12,padding:'0 14px',margin:'0 2px'}}>{glyphs}</span>
          :<span key={pi}>{glyphs}</span>;})}
    </div>
  </div>;
}

export function ElevatorCables(){
  const f=useCurrentFrame(),t=f/FPS;
  const cam=camAt(t,script.cam.map(c=>({at:c.f/FPS,zoom:c.zoom,cy:c.cy})));
  const roll=wiggle(3,t,.3,.5),dy=joltAt(f),cut=f>=E.cut;
  const sway=(i:number)=>(i===GOLD?.6:2)*Math.sin(2*Math.PI*f/SWAY_P[i]+i);
  const theta=190*Math.PI/180*spring({frame:f-E.cut,fps:FPS,config:{damping:7,stiffness:80,mass:1}});
  const bx=CABLE_X(BROKEN)+sway(BROKEN);
  const hook=(()=>{const n=26,ds=HOOK_LEN/n;let x=bx,y=TOP+6,d=`M${x} ${y}`;
    for(let k=0;k<n;k++){const a=-Math.PI/2-theta*Math.pow(k/n,1.2);x+=ds*Math.cos(a);y+=ds*Math.sin(a);d+=`L${x.toFixed(1)} ${y.toFixed(1)}`;}return d;})();
  const sparkT=f-E.cut,sparks=sparkT>=0&&sparkT<=5;
  const grid:string[]=[];for(let x=0;x<=W;x+=80)grid.push(`M${x} -400V2300`);for(let y=-400;y<=2300;y+=80)grid.push(`M0 ${y}H${W}`);
  const world=<>
    <defs><Braid id="braid" a={K.cable} b={K.cableHi}/><Braid id="braidGold" a={K.gold} b={K.goldHi}/></defs>
    <path d={grid.join('')} stroke={K.grid} strokeWidth={1.5} fill="none"/>
    {script.floors.map((n,k)=><text key={n} x={70} y={420+k*320} fontSize={120} fontWeight={900} fontFamily={FONT} fill={K.floor} opacity={.5}>{n}</text>)}
    {Array.from({length:7}).map((_,i)=>{
      const x=CABLE_X(i),dx=sway(i),stroke={stroke:i===GOLD?'url(#braidGold)':'url(#braid)',strokeWidth:14,fill:'none',strokeLinecap:'round' as const};
      if(i===BROKEN&&cut)return <g key={i}><path d={`M${x+dx} -900V${CUT_Y}`} {...stroke}/><path d={hook} {...stroke}/></g>;
      return <path key={i} transform={`translate(${dx} 0)`} d={`M${x} -900V${TOP+8}`} {...stroke}/>;})}
    {f>=E.frayStart&&<Strands f={f} x={bx}/>}
    {sparks&&[0,1,2].map(k=>{const a=-.4-k*1.1,d=8+sparkT*5+k*3;
      return <circle key={k} cx={bx+Math.cos(a)*d} cy={CUT_Y+Math.sin(a)*d} r={Math.max(0,8-sparkT*1.5)} fill={k===1?'#FFD27A':K.orange}/>;})}
    <g transform={`translate(0 ${dy})`}>
      <rect x={X0} y={TOP} width={X1-X0} height={BOT-TOP} rx={8} fill={K.cream} opacity={.92}/>
      <rect x={X0+3} y={TOP+3} width={6} height={BOT-TOP-6} fill={K.orange}/><rect x={X1-9} y={TOP+3} width={6} height={BOT-TOP-6} fill={K.orange}/>
      {PEOPLE.map((_,i)=><Person key={i} i={i} f={f} cx={360+i*120}/>)}
      <rect x={X0} y={TOP} width={X1-X0} height={BOT-TOP} rx={8} fill="none" stroke={K.blue} strokeWidth={6}/>
      <rect x={X0-20} y={BOT} width={X1-X0+40} height={26} rx={4} fill={K.bar}/>
      <polygon points={`${X0-20},${BOT+26} ${X0-20},${BOT+70} ${X0+28},${BOT+26}`} fill={K.orange}/>
      <polygon points={`${X1+20},${BOT+26} ${X1+20},${BOT+70} ${X1-28},${BOT+26}`} fill={K.orange}/>
    </g>
  </>;
  return <AbsoluteFill style={{background:K.bg,overflow:'hidden'}}>
    <CameraMotionBlur shutterAngle={140} samples={4}>
      <svg width={W} height={H} style={{position:'absolute',inset:0}}>
        <g transform={`translate(540 960) rotate(${roll}) scale(${cam.zoom}) translate(-540 ${-cam.cy})`}>{world}</g>
        <line x1={26} y1={0} x2={26} y2={H} stroke={K.red} strokeWidth={2} strokeDasharray="12 9"/>
        <line x1={46} y1={0} x2={46} y2={H} stroke={K.red} strokeWidth={2} strokeDasharray="12 9"/>
      </svg>
    </CameraMotionBlur>
    {script.captions.map((c,i)=><Caption key={i} c={c} f={f}/>)}
  </AbsoluteFill>;
}
