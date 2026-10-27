import React from 'react';
import {AbsoluteFill,interpolate,spring,staticFile,useCurrentFrame} from 'remotion';
import {evolvePath,interpolatePath} from '@remotion/paths';
import {noise2D} from '@remotion/noise';
import {CameraMotionBlur} from '@remotion/motion-blur';
import script from './script-light.json';
import {Dial,EZ,FPS,Glyphs,H,Halftone,W,camAt,clip,ez,mono,pts,seg,toD,Tube} from './kit';

// Light pastel version in the look of the first reference (HUD frame, bold kinetic type, UI cards, sweeping colour panels).
// Same rig as Coffee.tsx; no grain, vignette or chromatic aberration. Driven by script-light.json.
export const COFFEE_LIGHT_FRAMES=Math.round(script.duration*FPS);
const P={ink:'#2a2433',dim:'#7d7788',coral:'#ff6b5e',coralHi:'#ffc6bd',green:'#1f9d63',white:'#ffffff',
  cream:'#fdf7ee',peach:'#ffe3d2',mint:'#d9f2e6',lilac:'#e6defc',blue:'#8fb4ff',sweet:'#6fd39a',tan:'#d9a57a',brown:'#7a4b34',dot:'#f0b999'};
const TXT:Record<string,string>={ink:P.ink,coral:P.coral,green:P.green};
const BG=[P.cream,P.peach,P.mint,P.lilac];
const CX=540,CY=960,N=240;
const rot=(x:number,y:number,a:number):[number,number]=>[CX+x*Math.cos(a)-y*Math.sin(a),CY+x*Math.sin(a)+y*Math.cos(a)];
const BEAN=toD(pts(N,t=>{const a=t*Math.PI*2;return rot(185*Math.cos(a)*(1+.04*Math.sin(3*a)),285*Math.sin(a)*(1+.035*Math.sin(2*a+1)),.38);}));
const RING=toD(pts(N,t=>{const a=t*Math.PI*2;return [CX+230*Math.cos(a),CY+230*Math.sin(a)];}));
const CREASE=toD(pts(120,t=>{const s=t*2-1;return rot(Math.sin(s*Math.PI*1.15)*42*(1-s*s*.35),s*255,.38);}));

const rnd=(i:number,s:number)=>{const v=Math.sin(i*127.1+s*311.7)*43758.5453;return v-Math.floor(v);};
const K=220;
const PARTS=Array.from({length:K},(_,k)=>{const rr=Math.sqrt(rnd(k,1))*200,th=rnd(k,2)*Math.PI*2;return {x:CX+rr*Math.cos(th),y:CY+rr*Math.sin(th),s:.6+.8*rnd(k,3)};});
// illustrative surface-area index per grind style (qualitative)
const CARDS:[string,string,number][]=[['espresso','fine',.95],['moka pot','fine',.8],['filter','medium',.62],['drip','medium',.5],['french press','coarse',.3],['cold brew','coarse',.2]];

const X0=170,X1=960,Y0=1260,PPP=17,yOf=(e:number)=>Y0-e*PPP,eOf=(x:number)=>30*(1-Math.exp(-3*x));
const CP=pts(160,t=>[X0+(X1-X0)*t,yOf(eOf(t))]),CURVE=toD(CP);
const CUM=CP.map((_,i)=>CP.slice(0,i+1).reduce((s,p,j,a)=>j?s+Math.hypot(p[0]-a[j-1][0],p[1]-a[j-1][1]):0,0));
const lf=(x:number)=>{const f=clip(x)*159,i=Math.min(158,Math.floor(f));return (CUM[i]+(CUM[i+1]-CUM[i])*(f-i))/CUM[159];};
const at=(x:number):[number,number]=>[X0+(X1-X0)*x,yOf(eOf(x))];
const K1=(t:number,a:number[],b:number[])=>interpolate(t,a,b,{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});
const BOUNDS=Object.values(script.phases).map(p=>p[0]).slice(1);

