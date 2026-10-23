import React from 'react';
import {AbsoluteFill,Audio,Sequence,staticFile,useCurrentFrame} from 'remotion';
import {Transition} from './Transition';
import {Device,DeviceT} from './Devices';

// Generic motion-graphics edit driven by props from brainrot/motion.py: narration-timed keyword punches,
// shockwave rings, kinetic captions, animated backgrounds and varied scene transitions.
export const FPS=30;
const C={ink:'#101c27',cream:'#f5ead5',coral:'#ff765f',cyan:'#68d4e7',gold:'#ffd36b',lime:'#c8f560'};
const clip=(v:number)=>Math.max(0,Math.min(1,v));
const ease=(p:number)=>{p=clip(p);return p*p*(3-2*p);};
const back=(p:number)=>{p=clip(p);return 1+2.7*Math.pow(p-1,3)+1.7*Math.pow(p-1,2);};

type Word={text:string,start:number,end:number};
type Kw={text:string,at:number};
type SceneT={start:number,end:number,keywords:Kw[],device?:DeviceT};
export type MotionProps={scenes:SceneT[],words:Word[],duration:number,audio:string};
export const defaultMotionProps:MotionProps={scenes:[{start:0,end:1,keywords:[]}],words:[],duration:1,audio:'narration.mp3'};

const ACCENT=[C.lime,C.coral,C.cyan,C.gold];
const CREAM=(i:number)=>i%3===1;

function Scene({index,scene,words}:{index:number,scene:SceneT,words:Word[]}){
  const frame=useCurrentFrame(),t=frame/FPS,dark=!CREAM(index),accent=ACCENT[index%4];
  const ws=words.filter(w=>w.start>=scene.start&&w.start<scene.end),gt=t+scene.start;
  const gi=Math.max(0,ws.findIndex((w,i)=>gt>=w.start&&(!ws[i+1]||gt<ws[i+1].start))),g=Math.floor(gi/4)*4;
  const pop=ease(t/.45),len=scene.end-scene.start,fg=dark?C.cream:C.ink;
  return <AbsoluteFill style={{background:dark?C.ink:C.cream,color:fg,fontFamily:'DM Sans',overflow:'hidden'}}>
    <div style={{position:'absolute',inset:0,background:dark?'radial-gradient(ellipse at 50% 50%, #254052 0%, transparent 65%)':'radial-gradient(ellipse at 50% 50%, #fff9eb 0%, transparent 70%)'}}/>
    <div style={{position:'absolute',inset:0,backgroundImage:`radial-gradient(circle, ${dark?'rgba(255,255,255,.1)':'rgba(16,28,39,.09)'} 3px, transparent 4px)`,backgroundSize:'90px 90px',backgroundPosition:`${t*22}px ${t*15}px`}}/>
    <div style={{position:'absolute',inset:0,transform:`scale(${(1+(1-pop)*.05)*(1+t*.002)})`,transformOrigin:'50% 52%'}}>
      {[0,1,2].map(i=><div key={i} style={{position:'absolute',left:540-380-i*130,top:880-380-i*130,width:760+i*260,height:760+i*260,borderRadius:'50%',border:`6px ${i===1?'dashed':'solid'} ${accent}`,opacity:.16-i*.04,transform:`scale(${1+Math.sin(t*1.1+i)*.04}) rotate(${t*(12-i*5)}deg)`}}/>)}
      {scene.keywords.map((k,i)=>{const e=t-(k.at-scene.start);if(e<0||e>2.6)return null;const up=i%2===0,r=clip(e/.7);
        return <React.Fragment key={i}>
          <div style={{position:'absolute',left:340,top:(up?760:980)-200,width:400,height:400,borderRadius:'50%',border:`${14*(1-r)+2}px solid ${accent}`,transform:`scale(${.1+r*.9})`,opacity:e<.7?1-r:0}}/>
          <div style={{position:'absolute',left:40,right:40,top:up?690:910,textAlign:'center',whiteSpace:'nowrap',fontSize:k.text.length>9?104:140,fontWeight:900,letterSpacing:-5,lineHeight:1,color:accent,opacity:1-clip((e-2.3)/.3),transform:`rotate(${up?-3:3}deg) scale(${back(e/.35)})`,textShadow:dark?'0 10px 0 rgba(0,0,0,.35)':'0 10px 0 rgba(16,28,39,.18)'}}>{k.text.toUpperCase()}</div>
        </React.Fragment>;})}
      {scene.device&&<Device d={scene.device} k={t-(scene.device.at-scene.start)} dark={dark} accent={accent}/>}
    </div>
    <div style={{position:'absolute',top:0,left:0,height:12,width:`${clip(t/len)*100}%`,background:accent}}/>
    <div style={{position:'absolute',top:1790,left:40,right:40,textAlign:'center',whiteSpace:'nowrap',fontSize:56,fontWeight:850,letterSpacing:-2}}>{ws.slice(g,g+4).map((w,i)=><span key={g+i} style={{display:'inline-block',margin:'0 12px',color:g+i===gi?C.gold:fg,opacity:g+i===gi?1:.75,transform:`scale(${g+i===gi?1+(1-ease((gt-w.start)/.2))*.35:1})`}}>{w.text}</span>)}</div>
    <Transition index={index} t={t}/>
  </AbsoluteFill>;
}

export const MotionVideo=(p:MotionProps)=><AbsoluteFill><style>{`@font-face{font-family:'DM Sans';src:url('${staticFile('DMSans.ttf')}')}*{box-sizing:border-box}`}</style>
  {p.scenes.map((s,i)=>{const a=Math.round(s.start*FPS);return <Sequence key={i} from={a} durationInFrames={Math.max(1,Math.round(s.end*FPS)-a)}><Scene index={i} scene={s} words={p.words}/></Sequence>;})}
  <Audio src={staticFile(p.audio)}/></AbsoluteFill>;
