import React from 'react';
import {AbsoluteFill,Sequence,staticFile,useCurrentFrame} from 'remotion';

// Silent motion test: no skill, no narration. Six scenes joined by sweeping wipes, a continuous camera drift, HUD chrome.
const FPS=30,W=1080,H=1920;
const C={ink:'#0b0b0e',paper:'#f3f1ec',red:'#e5262d',dim:'#8a8a92'};
const BOUNDS=[0,3.5,7,11.5,16.5,21,27];
export const DELEGATION_FRAMES=BOUNDS[BOUNDS.length-1]*FPS;
const clip=(v:number)=>Math.max(0,Math.min(1,v));
const ease=(p:number)=>{p=clip(p);return p*p*(3-2*p);};
const out=(p:number)=>1-Math.pow(1-clip(p),3);
const back=(p:number)=>{p=clip(p);return 1+2.7*Math.pow(p-1,3)+1.7*Math.pow(p-1,2);};
const seg=(t:number,a:number,d:number)=>clip((t-a)/d);
const mono:React.CSSProperties={fontFamily:'Consolas, "Courier New", monospace',letterSpacing:4,textTransform:'uppercase'};
const hex=(n:number)=>String(n).padStart(2,'0');

function Chars({text,t,start,gap=.05,size,color}:{text:string,t:number,start:number,gap?:number,size:number,color:string}){
  return <div style={{display:'flex',justifyContent:'center',overflow:'hidden',paddingBottom:size*.12}}>
    {text.split('').map((c,i)=>{const p=out(seg(t,start+i*gap,.5));return <span key={i} style={{display:'inline-block',whiteSpace:'pre',fontSize:size,fontWeight:900,letterSpacing:-size*.04,color,lineHeight:1,transform:`translateY(${(1-p)*size*1.1}px) rotate(${(1-p)*-5}deg)`,opacity:p>0?1:0}}>{c}</span>;})}
  </div>;
}

function Hud({t,len,dark,tag}:{t:number,len:number,dark:boolean,tag:string}){
  const fg=dark?C.paper:C.ink,s=Math.floor(t),f=Math.floor((t%1)*FPS);
  const br=(s:React.CSSProperties)=><div style={{position:'absolute',width:34,height:34,borderColor:fg,borderStyle:'solid',borderWidth:0,opacity:.8,...s}}/>;
  return <>
    {br({top:50,left:50,borderTopWidth:3,borderLeftWidth:3})}{br({top:50,right:50,borderTopWidth:3,borderRightWidth:3})}
    {br({bottom:50,left:50,borderBottomWidth:3,borderLeftWidth:3})}{br({bottom:50,right:50,borderBottomWidth:3,borderRightWidth:3})}
    <div style={{...mono,position:'absolute',top:62,left:100,fontSize:22,color:fg,fontWeight:700}}>AI DELEGATION<div style={{color:C.dim,marginTop:6,fontSize:18}}>{tag}</div></div>
    <div style={{...mono,position:'absolute',top:62,right:100,fontSize:22,color:fg,fontWeight:700}}>00:00:{hex(s)}:{hex(f)}</div>
    <div style={{position:'absolute',left:100,right:100,bottom:68,height:3,background:dark?'rgba(255,255,255,.15)':'rgba(0,0,0,.15)'}}><div style={{height:3,width:`${clip(t/len)*100}%`,background:C.red}}/></div>
  </>;
}

// 0: kinetic type
function S0({t}:{t:number}){
  const p=ease(seg(t,2.5,.6));
  return <AbsoluteFill style={{background:C.paper,color:C.ink}}>
    {[0,1,2].map(i=><div key={i} style={{position:'absolute',left:540-300-i*110,top:900-300-i*110,width:600+i*220,height:600+i*220,borderRadius:'50%',border:`4px ${i===1?'dashed':'solid'} ${C.ink}`,opacity:.1,transform:`rotate(${t*(14-i*6)}deg) scale(${1+Math.sin(t*1.3+i)*.03})`}}/>)}
    <div style={{...mono,position:'absolute',top:760,width:W,textAlign:'center',fontSize:40,fontWeight:700,opacity:ease(seg(t,.1,.4)),transform:`translateY(${(1-ease(seg(t,.1,.5)))*30}px)`}}>The engineers at</div>
    <div style={{position:'absolute',top:830,width:W}}><Chars text="Anthropic" t={t} start={.45} size={190} color={C.ink}/></div>
    <div style={{position:'absolute',left:130,top:1075,height:14,width:(W-260)*out(seg(t,1.5,.7)),background:C.red}}/>
    <div style={{position:'absolute',left:0,top:1200,width:W,textAlign:'center',fontSize:76,fontWeight:900,color:C.red,letterSpacing:-3,transform:`scale(${back(seg(t,2.1,.4))}) rotate(${(1-p)*4}deg)`,opacity:t>2.1?1:0}}>say the opposite.</div>
  </AbsoluteFill>;
}