export const CoffeeLight=()=>{
  const frame=useCurrentFrame(),T=frame/FPS;
  const {zoom,cy}=camAt(T,script.cam),roll=noise2D('r',T*.3,0)*.5;
  const drawIn=ez(EZ.inout,T,.2,1.4),morph=ez(EZ.inout,T,2.7,1.0);
  const d=interpolatePath(morph,BEAN,RING),dash=evolvePath(drawIn,d);
  const crease=evolvePath(ez(EZ.inout,T,1.4,1),CREASE);
  const kT=[0,3.6,4.5,8.2,9.1,12.6,13.5,16];
  const gx=K1(T,kT,[CX,CX,CX,CX,230,230,CX,CX]),gy=K1(T,kT,[CY,CY,620,620,590,590,1540,1540]),gs=K1(T,kT,[1,1,.62,.62,.3,.3,.45,.45]);
  const grind=ez(EZ.inout,T,4.2,3.8),sz=22-16*grind,count=Math.floor(25+195*grind);
  const hx=interpolate(T,[8.9,10,11.2,11.6,12.5],[0,.305,.4377,.45,1],{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const e=eOf(hx),zone=e<18?P.blue:e<22?P.sweet:P.coral;
  const chartA=ez(EZ.out,T,8.5,.6)*(1-ez(EZ.inout,T,12.7,.7)),chartX=-W*ez(EZ.inout,T,12.7,.7);
  const axes=evolvePath(ez(EZ.inout,T,8.5,.8),`M${X0} ${Y0}L${X0} 720M${X0} ${Y0}L${X1} ${Y0}`);
  const curve=evolvePath(lf(hx),CURVE);
  const card=spring({frame:frame-12.9*FPS,fps:FPS,config:{damping:14,stiffness:90}}),bar=ez(EZ.out,T,13.7,.9),steam=ez(EZ.out,T,13.8,.8);
  const phase=Object.entries(script.phases).find(([,[a,b]])=>T>=a&&T<b)?.[0]??'card';
  const dialVal=(dl:typeof script.dials[number])=>dl.id==='extract'?e:interpolate(T,[dl.at+.2,dl.until],[dl.from,dl.to],{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const head=at(hx),cur=at;
  const bgIdx=BOUNDS.filter(b=>T>=b).length;

  const content=<AbsoluteFill style={{background:BG[bgIdx]}}>
    {/* colour panels sweep across each phase boundary; content stays and carries over */}
    {BOUNDS.map((b,i)=>{const p=(T-(b-.25))/.5;if(p<0||p>1)return null;const w=W*1.5;
      return <div key={i} style={{position:'absolute',top:-50,height:H+100,width:w,left:W-ez(EZ.inout,p,0,1)*(W+w),background:BG[i+1],transform:'skewX(-12deg)'}}/>;})}
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{position:'absolute',inset:0}}>
      <defs>
        <radialGradient id="beanfill" cx=".35" cy=".3" r=".9"><stop offset="0" stopColor="#e7c3a0"/><stop offset="1" stopColor="#a8683f"/></radialGradient>
        <clipPath id="cup"><circle cx={CX} cy={CY} r={214}/></clipPath>
      </defs>
      <g transform={`translate(540 960) rotate(${roll}) scale(${zoom}) translate(-540 ${-cy})`}>
        <g opacity={chartA} transform={`translate(${chartX} 0)`}>
          <rect x={X0} y={yOf(18)} width={X1-X0} height={Y0-yOf(18)} fill={P.blue} opacity={.28*seg(T,8.9,.5)}/>
          <rect x={X0} y={yOf(22)} width={X1-X0} height={yOf(18)-yOf(22)} fill={P.sweet} opacity={.45*seg(T,9.1,.5)}/>
          <rect x={X0} y={yOf(30)} width={X1-X0} height={yOf(22)-yOf(30)} fill={P.coral} opacity={.22*seg(T,9.3,.5)}/>
          <path d={`M${X0} ${yOf(18)}H${X1}M${X0} ${yOf(22)}H${X1}`} stroke={P.ink} strokeWidth={2} strokeDasharray="10 10" opacity={.3*seg(T,9.3,.4)}/>
          <path d={`M${X0} ${Y0}L${X0} 720M${X0} ${Y0}L${X1} ${Y0}`} stroke={P.ink} strokeWidth={5} fill="none" strokeLinecap="round" {...axes}/>
          <g style={{...mono,letterSpacing:3}} fontSize={22} fontWeight={700} textAnchor="end">
            <text x={X1-14} y={Y0-18} fill="#4a6fd1" opacity={seg(T,9,.4)}>sour · under</text>
            <text x={X1-14} y={yOf(20)+8} fill={P.green} opacity={seg(T,9.2,.4)}>sweet</text>
            <text x={X1-14} y={yOf(30)+34} fill="#e0463a" opacity={seg(T,9.4,.4)}>bitter · over</text>
          </g>
          <text x={X0+10} y={706} fontSize={18} fill={P.dim} style={mono}>extraction ↑</text>
          <text x={X1} y={Y0+40} textAnchor="end" fontSize={18} fill={P.dim} style={mono}>brew time →</text>
          {hx>0&&<><Tube d={CURVE} w={14} color={P.coral} light={P.coralHi} outline={P.ink} dash={curve}/>
            {[5,4,3,2,1].map(k=>{const p=cur(Math.max(0,hx-k*.018));return <circle key={k} cx={p[0]} cy={p[1]} r={16-k*2} fill={zone} opacity={.5-k*.08}/>;})}
            <circle cx={head[0]} cy={head[1]} r={20} fill={zone} stroke={P.ink} strokeWidth={5}/>
            {e>=18&&e<22&&<circle cx={head[0]} cy={head[1]} r={20+(T*60%1)*30} fill="none" stroke={P.sweet} strokeWidth={4} opacity={1-(T*60%1)}/>}</>}
        </g>
        <g transform={`translate(${gx} ${gy}) scale(${gs}) translate(${-CX} ${-CY})`}>
          <Halftone cx={CX} cy={CY-20} rx={330} ry={430} appear={ez(EZ.out,T,.1,1)*(T<8.3?1:.7)} t={0} color={P.dot}/>
          <path d={d} fill="url(#beanfill)" fillOpacity={seg(T,1.0,.7)}/>
          <Tube d={d} w={18} color={P.coral} light={P.coralHi} outline={P.ink} dash={dash}/>
          {T>1.4&&T<3.6&&<g opacity={1-seg(T,2.7,.6)}><Tube d={CREASE} w={9} color="#fff1dc" light="#ffffff" outline={P.brown} dash={crease}/></g>}
          {morph>0&&morph<1&&[1,2,3].map(k=><path key={k} d={interpolatePath(clip(morph-k*.07),BEAN,RING)} fill="none" stroke={P.coral} strokeWidth={10} opacity={.22/k} strokeLinecap="round"/>)}
          <g clipPath="url(#cup)">{PARTS.map((p,k)=>{
            if(k>=count)return null;
            const sp=spring({frame:frame-(4.1+k/K*3.4)*FPS,fps:FPS,config:{damping:12,stiffness:110,mass:.8}});if(sp<.01)return null;
            const r=sz*p.s*.5;return <g key={k} transform={`translate(${p.x} ${p.y-(1-sp)*700})`}><circle r={r+2} fill={P.ink}/><circle r={r} fill={P.brown}/><circle cx={-r*.3} cy={-r*.3} r={r*.35} fill={P.tan}/></g>;})}</g>
        </g>
        {/* grind-style cards: UI stat grid like the reference */}
        {phase==='grind'&&CARDS.map(([name,kind,v],i)=>{const a=ez(EZ.out,T,4.7+i*.12,.5)*(1-seg(T,8.0,.3)),f=ez(EZ.out,T,5.1+i*.12,1.4),x=90+(i%2)*480,y=900+Math.floor(i/2)*180;
          return <g key={name} transform={`translate(${x} ${y+(1-a)*60})`} opacity={a}>
            <rect width={420} height={150} rx={24} fill={P.white} stroke={P.ink} strokeOpacity={.12} strokeWidth={3}/>
            <text x={26} y={40} fontSize={16} fill={P.dim} style={{...mono,letterSpacing:2}}>{kind}</text>
            <text x={26} y={88} fontSize={36} fontWeight={800} fill={P.ink}>{name}</text>
            <rect x={26} y={106} width={368} height={14} rx={7} fill={P.ink} opacity={.1}/><rect x={26} y={106} width={368*v*f} height={14} rx={7} fill={P.coral}/>
          </g>;})}
        {steam>0&&[-46,0,46].map((bx,i)=>{const dd=toD(pts(40,t=>[540+bx+noise2D('s'+i,t*2.4,T*.7)*26*t,1440-t*150]));
          return <g key={i}><Tube d={dd} w={9} color={P.white} light={P.white} outline="#9b8bd6" dash={evolvePath(steam,dd)}/></g>;})}
        <g transform={`translate(0 ${(1-card)*2300}) rotate(${-4*(1-card)} 540 790)`}>
          <rect x={90} y={358} width={900} height={900} rx={32} fill="#c9bdf0"/>
          <rect x={90} y={340} width={900} height={900} rx={32} fill={P.white}/>
          <text x={140} y={405} fontSize={20} fill={P.dim} style={mono}>journal of coffee brewing</text>
          <path d="M140 430H940" stroke={P.ink} strokeWidth={3}/>
          <text x={136} y={640} fontSize={210} fontWeight={900} fill={P.ink} letterSpacing={-10}>18–22%</text>
          <text x={140} y={725} fontSize={46} fontWeight={700} fill={P.ink}>of the coffee dissolves</text>
          <text x={140} y={780} fontSize={46} fontWeight={700} fill={P.ink}>into the cup</text>
          <g transform="translate(140 880)">
            <rect width={480*bar} height={44} rx={8} fill={P.blue}/><rect x={480} width={107*bar} height={44} rx={8} fill={P.sweet}/><rect x={587} width={213*bar} height={44} rx={8} fill={P.coral}/>
            <g fontSize={18} fill={P.ink} style={{...mono,letterSpacing:2}} opacity={bar}><text y={78}>sour</text><text x={470} y={78}>sweet</text><text x={800} y={78} textAnchor="end">bitter</text></g>
          </g>
          <text x={140} y={1050} fontSize={26} fill={P.ink} fontWeight={700} style={mono}>brew water 90–96 °C</text>
          <path d="M140 1085H940" stroke={P.ink} strokeWidth={2} opacity={.2}/>
          <text x={140} y={1200} fontSize={15} fill={P.dim} style={{...mono,letterSpacing:2}}>source: specialty coffee association · gold cup standard</text>
        </g>
      </g>
      {script.dials.map(dl=><Dial key={dl.id} x={dl.x} y={dl.y} label={dl.label} unit={dl.unit} value={dialVal(dl)} max={dl.max} decimals={dl.decimals} appear={ez(EZ.out,T,dl.at,.5)*(1-seg(T,dl.until,.3))} color={P.coral} fg={P.ink} track="rgba(42,36,51,.15)"/>)}
    </svg>
    {script.texts.map((tx,i)=>{const v=(T>=tx.at-.05&&T<tx.until+.3)?1-seg(T,tx.until,.25):0;
      return v>0?<div key={i} style={{position:'absolute',inset:0,opacity:v}}><Glyphs text={tx.text} frame={frame} startS={tx.at} size={tx.size} color={TXT[tx.color]} y={tx.y} font={tx.font} ca={false} wave={(tx as {wave?:number}).wave??0}/></div>:null;})}
    {phase==='extract'||phase==='grind'?<div style={{...mono,position:'absolute',bottom:100,width:W,textAlign:'center',fontSize:18,color:P.dim,letterSpacing:3}}>illustrative values, not a measurement</div>:null}
  </AbsoluteFill>;
  return <AbsoluteFill style={{background:BG[0],fontFamily:'DM Sans, Arial, sans-serif'}}>
    <style>{`@font-face{font-family:'DM Sans';src:url('${staticFile('DMSans.ttf')}')}`}</style>
    <CameraMotionBlur shutterAngle={140} samples={4}>{content}</CameraMotionBlur>
  </AbsoluteFill>;
};
