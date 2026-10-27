import React from 'react';
import {Easing,interpolate,spring} from 'remotion';
import {noise2D} from '@remotion/noise';

// Reusable vector-motion primitives (After-Effects-style). Shared by compositions; no scene logic here.
export const FPS=30,W=1080,H=1920;
export const C={ink:'#0b0b0e',cream:'#f3f1ec',red:'#e5262d',hi:'#ff8f7d',deep:'#7a0f14',lime:'#d7ff3a',dim:'#8a8a92',blue:'#4b7bff',brown:'#6b3a22',tan:'#c98a5b'};
export const COL:Record<string,string>={cream:C.cream,red:C.red,lime:C.lime,ink:C.ink,dim:C.dim,blue:C.blue};
export const clip=(v:number)=>Math.max(0,Math.min(1,v));
export const seg=(t:number,a:number,d:number)=>clip((t-a)/d);
export const EZ={out:Easing.bezier(.16,1,.3,1),inout:Easing.bezier(.65,0,.35,1)};
export const ez=(f:(x:number)=>number,t:number,a:number,d:number)=>f(seg(t,a,d));
export const mono:React.CSSProperties={fontFamily:'Consolas, "Courier New", monospace',letterSpacing:4,textTransform:'uppercase'};
export const wiggle=(seed:number,t:number,amp:number,freq=1)=>noise2D('w'+seed,t*freq,seed)*amp;

export const pts=(n:number,f:(t:number)=>[number,number])=>Array.from({length:n},(_,i)=>f(i/(n-1)));
export const toD=(p:[number,number][])=>p.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join('');

// Tube-lit stroke: dark outline, body, offset highlight; accepts an evolvePath dash for trim-path draw-on.
export function Tube({d,w=18,color=C.red,light=C.hi,outline='#150507',dash}:{d:string,w?:number,color?:string,light?:string,outline?:string,dash?:{strokeDasharray:string,strokeDashoffset:number}}){
  const p={fill:'none',strokeLinecap:'round' as const,strokeLinejoin:'round' as const,...dash};
  return <g><path d={d} stroke={outline} strokeWidth={w+12} {...p}/><path d={d} stroke={color} strokeWidth={w} {...p}/><path d={d} stroke={light} strokeWidth={w*.22} transform="translate(-2,-4)" opacity={.85} {...p}/></g>;
}

// Halftone disc: dot radius falls off from a light source up-left of centre.
export const Halftone=React.memo(function Halftone({cx,cy,rx,ry,appear,t,color=C.cream}:{cx:number,cy:number,rx:number,ry:number,appear:number,t:number,color?:string}){
  const s=16,out:React.ReactNode[]=[],R=Math.ceil(ry/s*1.15),Cc=Math.ceil(rx/s*1.15);
  for(let r=-R;r<=R;r++)for(let c=-Cc;c<=Cc;c++){
    const x=c*s+(r%2?s/2:0),y=r*s*.88,d=Math.hypot(x/rx,y/ry);if(d>1)continue;
    const l=Math.hypot((x+rx*.25)/rx,(y+ry*.3)/ry),k=Math.max(0,1-Math.pow(l,1.7))*(1-d*.2)*appear*(1+Math.sin(t*1.4+x*.01)*.05);
    if(k>.04)out.push(<circle key={r+'_'+c} cx={cx+x} cy={cy+y} r={s*.5*k} fill={color}/>);}
  return <g>{out}</g>;
});

// Per-glyph text animator: spring slide-up through a mask, optional wave and chromatic aberration on impact.
export function Glyphs({text,frame,startS,size,color,y,gap=.04,wave=0,font='sans',ca=true}:{text:string,frame:number,startS:number,size:number,color:string,y:number,gap?:number,wave?:number,font?:string,ca?:boolean}){
  const t=frame/FPS;
  return <div style={{position:'absolute',top:y,width:W,display:'flex',justifyContent:'center',overflow:'hidden',paddingBottom:size*.15,...(font==='mono'?mono:{})}}>
    {text.split('').map((ch,i)=>{const sp=spring({frame:frame-(startS+i*gap)*FPS,fps:FPS,config:{damping:13,stiffness:170,mass:.7}});
      const off=ca?Math.max(0,(1-sp))*10:0,w=Math.sin(t*5+i*.7)*wave*sp;
      return <span key={i} style={{display:'inline-block',whiteSpace:'pre',fontSize:size,fontWeight:font==='mono'?700:900,letterSpacing:font==='mono'?4:-size*.04,lineHeight:1,color,textShadow:off>.5?`${off}px 0 #00e5ff, ${-off}px 0 #ff2d55`:'none',transform:`translateY(${(1-sp)*size*1.2+w}px) rotate(${(1-sp)*-7}deg)`,opacity:sp>.01?1:0}}>{ch}</span>;})}
  </div>;
}

// Gauge dial with persistent needle and counting readout.
export function Dial({x,y,label,unit,value,max,decimals=0,appear,color=C.lime,fg=C.cream,track='#2c2c34'}:{x:number,y:number,label:string,unit:string,value:number,max:number,decimals?:number,appear:number,color?:string,fg?:string,track?:string}){
  const r=70,a0=135,sweep=270,p=clip(value/max),a=(a0+sweep*p)*Math.PI/180;
  const arc=(p2:number)=>{const e=(a0+sweep*p2)*Math.PI/180,s=a0*Math.PI/180;return `M${r*Math.cos(s)} ${r*Math.sin(s)}A${r} ${r} 0 ${sweep*p2>180?1:0} 1 ${r*Math.cos(e)} ${r*Math.sin(e)}`;};
  return <g transform={`translate(${x} ${y}) scale(${appear})`} opacity={appear}>
    <path d={arc(1)} stroke={track} strokeWidth={9} fill="none" strokeLinecap="round"/>
    {p>.005&&<path d={arc(p)} stroke={color} strokeWidth={9} fill="none" strokeLinecap="round"/>}
    <line x1={0} y1={0} x2={(r-16)*Math.cos(a)} y2={(r-16)*Math.sin(a)} stroke={color} strokeWidth={5} strokeLinecap="round"/><circle r={7} fill={color}/>
    <text y={34} textAnchor="middle" fontSize={30} fontWeight={800} fill={fg} style={{...mono,letterSpacing:1}}>{value.toFixed(decimals)}<tspan fontSize={18} fill={C.dim}> {unit}</tspan></text>
    <text y={r+44} textAnchor="middle" fontSize={17} fill={color} style={{...mono,letterSpacing:2}}>{label}</text>
  </g>;
}

// Film grain + vignette overlay.
export function Grain({frame}:{frame:number}){
  return <>
    <svg width={W} height={H} style={{position:'absolute',inset:0,mixBlendMode:'overlay',opacity:.16,pointerEvents:'none'}}>
      <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves={2} seed={Math.floor(frame)%7}/><feColorMatrix type="saturate" values="0"/></filter>
      <rect width={W} height={H} filter="url(#grain)"/></svg>
    <div style={{position:'absolute',inset:0,background:'radial-gradient(ellipse at 50% 50%, transparent 55%, rgba(0,0,0,.55) 100%)',pointerEvents:'none'}}/>
  </>;
}

export const camAt=(t:number,cam:{at:number,zoom:number,cy:number}[])=>({
  zoom:interpolate(t,cam.map(c=>c.at),cam.map(c=>c.zoom),{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'}),
  cy:interpolate(t,cam.map(c=>c.at),cam.map(c=>c.cy),{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'})});