// 1: scribble draw-on and word slam
const scribble=(()=>{const pts:string[]=[];for(let i=0;i<=140;i++){const a=i*.34,r=40+i*1.3+Math.sin(i*.9)*34;pts.push(`${i?'L':'M'}${(270+Math.cos(a)*r*1.25).toFixed(1)} ${(210+Math.sin(a*1.15)*r*.8).toFixed(1)}`);}return pts.join(' ');})();
function S1({t}:{t:number}){
  const draw=out(seg(t,.2,1.8)),shake=t>2.2?Math.sin(t*60)*3:0,sl=back(seg(t,2.2,.35));
  return <AbsoluteFill style={{background:C.ink,color:C.paper}}>
    <div style={{...mono,position:'absolute',top:640,width:W,textAlign:'center',fontSize:40,fontWeight:700,opacity:ease(seg(t,0,.3))}}>to be fair</div>
    <svg width={540} height={420} viewBox="0 0 540 420" style={{overflow:"visible",position:'absolute',left:270,top:700,transform:`rotate(${shake}deg)`}}><path d={scribble} pathLength={1} fill="none" stroke={C.paper} strokeWidth={5} strokeLinecap="round" strokeDasharray={1} strokeDashoffset={1-draw}/></svg>
    <div style={{position:'absolute',top:1200,width:W,textAlign:'center',fontSize:46,fontWeight:700,opacity:ease(seg(t,1.2,.3))}}>it's</div>
    <div style={{position:'absolute',top:1260,width:W,textAlign:'center',fontSize:170,fontWeight:900,letterSpacing:-8+(1-sl)*40,color:C.red,transform:`scale(${.3+sl*.7}) translateX(${shake*3}px)`,opacity:t>2.2?1:0}}>COMPLEX</div>
  </AbsoluteFill>;
}

// 2: number count-up and stat grid
const PCT=[.46,.51,.56,.41,.47,.54,.42,.48,.5,.56,.43,.46,.42,.34,.59];
function S2({t}:{t:number}){
  const n=Math.round(15*ease(seg(t,.15,.9))),pop=back(seg(t,.15,.5));
  return <AbsoluteFill style={{background:C.ink,color:C.paper}}>
    <div style={{position:'absolute',inset:0,transform:`scale(${1+t*.025})`,transformOrigin:'50% 40%'}}>
      <div style={{position:'absolute',left:90,top:260,fontSize:300,fontWeight:900,color:C.red,letterSpacing:-14,lineHeight:1,transform:`scale(${pop}) translateY(${(1-pop)*60}px)`,transformOrigin:'0 100%'}}>{n}</div>
      <div style={{position:'absolute',left:500,top:420,fontSize:92,fontWeight:900,letterSpacing:-4,transform:`translateX(${(1-out(seg(t,.5,.5)))*400}px)`,opacity:out(seg(t,.5,.3))}}>PROJECTS</div>
      <div style={{...mono,position:'absolute',left:500,top:530,fontSize:26,color:C.dim,opacity:ease(seg(t,.9,.4))}}>in flight</div>
      <div style={{position:'absolute',left:90,right:90,top:680,display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:22}}>
        {PCT.map((pc,i)=>{const a=seg(t,.7+i*.07,.45),fill=out(seg(t,1+i*.07,1.6))*pc;
          return <div key={i} style={{background:'#17171c',border:'1px solid #2a2a31',borderRadius:14,padding:'18px 16px',opacity:a,transform:`translateY(${(1-out(a))*50}px)`}}>
            <div style={{...mono,fontSize:17,letterSpacing:2,fontWeight:700,marginBottom:16}}>project_{hex(i+1)}</div>
            <div style={{height:10,borderRadius:5,background:'#2c2c34'}}><div style={{height:10,borderRadius:5,width:`${fill*100}%`,background:C.paper}}/></div>
            <div style={{...mono,fontSize:15,letterSpacing:1,color:C.dim,marginTop:12}}>{Math.round(fill*100)}%</div></div>;})}
      </div>
      <div style={{position:'absolute',left:0,width:W,top:1500,textAlign:'center',fontSize:70,fontWeight:900,letterSpacing:-3,opacity:ease(seg(t,3.2,.4)),transform:`scale(${back(seg(t,3.2,.4))})`}}>sitting <span style={{color:C.red}}>half</span> done</div>
    </div>
  </AbsoluteFill>;
}

