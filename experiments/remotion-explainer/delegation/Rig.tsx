import React from 'react';
import {AbsoluteFill,Easing,interpolate,spring,staticFile,useCurrentFrame} from 'remotion';
import {evolvePath,interpolatePath} from '@remotion/paths';

// After-Effects-style vector rig in SVG, one continuous timeline (no scene cuts):
//  trim-path draw-on (evolvePath), shape morph (interpolatePath), tube-lit strokes, halftone lighting,
//  echo trails, shared elements that travel between beats, a camera null, bezier-graph easing, per-glyph text animator.
const FPS=30,W=1080,H=1920;
export const RIG_FRAMES=Math.round(12.6*FPS);
const C={ink:'#0b0b0e',cream:'#f3f1ec',red:'#e5262d',hi:'#ff8f7d',deep:'#7a0f14',lime:'#d7ff3a',dim:'#8a8a92'};
const clip=(v:number)=>Math.max(0,Math.min(1,v));
const seg=(t:number,a:number,d:number)=>clip((t-a)/d);
// graph-editor style curves
const EZ={out:Easing.bezier(.16,1,.3,1),inout:Easing.bezier(.65,0,.35,1)};
const ez=(f:(x:number)=>number,t:number,a:number,d:number)=>f(seg(t,a,d));
const mono:React.CSSProperties={fontFamily:'Consolas, "Courier New", monospace',letterSpacing:4,textTransform:'uppercase'};

const N=260,CX=540,CY=960;
const pts=(f:(t:number)=>[number,number])=>Array.from({length:N},(_,i)=>f(i/(N-1)));
const toD=(p:[number,number][])=>p.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join('');
const SCRIBBLE=toD(pts(t=>{const a=t*Math.PI*2*3.3,r=250*(.55+.45*Math.sin(t*Math.PI));return [CX+r*Math.cos(a)+60*Math.sin(a*2.7),CY-40+r*Math.sin(a*1.3)*1.2+60*Math.cos(a*3.1)];}));
const RING=toD(pts(t=>{const a=t*Math.PI*2-Math.PI/2;return [CX+210*Math.cos(a),CY+210*Math.sin(a)];}));

function Tube({d,w=18,dash}:{d:string,w?:number,dash?:{strokeDasharray:string,strokeDashoffset:number}}){
  const p={fill:'none',strokeLinecap:'round' as const,strokeLinejoin:'round' as const,...dash};
  return <g><path d={d} stroke="#1c0609" strokeWidth={w+12} {...p}/><path d={d} stroke={C.red} strokeWidth={w} {...p}/><path d={d} stroke={C.hi} strokeWidth={w*.22} transform="translate(-2,-4)" opacity={.85} {...p}/></g>;
}

// halftone disc: dot radius falls off from a light source that sits up-left of centre
function Halftone({cx,cy,rx,ry,appear,t}:{cx:number,cy:number,rx:number,ry:number,appear:number,t:number}){
  const s=16,out:React.ReactNode[]=[];
  for(let r=-Math.ceil(ry/s*1.15);r<=Math.ceil(ry/s*1.15);r++)for(let c=-Math.ceil(rx/s*1.15);c<=Math.ceil(rx/s*1.15);c++){
    const x=c*s+(r%2?s/2:0),y=r*s*.88,d=Math.hypot(x/rx,y/ry);if(d>1)continue;
    const l=Math.hypot((x+rx*.25)/rx,(y+ry*.3)/ry),k=Math.max(0,1-Math.pow(l,1.7))*(1-d*.2)*appear*(1+Math.sin(t*1.4+x*.01)*.05);
    if(k>.04)out.push(<circle key={r+'_'+c} cx={cx+x} cy={cy+y} r={s*.5*k} fill={C.cream}/>);}
  return <g>{out}</g>;
}

