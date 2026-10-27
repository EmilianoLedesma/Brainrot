import React from 'react';
import {AbsoluteFill,interpolate,spring,staticFile,useCurrentFrame} from 'remotion';
import {evolvePath,interpolatePath} from '@remotion/paths';
import {noise2D} from '@remotion/noise';
import {CameraMotionBlur} from '@remotion/motion-blur';
import script from './script.json';
import {C,COL,Dial,EZ,FPS,Glyphs,Grain,H,Halftone,W,camAt,clip,ez,mono,pts,seg,toD,Tube} from './kit';

// Silent coffee-science explainer driven entirely by script.json (texts, camera, dials, phases, sfx cues).
// Upgrades in use: SVG shape rig (draw-on, morph), tube strokes, halftone light, shared elements across phases,
// camera null + bezier easing, spring text animator with chromatic aberration, gauges, motion blur, grain, noise steam.
export const COFFEE_FRAMES=Math.round(script.duration*FPS);
const CX=540,CY=960,N=240;
const rot=(x:number,y:number,a:number):[number,number]=>[CX+x*Math.cos(a)-y*Math.sin(a),CY+x*Math.sin(a)+y*Math.cos(a)];
const BEAN=toD(pts(N,t=>{const a=t*Math.PI*2;return rot(185*Math.cos(a)*(1+.04*Math.sin(3*a)),285*Math.sin(a)*(1+.035*Math.sin(2*a+1)),.38);}));
const RING=toD(pts(N,t=>{const a=t*Math.PI*2;return [CX+230*Math.cos(a),CY+230*Math.sin(a)];}));
const CREASE=toD(pts(120,t=>{const s=t*2-1;return rot(Math.sin(s*Math.PI*1.15)*42*(1-s*s*.35),s*255,.38);}));

// particles for the grind phase (deterministic)
const rnd=(i:number,s:number)=>{const v=Math.sin(i*127.1+s*311.7)*43758.5453;return v-Math.floor(v);};
const K=220;
const PARTS=Array.from({length:K},(_,k)=>{const rr=Math.sqrt(rnd(k,1))*200,th=rnd(k,2)*Math.PI*2;return {x:CX+rr*Math.cos(th),y:CY+rr*Math.sin(th),s:.6+.8*rnd(k,3)};});

// extraction chart: 0..30 % on the y axis, brew time on x
const X0=170,X1=960,Y0=1260,PPP=17,yOf=(e:number)=>Y0-e*PPP,eOf=(x:number)=>30*(1-Math.exp(-3*x));
const CP=pts(160,t=>[X0+(X1-X0)*t,yOf(eOf(t))]),CURVE=toD(CP);
const CUM=CP.map((_,i)=>CP.slice(0,i+1).reduce((s,p,j,a)=>j?s+Math.hypot(p[0]-a[j-1][0],p[1]-a[j-1][1]):0,0));
const lf=(x:number)=>{const f=clip(x)*159,i=Math.min(158,Math.floor(f));return (CUM[i]+(CUM[i+1]-CUM[i])*(f-i))/CUM[159];};
const at=(x:number):[number,number]=>[X0+(X1-X0)*x,yOf(eOf(x))];

const K1=(t:number,a:number[],b:number[])=>interpolate(t,a,b,{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});