// 3: agent wiring, then REVERSE slam
const TASKS=['Email','Research','Reports','Social','Support'];
function S3({t}:{t:number}){
  const rev=seg(t,3.1,.25),slam=back(seg(t,3.1,.4)),shake=t>3.1&&t<3.6?Math.sin(t*90)*14*(1-(t-3.1)*2):0;
  return <AbsoluteFill style={{background:C.paper,color:C.ink}}>
    <div style={{...mono,position:'absolute',top:240,width:W,textAlign:'center',fontSize:34,fontWeight:700,opacity:ease(seg(t,0,.3))}}>everyone said</div>
    <div style={{position:'absolute',top:310,width:W,textAlign:'center',fontSize:62,fontWeight:900,letterSpacing:-2,opacity:ease(seg(t,.1,.3))}}>build an agent <span style={{color:C.red}}>per job.</span></div>
    <div style={{position:'absolute',inset:0,opacity:1-rev*.8,filter:`blur(${rev*5}px) saturate(${1-rev})`}}>
      {TASKS.map((k,i)=>{const y=620+i*150,a=seg(t,.5+i*.15,.4),line=out(seg(t,1.1+i*.2,.7)),nx=860+(i%2?-30:20),dot=(t*.7+i*.2)%1;
        return <React.Fragment key={k}>
          <div style={{position:'absolute',left:110,top:y-34,padding:'16px 34px',borderRadius:40,background:C.ink,color:C.paper,fontSize:40,fontWeight:800,transform:`translateX(${(1-out(a))*-300}px)`,opacity:a}}>{k}</div>
          <svg width={W} height={H} style={{position:'absolute',inset:0}}><line x1={330} y1={y} x2={330+(nx-330)*line} y2={y} stroke={C.red} strokeWidth={3} strokeDasharray="12 10"/>
            {t>1.8+i*.2&&<circle cx={330+(nx-330)*dot} cy={y} r={9} fill={C.red}/>}</svg>
          <div style={{position:'absolute',left:nx-34,top:y-34,width:68,height:68,borderRadius:'50%',border:`4px solid ${C.ink}`,background:C.paper,transform:`scale(${back(seg(t,1.7+i*.2,.35))})`}}><div style={{position:'absolute',inset:16,borderRadius:'50%',background:C.red}}/></div>
        </React.Fragment>;})}
    </div>
    <div style={{position:'absolute',inset:0,background:C.ink,opacity:rev*.92}}/>
    <div style={{...mono,position:'absolute',top:880,width:W,textAlign:'center',fontSize:44,fontWeight:700,color:C.paper,opacity:rev}}>the exact</div>
    <div style={{position:'absolute',top:930,width:W,textAlign:'center',fontSize:225,fontWeight:900,letterSpacing:-10,color:C.paper,opacity:t>3.1?1:0,transform:`scale(${.4+slam*.6}) translateX(${shake}px)`}}>REVERSE</div>
  </AbsoluteFill>;
}

// 4: red title card
const CHIPS=['01 INTERVIEW','02 TOOLBOX','03 PROOF'];
function S4({t}:{t:number}){
  const ai=back(seg(t,0,.5));
  return <AbsoluteFill style={{background:C.red,color:C.paper}}>
    {[0,1].map(i=><div key={i} style={{position:'absolute',left:540-420-i*160,top:800-420-i*160,width:840+i*320,height:840+i*320,borderRadius:'50%',border:`5px ${i?'dashed':'solid'} rgba(255,255,255,.22)`,transform:`scale(${.6+out(seg(t,0,1.4))*.4}) rotate(${t*20*(i?-1:1)}deg)`}}/>)}
    <div style={{position:'absolute',top:480,width:W,textAlign:'center',fontSize:430,fontWeight:900,letterSpacing:-20,lineHeight:1,transform:`scale(${.2+ai*.8})`,opacity:t>0?1:0}}>AI</div>
    <div style={{position:'absolute',top:900,width:W,display:'flex',justifyContent:'center'}}>
      {'DELEGATION'.split('').map((c,i)=>{const p=out(seg(t,.5+i*.04,.45)),d=i%2?1:-1;return <span key={i} style={{fontSize:140,fontWeight:900,letterSpacing:-8,color:C.ink,display:'inline-block',transform:`translateY(${(1-p)*d*300}px)`,opacity:p>0?1:0}}>{c}</span>;})}
    </div>
    <div style={{position:'absolute',top:1130,width:W,display:'flex',justifyContent:'center',gap:14}}>
      {CHIPS.map((c,i)=><div key={c} style={{padding:'14px 24px',borderRadius:40,background:C.paper,color:C.ink,fontSize:28,fontWeight:800,transform:`scale(${back(seg(t,1.4+i*.2,.35))})`}}>{c}</div>)}
    </div>
  </AbsoluteFill>;
}