function Glyphs({text,t,start,size,color,y,gap=.04,wave=0}:{text:string,t:number,start:number,size:number,color:string,y:number,gap?:number,wave?:number}){
  const f=Math.round(t*FPS);
  return <div style={{position:'absolute',top:y,width:W,display:'flex',justifyContent:'center',overflow:'hidden',paddingBottom:size*.15}}>
    {text.split('').map((ch,i)=>{const sp=spring({frame:f-Math.round((start+i*gap)*FPS),fps:FPS,config:{damping:13,stiffness:170,mass:.7}});
      const w=Math.sin(t*5+i*.7)*wave*sp;
      return <span key={i} style={{display:'inline-block',whiteSpace:'pre',fontSize:size,fontWeight:900,letterSpacing:-size*.04,lineHeight:1,color,transform:`translateY(${(1-sp)*size*1.2+w}px) rotate(${(1-sp)*-7}deg)`,opacity:sp>.01?1:0}}>{ch}</span>;})}
  </div>;
}

const TASKS=['Email','Research','Reports','Social','Support'];
const ang=(i:number)=>-Math.PI/2+i*Math.PI*2/5;

export const Rig=()=>{
  const frame=useCurrentFrame(),T=frame/FPS;
  // beats
  const drawIn=ez(EZ.inout,T,.25,1.9),morph=ez(EZ.inout,T,3.1,1.1),netIn=seg(T,4.5,.1),rev=T>8.6;
  const hubOn=ez(EZ.out,T,8.7,.8);
  const d=interpolatePath(morph,SCRIBBLE,RING),ev=evolvePath(drawIn,d);
  // camera null
  const K=(a:number[],b:number[])=>interpolate(T,a,b,{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const zoom=K([0,3.2,4.9,8.4,12.6],[1,1.2,1,1.06,.92]),cy=K([0,3.2,4.9,8.4,12.6],[860,880,1000,900,930]),roll=Math.sin(T*.6)*.6;
  const lightA=ez(EZ.out,T,.1,1)*(1-ez(EZ.inout,T,4.4,.8)*.5);
  const nodes=TASKS.map((k,i)=>{
    const s=spring({frame:frame-Math.round((8.7+i*.07)*FPS),fps:FPS,config:{damping:11,stiffness:120,mass:.9}});
    const a=ang(i),pop=spring({frame:frame-Math.round((4.9+i*.18)*FPS),fps:FPS,config:{damping:9,stiffness:150}});
    const pill={x:210,y:760+i*150},nd={x:870-(i%2)*40,y:760+i*150};
    const ndE={x:CX+210*Math.cos(a),y:CY+210*Math.sin(a)},plE={x:CX+365*Math.cos(a),y:CY+365*Math.sin(a)};
    return {k,i,pop,wire:ez(EZ.out,T,4.7+i*.18,.7),
      pill:{x:pill.x+(plE.x-pill.x)*s,y:pill.y+(plE.y-pill.y)*s},nd:{x:nd.x+(ndE.x-nd.x)*s,y:nd.y+(ndE.y-nd.y)*s}};});
  return <AbsoluteFill style={{background:C.ink,fontFamily:'DM Sans, Arial, sans-serif',overflow:'hidden'}}>
    <style>{`@font-face{font-family:'DM Sans';src:url('${staticFile('DMSans.ttf')}')}`}</style>
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{position:'absolute',inset:0}}>
      <defs><radialGradient id="sph" cx=".35" cy=".3" r=".8"><stop offset="0" stopColor={C.hi}/><stop offset=".45" stopColor={C.red}/><stop offset="1" stopColor={C.deep}/></radialGradient></defs>
      <g transform={`translate(540 960) rotate(${roll}) scale(${zoom}) translate(-540 ${-cy})`}>
        <Halftone cx={CX} cy={CY-20} rx={330} ry={430} appear={lightA} t={T}/>
        {/* hero rope: draws on, morphs scribble -> ring, becomes the hub */}
        <g opacity={T<4.9?1:.35+.65*hubOn} transform={`translate(${CX} ${CY}) scale(${1+hubOn*.06}) translate(${-CX} ${-CY})`}>
          <Tube d={d} w={18} dash={ev}/>
        </g>
        {/* echo trail while the rope untangles */}
        {morph>0&&morph<1&&[1,2,3].map(k=><path key={k} d={interpolatePath(clip(morph-k*.07),SCRIBBLE,RING)} fill="none" stroke={C.red} strokeWidth={10} opacity={.22/k} strokeLinecap="round"/>)}
        {/* agent network: shared elements that later fly onto the hub */}
        {netIn>0&&nodes.map(n=>{
          const wx=n.pill.x+(n.nd.x-n.pill.x)*n.wire,wy=n.pill.y+(n.nd.y-n.pill.y)*n.wire,dir=rev?-1:1;
          const p=(T*.7+n.i*.2)%1,pos=dir>0?p:1-p;
          return <g key={n.k}>
            <line x1={n.pill.x} y1={n.pill.y} x2={wx} y2={wy} stroke={C.red} strokeWidth={3} strokeDasharray="12 10"/>
            {n.wire>.95&&[0,1,2,3].map(e=>{const q=clip(pos-e*.045*dir);return <circle key={e} cx={n.pill.x+(n.nd.x-n.pill.x)*q} cy={n.pill.y+(n.nd.y-n.pill.y)*q} r={9-e*1.6} fill={C.lime} opacity={1-e*.25}/>;})}
            <g transform={`translate(${n.nd.x} ${n.nd.y}) scale(${n.pop})`}><circle r={40} fill="url(#sph)" stroke="#1c0609" strokeWidth={5}/><circle cx={-12} cy={-14} r={7} fill="#fff" opacity={.55}/></g>
            <g transform={`translate(${n.pill.x} ${n.pill.y}) scale(${Math.min(1,n.pop*1.1)})`}>
              <rect x={-95} y={-34} width={190} height={68} rx={34} fill={C.cream} stroke="#1c0609" strokeWidth={5}/>
              <text textAnchor="middle" y={13} fontSize={38} fontWeight={800} fill={C.ink}>{n.k}</text></g>
            <text x={n.nd.x} y={n.nd.y+72} textAnchor="middle" fontSize={20} fill={C.lime} opacity={n.pop*(1-seg(T,8.6,.2))} style={{...mono,letterSpacing:2}}>agent {n.i+1}</text>
          </g>;})}
        {hubOn>0&&<g opacity={hubOn} transform={`translate(0 ${(1-hubOn)*30})`} textAnchor="middle" fontWeight={900} fill={C.cream}><text x={CX} y={CY-8} fontSize={58}>ONE</text><text x={CX} y={CY+56} fontSize={58}>PLAYBOOK</text></g>}
      </g>
    </svg>
    {/* screen-space overlay: text animator + HUD */}
    <div style={{position:'absolute',inset:0,opacity:1-seg(T,3.9,.3)}}><Glyphs text="TO BE FAIR" t={T} start={.2} size={46} color={C.cream} y={330} wave={0}/></div>
    <div style={{position:'absolute',inset:0,opacity:1-seg(T,4.0,.4),pointerEvents:'none'}}><Glyphs text="IT'S COMPLEX" t={T} start={2.0} size={150} color={C.red} y={1560} gap={.035} wave={10}/></div>
    <div style={{position:'absolute',inset:0,opacity:seg(T,4.4,.2)*(1-seg(T,8.5,.2))}}><Glyphs text="BUILD AN AGENT PER JOB." t={T} start={4.6} size={64} color={C.cream} y={330} gap={.02}/></div>
    <Glyphs text="REVERSE" t={T} start={8.7} size={190} color={C.cream} y={1560} gap={.05} wave={14}/>
    <div style={{...mono,position:'absolute',top:62,left:100,fontSize:22,color:C.cream,fontWeight:700}}>AI DELEGATION<div style={{color:C.dim,marginTop:6,fontSize:18}}>{T<4.4?'WHO AGREES':T<8.6?'THE ADVICE':'THE REVERSE'}</div></div>
    <div style={{...mono,position:'absolute',top:62,right:100,fontSize:22,color:C.cream,fontWeight:700}}>00:00:{String(Math.floor(T)).padStart(2,'0')}:{String(frame%FPS).padStart(2,'0')}</div>
  </AbsoluteFill>;
};