export const Coffee=()=>{
  const frame=useCurrentFrame(),T=frame/FPS;
  const {zoom,cy}=camAt(T,script.cam),roll=noise2D('r',T*.3,0)*.6;
  // hero rope: draw-on, then morph bean -> cup rim
  const drawIn=ez(EZ.inout,T,.2,1.4),morph=ez(EZ.inout,T,2.7,1.0);
  const d=interpolatePath(morph,BEAN,RING),dash=evolvePath(drawIn,d);
  const crease=evolvePath(ez(EZ.inout,T,1.4,1),CREASE);
  // shared hero element travels: centre -> chart corner -> card cup
  const kT=[0,8.3,9.2,12.8,13.7,16];
  const gx=K1(T,kT,[CX,CX,230,230,CX,CX]),gy=K1(T,kT,[CY,CY,590,590,1540,1540]),gs=K1(T,kT,[1,1,.3,.3,.45,.45]);
  const grind=ez(EZ.inout,T,4.2,3.8),sz=22-16*grind,count=Math.floor(25+195*grind);
  // extraction cursor
  const hx=interpolate(T,[8.9,10,11.2,11.6,12.5],[0,.305,.4377,.45,1],{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const e=eOf(hx),zone=e<18?C.blue:e<22?C.lime:C.red;
  const chartA=ez(EZ.out,T,8.5,.6)*(1-ez(EZ.inout,T,12.7,.7)),chartX=-W*ez(EZ.inout,T,12.7,.7);
  const axes=evolvePath(ez(EZ.inout,T,8.5,.8),`M${X0} ${Y0}L${X0} 720M${X0} ${Y0}L${X1} ${Y0}`);
  const curve=evolvePath(lf(hx),CURVE);
  // card
  const card=spring({frame:frame-12.9*FPS,fps:FPS,config:{damping:14,stiffness:90}}),bar=ez(EZ.out,T,13.7,.9),steam=ez(EZ.out,T,13.8,.8);
  const phase=Object.entries(script.phases).find(([,[a,b]])=>T>=a&&T<b)?.[0]??'card';
  const dialVal=(dl:typeof script.dials[number])=>dl.id==='extract'?e:interpolate(T,[dl.at+.2,dl.until],[dl.from,dl.to],{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const cur=(x:number)=>at(x),head=cur(hx);

  const content=<AbsoluteFill style={{background:C.ink}}>
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{position:'absolute',inset:0}}>
      <defs>
        <radialGradient id="beanfill" cx=".35" cy=".3" r=".9"><stop offset="0" stopColor="#5a2c1a"/><stop offset="1" stopColor="#150909"/></radialGradient>
        <clipPath id="cup"><circle cx={CX} cy={CY} r={214}/></clipPath>
      </defs>
      <g transform={`translate(540 960) rotate(${roll}) scale(${zoom}) translate(-540 ${-cy})`}>
        {/* chart (slides out left when the card arrives) */}
        <g opacity={chartA} transform={`translate(${chartX} 0)`}>
          <rect x={X0} y={yOf(18)} width={X1-X0} height={Y0-yOf(18)} fill={C.blue} opacity={.14*seg(T,8.9,.5)}/>
          <rect x={X0} y={yOf(22)} width={X1-X0} height={yOf(18)-yOf(22)} fill={C.lime} opacity={.2*seg(T,9.1,.5)}/>
          <rect x={X0} y={yOf(30)} width={X1-X0} height={yOf(22)-yOf(30)} fill={C.red} opacity={.14*seg(T,9.3,.5)}/>
          <path d={`M${X0} ${yOf(18)}H${X1}M${X0} ${yOf(22)}H${X1}`} stroke={C.cream} strokeWidth={2} strokeDasharray="10 10" opacity={.35*seg(T,9.3,.4)}/>
          <path d={`M${X0} ${Y0}L${X0} 720M${X0} ${Y0}L${X1} ${Y0}`} stroke={C.cream} strokeWidth={4} fill="none" strokeLinecap="round" {...axes}/>
          <g style={{...mono,letterSpacing:3}} fontSize={22} fontWeight={700} textAnchor="end">
            <text x={X1-14} y={Y0-18} fill={C.blue} opacity={seg(T,9,.4)}>sour · under</text>
            <text x={X1-14} y={yOf(20)+8} fill={C.lime} opacity={seg(T,9.2,.4)}>sweet</text>
            <text x={X1-14} y={yOf(30)+34} fill={C.red} opacity={seg(T,9.4,.4)}>bitter · over</text>
          </g>
          <text x={X0+10} y={706} fontSize={18} fill={C.dim} style={mono}>extraction ↑</text>
          <text x={X1} y={Y0+40} textAnchor="end" fontSize={18} fill={C.dim} style={mono}>brew time →</text>
          {hx>0&&<><Tube d={CURVE} w={14} dash={curve}/>
            {[5,4,3,2,1].map(k=>{const p=cur(Math.max(0,hx-k*.018));return <circle key={k} cx={p[0]} cy={p[1]} r={16-k*2} fill={zone} opacity={.5-k*.08}/>;})}
            <circle cx={head[0]} cy={head[1]} r={20} fill={zone} stroke="#150507" strokeWidth={5}/>
            {e>=18&&e<22&&<circle cx={head[0]} cy={head[1]} r={20+(T*60%1)*30} fill="none" stroke={C.lime} strokeWidth={4} opacity={1-(T*60%1)}/>}</>}
        </g>
        {/* hero: halftone-lit bean that morphs into the cup, grinds, shrinks to the chart, returns on the card */}
        <g transform={`translate(${gx} ${gy}) scale(${gs}) translate(${-CX} ${-CY})`}>
          <Halftone cx={CX} cy={CY-20} rx={330} ry={430} appear={ez(EZ.out,T,.1,1)*(T<8.3?1:.55)} t={0}/>
          <path d={d} fill="url(#beanfill)" fillOpacity={seg(T,1.0,.7)}/>
          <Tube d={d} w={18} dash={dash}/>
          {T>1.4&&T<3.6&&<g opacity={1-seg(T,2.7,.6)}><Tube d={CREASE} w={9} color="#e8b98a" light="#fff3e0" dash={crease}/></g>}
          {morph>0&&morph<1&&[1,2,3].map(k=><path key={k} d={interpolatePath(clip(morph-k*.07),BEAN,RING)} fill="none" stroke={C.red} strokeWidth={10} opacity={.22/k} strokeLinecap="round"/>)}
          <g clipPath="url(#cup)">{PARTS.map((p,k)=>{
            if(k>=count)return null;
            const sp=spring({frame:frame-(4.1+k/K*3.4)*FPS,fps:FPS,config:{damping:12,stiffness:110,mass:.8}});if(sp<.01)return null;
            const r=sz*p.s*.5;return <g key={k} transform={`translate(${p.x} ${p.y-(1-sp)*700})`}><circle r={r+2} fill="#150507"/><circle r={r} fill={C.brown}/><circle cx={-r*.3} cy={-r*.3} r={r*.35} fill={C.tan}/></g>;})}</g>
        </g>
        {/* steam over the cup on the card */}
        {steam>0&&[-46,0,46].map((bx,i)=>{const dd=toD(pts(40,t=>[540+bx+noise2D('s'+i,t*2.4,T*.7)*26*t,1440-t*150]));
          return <g key={i} opacity={.9}><Tube d={dd} w={9} color={C.cream} light="#fff" dash={evolvePath(steam,dd)}/></g>;})}
        {/* cream source card */}
        <g style={{filter:'drop-shadow(0 30px 60px rgba(229,38,45,.28))'}} transform={`translate(0 ${(1-card)*2300}) rotate(${-4*(1-card)} 540 790)`}>
          <rect x={90} y={340} width={900} height={900} rx={28} fill={C.cream}/>
          <text x={140} y={405} fontSize={20} fill="#6b6b73" style={mono}>journal of coffee brewing</text>
          <path d="M140 430H940" stroke={C.ink} strokeWidth={3}/>
          <text x={136} y={640} fontSize={210} fontWeight={900} fill={C.ink} letterSpacing={-10}>18–22%</text>
          <text x={140} y={725} fontSize={46} fontWeight={700} fill={C.ink}>of the coffee dissolves</text>
          <text x={140} y={780} fontSize={46} fontWeight={700} fill={C.ink}>into the cup</text>
          <g transform="translate(140 880)">
            <rect width={480*bar} height={44} fill={C.blue}/><rect x={480} width={107*bar} height={44} fill="#9ac400"/><rect x={587} width={213*bar} height={44} fill={C.red}/>
            <g fontSize={18} fill={C.ink} style={{...mono,letterSpacing:2}} opacity={bar}><text y={78}>sour</text><text x={470} y={78}>sweet</text><text x={800} y={78} textAnchor="end">bitter</text></g>
          </g>
          <text x={140} y={1050} fontSize={26} fill={C.ink} fontWeight={700} style={mono}>brew water 90–96 °C</text>
          <path d="M140 1085H940" stroke={C.ink} strokeWidth={2} opacity={.25}/>
          <text x={140} y={1200} fontSize={15} fill="#6b6b73" style={{...mono,letterSpacing:2}}>source: specialty coffee association · gold cup standard</text>
        </g>
      </g>
      {/* dials stay in screen space */}
      {script.dials.map(dl=><Dial key={dl.id} x={dl.x} y={dl.y} label={dl.label} unit={dl.unit} value={dialVal(dl)} max={dl.max} decimals={dl.decimals} appear={ez(EZ.out,T,dl.at,.5)*(1-seg(T,dl.until,.3))}/>)}
    </svg>
    {script.texts.map((tx,i)=>{const v=(T>=tx.at-.05&&T<tx.until+.3)?1-seg(T,tx.until,.25):0;
      return v>0?<div key={i} style={{position:'absolute',inset:0,opacity:v}}><Glyphs text={tx.text} frame={frame} startS={tx.at} size={tx.size} color={COL[tx.color]} y={tx.y} font={tx.font} wave={(tx as {wave?:number}).wave??0}/></div>:null;})}
    <div style={{...mono,position:'absolute',top:62,left:100,fontSize:22,color:C.cream,fontWeight:700}}>COFFEE · SCIENCE<div style={{color:C.dim,marginTop:6,fontSize:18}}>{phase}</div></div>
    <div style={{...mono,position:'absolute',top:62,right:100,fontSize:22,color:C.cream,fontWeight:700}}>00:00:{String(Math.floor(T)).padStart(2,'0')}:{String(Math.floor(frame)%FPS).padStart(2,'0')}</div>
    {phase==='extract'||phase==='grind'?<div style={{...mono,position:'absolute',bottom:100,width:W,textAlign:'center',fontSize:18,color:C.dim,letterSpacing:3}}>illustrative values, not a measurement</div>:null}
  </AbsoluteFill>;
  return <AbsoluteFill style={{background:C.ink,fontFamily:'DM Sans, Arial, sans-serif'}}>
    <style>{`@font-face{font-family:'DM Sans';src:url('${staticFile('DMSans.ttf')}')}`}</style>
    <CameraMotionBlur shutterAngle={200} samples={5}>{content}</CameraMotionBlur>
    <Grain frame={frame}/>
  </AbsoluteFill>;
};