// 5: prompt typed, playbook builds, proof stamp
const PROMPT='Turn everything I just told you into a playbook for this task: the goal, the steps in order, the rules.';
const LINES:[string,string][]=[['GOAL','Weekly report, one page'],['STEP 1','Pull the numbers'],['STEP 2','Check every total, then fill the template'],['RULE','Numbers first']];
function S5({t}:{t:number}){
  const typed=PROMPT.slice(0,Math.floor(clip((t-.4)/1.8)*PROMPT.length)),cardA=out(seg(t,3,.6)),hi=Math.floor(clip((t-4.6)/2.2)*4),stamp=back(seg(t,5.6,.3));
  return <AbsoluteFill style={{background:C.ink,color:C.paper}}>
    <div style={{...mono,position:'absolute',top:250,left:110,fontSize:34,fontWeight:700,color:C.red,opacity:ease(seg(t,0,.3))}}>01 / interview</div>
    <div style={{position:'absolute',left:90,right:90,top:340,background:'#16161b',border:'1px solid #2e2e36',borderRadius:22,padding:'34px 38px',fontSize:38,lineHeight:1.35,minHeight:230,transform:`translateY(${(1-out(seg(t,0,.5)))*80}px)`,opacity:ease(seg(t,0,.3))}}>
      <div style={{...mono,fontSize:18,color:C.red,fontWeight:700,marginBottom:14}}>prompt</div>{typed}<span style={{opacity:Math.floor(t*3)%2?0:1,color:C.red}}>|</span></div>
    <div style={{position:'absolute',left:90,right:90,top:800,background:C.paper,color:C.ink,borderRadius:26,padding:'40px 44px',boxShadow:'0 30px 80px rgba(229,38,45,.25)',transform:`translateY(${(1-cardA)*700}px) rotate(${(1-cardA)*5}deg)`,opacity:cardA>0?1:0}}>
      <div style={{...mono,fontSize:26,fontWeight:800,marginBottom:30}}><span style={{color:C.red}}>●</span> playbook.md</div>
      {LINES.map(([k,v],i)=>{const a=out(seg(t,3.5+i*.35,.4)),act=t>4.6&&hi===i;
        return <div key={k} style={{padding:'14px 18px',margin:'4px -18px',borderRadius:12,border:`3px solid ${act?C.red:'transparent'}`,background:act?'rgba(229,38,45,.08)':'transparent',opacity:a,transform:`translateX(${(1-a)*60}px)`}}>
          <div style={{...mono,fontSize:19,color:C.dim,fontWeight:700}}>{k}</div><div style={{fontSize:44,fontWeight:700,marginTop:4}}>{v}</div></div>;})}
      <div style={{position:'absolute',right:40,bottom:44,border:`6px solid ${C.red}`,color:C.red,fontSize:56,fontWeight:900,padding:'6px 22px',borderRadius:10,letterSpacing:4,transform:`rotate(-9deg) scale(${.2+stamp*.8})`,opacity:t>5.6?1:0}}>PASSED</div>
    </div>
  </AbsoluteFill>;
}

const SCENES=[S0,S1,S2,S3,S4,S5],DARK=[false,true,true,false,false,true],TAGS=['WHO AGREES','WHO AGREES','SOUND FAMILIAR','THE ADVICE','THE METHOD','THE LOOP'];

// Wipe: a skewed panel sweeps right to left across each boundary; the scene swaps while it covers the frame.
function Wipe(){
  const t=useCurrentFrame()/FPS,w=W*1.5;
  return <>{BOUNDS.slice(1,-1).map((b,i)=>{const p=(t-(b-.3))/.6;if(p<0||p>1)return null;
    return <div key={i} style={{position:'absolute',top:-50,height:H+100,width:w,left:W-ease(p)*(W+w),background:i%2?C.paper:C.red,transform:'skewX(-12deg)'}}/>;})}</>;
}

function SceneFrame({i,S,len}:{i:number,S:React.FC<{t:number}>,len:number}){
  const t=useCurrentFrame()/FPS;
  return <AbsoluteFill><div style={{position:'absolute',inset:0,transform:`scale(${1.03+t*.006}) rotate(${Math.sin(t*.7+i)*.25}deg)`}}><S t={t}/></div><Hud t={t} len={len} dark={DARK[i]} tag={TAGS[i]}/></AbsoluteFill>;
}

export const Delegation=()=>(
  <AbsoluteFill style={{background:C.ink,fontFamily:'DM Sans, Arial, sans-serif',overflow:'hidden'}}>
    <style>{`@font-face{font-family:'DM Sans';src:url('${staticFile('DMSans.ttf')}')}*{box-sizing:border-box}`}</style>
    {SCENES.map((S,i)=>{const a=Math.round(BOUNDS[i]*FPS),b=Math.round(BOUNDS[i+1]*FPS);
      return <Sequence key={i} from={a} durationInFrames={b-a}><SceneFrame i={i} S={S} len={(b-a)/FPS}/></Sequence>;})}
    <Wipe/>
  </AbsoluteFill>
);
