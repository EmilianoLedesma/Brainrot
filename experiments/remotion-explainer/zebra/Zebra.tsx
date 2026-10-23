import React from 'react';
import {AbsoluteFill,Audio,Sequence,staticFile,useCurrentFrame} from 'remotion';
import plan from '../public/zebra/scene-plan.json';
import words from '../public/zebra/words.json';
import {Quad,Fly} from './Quad';
import {Transition} from '../Overlay';

// Why zebras have stripes: eight narration-timed scenes. One hero animal runs through the film;
// each scene adds one focus-grabbing device (counter, speed gauge, stamp, shockwave, eye view...).
// Study-based visuals are schematic illustrations of the cited findings, not measured data.
const FPS=30;
const C={ink:'#101c27',cream:'#f5ead5',coral:'#ff765f',cyan:'#68d4e7',gold:'#ffd36b',lime:'#c8f560'};
const clip=(v:number)=>Math.max(0,Math.min(1,v));
const ease=(p:number)=>{p=clip(p);return p*p*(3-2*p);};
const back=(p:number)=>{p=clip(p);return 1+2.7*Math.pow(p-1,3)+1.7*Math.pow(p-1,2);};
const lerp=(a:number,b:number,p:number)=>a+(b-a)*p;
type P={t:number,cue:(phrase:string,fallback:number)=>number};

const At=({x,y,w,s=1,r=0,o=1,children}:{x:number,y:number,w:number,s?:number,r?:number,o?:number,children:React.ReactNode})=><div style={{position:'absolute',left:x,top:y,width:w,transform:`rotate(${r}deg) scale(${s})`,opacity:o}}>{children}</div>;
const T=({y,children,size=90,color=C.cream,s=1,o=1,x=60,w=960,align='center',r=0}:{y:number,children:React.ReactNode,size?:number,color?:string,s?:number,o?:number,x?:number,w?:number,align?:'center'|'left',r?:number})=><div style={{position:'absolute',left:x,top:y,width:w,textAlign:align,fontSize:size,fontWeight:900,letterSpacing:-size*.03,lineHeight:1.02,color,opacity:o,transform:`rotate(${r}deg) scale(${s})`,whiteSpace:'nowrap'}}>{children}</div>;
// Big keyword that punches in on a spoken cue and leaves again.
const Kw=({t,at,y,text,size=120,color=C.lime,hold=2.4,r=0}:{t:number,at:number,y:number,text:string,size?:number,color?:string,hold?:number,r?:number})=>{const k=t-at;if(k<0||k>hold)return null;return <T y={y} x={40} w={1000} size={size} color={color} s={back(k/.35)} o={1-clip((k-(hold-.3))/.3)} r={r}>{text}</T>;};
const Ring=({x,y,p,color=C.coral}:{x:number,y:number,p:number,color?:string})=>p<=0||p>=1?null:<div style={{position:'absolute',left:x-200,top:y-200,width:400,height:400,borderRadius:'50%',border:`${14*(1-p)+2}px solid ${color}`,transform:`scale(${.1+p*.9})`,opacity:1-p}}/>;
const Hero=({x,y,width,t,progress=1,shift=0,scale=1}:{x:number,y:number,width:number,t:number,progress?:number,shift?:number,scale?:number})=><At x={x} y={y+Math.sin(t*1.3)*8} w={width} s={scale}><Quad width={width} progress={progress} shift={shift}/></At>;
// Converts a point in Quad viewBox space to screen space.
const qp=(x:number,y:number,left:number,top:number,width:number):[number,number]=>[left+(x+10)*width/660,top+(y+10)*width/660];

const S0=({t,cue}:P)=>{
  const test=cue('test them',16),chips:[string,number,string,number][]=[['CAMOUFLAGE',cue('camouflage',9.5),C.cyan,-1],['CONFUSING LIONS',cue('confusing lions',11),C.gold,1],['STAYING COOL',cue('staying cool',12.5),C.coral,-1]];
  const q=t<test?0:back((t-test)/.4);
  return <>
    <Kw t={t} at={.2} y={200} size={124} text="WHY STRIPES?" hold={99} color={C.cream}/>
    <Hero x={30} y={780} width={1020} t={t} progress={ease((t-.4)/2.6)} scale={1+t*.004}/>
    {chips.map(([label,at,col,side],i)=>{const p=back((t-at)/.45),fade=1-ease((t-test)/.5);return t<at?null:<At key={i} x={side<0?lerp(-700,60,clip(p)):lerp(1100,380,clip(p))} y={400+i*125} w={640} r={side*3} o={fade}><div style={{background:col,color:C.ink,fontSize:62,fontWeight:900,letterSpacing:-2,padding:'14px 34px',borderRadius:70,textAlign:'center',boxShadow:'0 12px 0 rgba(0,0,0,.3)'}}>{label}</div></At>;})}
    {t>=test&&<T y={430} size={560} color={C.lime} s={q} r={Math.sin(t*18)*4} o={1-ease((t-test-2.5)/.8)}>?</T>}
  </>;
};

const S1=({t,cue}:P)=>{
  const a7=cue('seven',3.5),a21=cue('twenty one',5.5),aR=cue('camouflage predators',11),aF=cue('places with',22);
  const n7=Math.round(7*ease((t-a7)/.7)),n21=Math.round(21*ease((t-a21)/1));
  const rows=['CAMOUFLAGE','PREDATORS','HEAT','SOCIAL LIFE'];
  return <>
    <At x={90} y={190+(1-ease(t/.6))*-420} w={900} r={-2}><div style={{background:'#fffaf0',color:C.ink,border:`6px solid ${C.ink}`,borderRadius:18,padding:'22px 34px',boxShadow:'0 14px 0 rgba(16,28,39,.25)'}}><div style={{fontSize:58,fontWeight:900,letterSpacing:-1.5}}>CARO ET AL. · 2014</div><div style={{fontSize:36,fontWeight:700,opacity:.7,marginTop:6}}>Nature Communications</div></div></At>
    <T y={520} x={60} w={480} size={190} color={C.coral}>{n7}</T><T y={730} x={60} w={480} size={40} color={C.ink}>HORSE RELATIVES</T>
    <T y={520} x={540} w={480} size={190} color={C.coral}>{n21}</T><T y={730} x={540} w={480} size={40} color={C.ink}>SUBSPECIES</T>
    <svg width={1080} height={1920} style={{position:'absolute',inset:0}}>{Array.from({length:21},(_,i)=>{const p=back((t-a21-.05*i)/.3);if(t<a21)return null;const cx=130+(i%7)*136,cy=870+Math.floor(i/7)*86;return <g key={i} transform={`translate(${cx} ${cy}) scale(${p})`}><circle r={30} fill={C.cream} stroke={C.ink} strokeWidth={6}/>{[-14,0,14].map(x=><path key={x} d={`M${x} -24V24`} stroke={C.ink} strokeWidth={7}/>)}</g>;})}</svg>
    {rows.map((label,i)=>{const at=aR+i*.7;if(t<at)return null;const p=ease((t-at)/.35),cross=ease((t-at-.3)/.25);return <div key={i} style={{position:'absolute',left:90+(1-p)*1000,top:1190+i*108,width:900,height:94,border:`5px solid ${C.ink}`,borderRadius:24,opacity:.55+.45*(1-cross),display:'flex',alignItems:'center',padding:'0 34px',fontSize:50,fontWeight:900,color:C.ink,letterSpacing:-1}}>{label}<svg width={80} height={80} style={{marginLeft:'auto'}}><path d="M12 12L68 68M68 12L12 68" stroke={C.coral} strokeWidth={12} strokeLinecap="round" strokeDasharray={112} strokeDashoffset={112*(1-cross)}/></svg></div>;})}
    {t>=aF&&<div style={{position:'absolute',left:90,top:1190+4*108,width:900,height:94,background:C.lime,border:`5px solid ${C.ink}`,borderRadius:24,display:'flex',alignItems:'center',padding:'0 34px',fontSize:54,fontWeight:900,color:C.ink,letterSpacing:-1,transform:`scale(${back((t-aF)/.4)})`,boxShadow:`0 0 ${30+Math.sin(t*6)*14}px ${C.lime}`}}>BITING FLIES<svg width={80} height={80} style={{marginLeft:'auto'}}><path d="M12 42L32 62L68 18" stroke={C.ink} strokeWidth={13} strokeLinecap="round" strokeLinejoin="round" fill="none"/></svg></div>}
  </>;
};

const S2=({t,cue}:P)=>{
  const aB=cue('blood',3.5),aD=cue('disease',6.5),aL=cue('short hair',8.5),pl=ease((t-aL-.4)/1.4);
  const lx=540+Math.sin(t*1.6)*320,ly=640+Math.sin(t*2.7)*110,[zx,zy]=qp(150,150,40,1000,1000),land=[zx,zy-60],fx=lerp(lx,land[0],pl),fy=lerp(ly,land[1],pl),flip=pl<1&&Math.cos(t*1.6)<0;
  return <>
    <Hero x={40} y={1000} width={1000} t={t}/>
    {t>=aB&&<At x={110} y={330+(1-ease((t-aB)/.4))*-400} w={860} o={1-ease((t-aB-3.2)/.4)}><div style={{display:'flex',alignItems:'center',gap:26,padding:'24px 32px',borderRadius:30,background:'rgba(16,28,39,.94)',border:`5px solid ${C.coral}`,boxShadow:'0 14px 0 rgba(0,0,0,.3)'}}><div style={{flex:'none',width:66,height:66,borderRadius:'50%',background:C.coral,color:C.ink,fontSize:48,fontWeight:900,display:'grid',placeItems:'center'}}>!</div><div style={{color:C.cream,fontSize:46,fontWeight:900,letterSpacing:-1.2,lineHeight:1.05}}>BLOOD-FEEDING FLIES</div></div></At>}
    <At x={fx-100} y={fy-80} w={200} s={1} r={0}><div style={{transform:`scaleX(${flip?-1:1})`}}><Fly size={200}/></div></At>
    <Kw t={t} at={aD} y={560} text="DISEASE" color={C.coral} size={150} hold={2.4} r={-4}/>
    {t>=aL+1.6&&<><Ring x={land[0]} y={land[1]+30} p={((t-aL-1.6)%1.6)/1.6} color={C.coral}/><At x={land[0]-26} y={land[1]+30+Math.min(60,(t-aL-1.6)*40)} w={52} s={ease((t-aL-1.6)/.8)}><svg width={52} height={70} viewBox="0 0 52 70"><path d="M26 0C26 0 4 34 4 48a22 22 0 0 0 44 0C48 34 26 0 26 0Z" fill={C.coral}/></svg></At></>}
    {t>=aL&&<At x={560} y={930} w={420} o={ease((t-aL)/.4)}><div style={{background:C.cream,color:C.ink,fontSize:48,fontWeight:900,padding:'10px 28px',borderRadius:16,display:'inline-block',letterSpacing:-1}}>SHORT HAIR</div></At>}
  </>;
};

const Panel=({top,label}:{top:number,label:string})=><><div style={{position:'absolute',left:40,top,width:1000,height:500,borderRadius:40,background:'rgba(255,255,255,.05)',border:'3px solid rgba(255,255,255,.2)'}}/><T y={top+22} x={80} w={400} size={54} color={C.cyan} align="left">{label}</T></>;
const Gauge=({top,v,color}:{top:number,v:number,color:string})=><><T y={top+424} x={80} w={200} size={34} color={C.cream} align="left" o={.8}>SPEED</T><div style={{position:'absolute',left:260,top:top+426,width:680,height:30,borderRadius:15,background:'rgba(255,255,255,.14)'}}><div style={{width:`${clip(v)*100}%`,height:'100%',borderRadius:15,background:color}}/></div></>;
const S3=({t,cue}:P)=>{
  const aS=cue('about as often',9),tA=cue('near a zebra',17.5),pa=clip((t-tA)/2.4),tops=[330,930],contact=.75;
  const orbit=(top:number)=>[761+Math.cos(t*2.2)*260,top+250+Math.sin(t*2.2)*110];
  const horse=pa<=0?orbit(tops[0]):[lerp(120,640,1-Math.pow(1-pa,3)),lerp(tops[0]+250,tops[0]+215,ease(pa))];
  const zb=pa<=0?orbit(tops[1]):pa<contact?[lerp(120,640,pa/contact),tops[1]+225]:[640-ease((pa-contact)/.25)*190,tops[1]+225-Math.sin(clip((pa-contact)/.25)*Math.PI)*60-(pa-contact)*200];
  const bounceAt=tA+contact*2.4;
  return <>
    <T y={190} size={92}>{t<tA-1?'SAME APPROACH':'THE LAST SECOND'}</T>
    <Panel top={tops[0]} label="HORSE"/><Panel top={tops[1]} label="ZEBRA"/>
    <At x={540} y={tops[0]+110} w={470}><Quad width={470} fill="#a9743f" stripes={false} mane="#2a1a10"/></At>
    <At x={540} y={tops[1]+110} w={470}><Quad width={470}/></At>
    <At x={horse[0]-45} y={horse[1]-36} w={90}><Fly size={90}/></At><At x={zb[0]-45} y={zb[1]-36} w={90}><Fly size={90}/></At>
    <Gauge top={tops[0]} v={pa<=0?.7:Math.pow(1-pa,2)} color={C.cyan}/><Gauge top={tops[1]} v={pa<=0?.7:pa<contact?1:lerp(1,.45,(pa-contact)/.25)} color={C.coral}/>
    {t>=aS&&t<tA-.5&&<T y={843} size={74} color={C.lime} s={back((t-aS)/.35)}>≈ SAME</T>}
    <Ring x={640} y={tops[1]+225} p={(t-bounceAt)/.6} color={C.coral}/>
    <Kw t={t} at={bounceAt} y={1080} text="BOUNCE!" size={150} color={C.coral} hold={2} r={-5}/>
    {pa>=1&&<T y={tops[0]+22} x={560} w={400} size={46} color={C.lime} o={ease((t-tA-2.4)/.3)}>LANDED</T>}
  </>;
};

const coatDots=(n:number,seed:number)=>Array.from({length:n},(_,i)=>[135+((i*97+seed*31)%330),100+((i*53+seed*17)%150)]);
const S4=({t,cue}:P)=>{
  const a=cue('hardly any',5.5),tops=[290,760,1230],rows:[string,string,boolean,string,number][]=[['STRIPED','#f6f1e4',true,'#14202b',2],['BLACK','#1b232b',false,'#000',12],['WHITE','#ffffff',false,'#888',11]];
  return <>
    {rows.map(([label,fill,st,mane,n],i)=>{const p=back((t-.1-i*.4)/.45),top=tops[i];return <React.Fragment key={i}>
      <At x={lerp(-700,40,clip(p))} y={top} w={600}><Quad width={600} fill={fill} stripes={st} mane={mane}/></At>
      <T y={top+130} x={690} w={360} size={68} color={C.ink} align="left" o={clip(p)}>{label}</T>
      <svg width={1080} height={1920} style={{position:'absolute',inset:0}}>{coatDots(n,i).map(([x,y],j)=>{const at=a+j*.22,[sx,sy]=qp(x,y,40,top,600),k=back((t-at)/.25);return t<at?null:<circle key={j} cx={sx} cy={sy-Math.max(0,1-k)*80} r={15} fill={C.coral} stroke={C.ink} strokeWidth={4} opacity={clip(k)}/>;})}</svg>
    </React.Fragment>;})}
    <T y={1700} size={34} color={C.ink} o={.7}>ILLUSTRATIVE / NOT MEASURED</T>
  </>;
};

const S5=({t,cue}:P)=>{
  const a=cue('fewer biting',7),rows:[string,boolean,number,number][]=[['UNPAINTED',false,9,6],['PAINTED STRIPES',true,3,2]],tops=[330,960];
  return <>
    <Kw t={t} at={a} y={190} text="FEWER FLIES" size={124} hold={4}/>
    {rows.map(([label,st,rate,flies],i)=>{const top=tops[i],tail=Math.sin(t*rate)*(i?9:28),cx=40+300*.97,cy=top+200;return <React.Fragment key={i}>
      <At x={40} y={top} w={640}><Quad width={640} fill="#222b34" stripes={st} stripe="#f1ece0" mane="#222b34" tail={tail}/></At>
      {Array.from({length:flies},(_,j)=><At key={j} x={cx+Math.cos(t*2+j*2.1)*(250+j*8)-35} y={cy+Math.sin(t*2.6+j*1.7)*(110+j*6)-28} w={70}><Fly size={70}/></At>)}
      <T y={top+445} x={60} w={600} size={52} color={i?C.lime:C.cream} align="left">{label}</T>
      <div style={{position:'absolute',left:560,top:top+462,width:420,height:26,borderRadius:13,background:'rgba(255,255,255,.14)'}}><div style={{width:`${clip(t/4)*(i?35:100)}%`,height:'100%',borderRadius:13,background:i?C.lime:C.coral}}/></div>
    </React.Fragment>;})}
    <T y={1650} size={34} color={C.cream} o={.7}>ILLUSTRATIVE FLICKS AND STAMPS</T>
  </>;
};

const S6=({t,cue}:P)=>{
  const aH=cue('hypothesis',4),aE=cue('low resolution',8),blur=ease((t-aE)/2.5)*11,sh=t<aE?0:Math.sin(t*7)*9*ease((t-aE)/1.5);
  return <>
    <At x={40} y={520} w={1000}><div style={{filter:`blur(${blur}px)`}}><Hero x={0} y={0} width={1000} t={t} shift={sh}/></div></At>
    <svg width={1000} height={690} style={{position:'absolute',left:40,top:520,opacity:ease((t-aE)/1.5)*.8}}><defs><pattern id="eye" width={26} height={22.5} patternUnits="userSpaceOnUse"><circle cx={13} cy={11} r={9} fill="rgba(16,28,39,.55)"/></pattern></defs><rect width={1000} height={690} fill="url(#eye)"/></svg>
    {t>=aH&&<T y={250} size={96} color={C.coral} s={1+(1-back((t-aH)/.3))*1.6} r={-6} o={1-ease((t-aH-3.2)/.4)}><span style={{border:`10px solid ${C.coral}`,borderRadius:22,padding:'6px 34px',background:'rgba(16,28,39,.78)'}}>HYPOTHESIS</span></T>}
    {t>=aE&&<T y={1380} size={58} color={C.lime} o={ease((t-aE)/.4)}>FLY'S-EYE VIEW (SIMPLIFIED)</T>}
  </>;
};

const S7=({t,cue}:P)=>{
  const aF=cue('best supported',2.5),aB=cue('bad runway',12.5),aE=cue('strongest evidence',9),ph=((t-1)%2.8+2.8)%2.8,ap=ease(ph/1.5),bp=clip((ph-1.5)/.8);
  const fx=ph<1.5?lerp(120,520,ap):lerp(520,860,ease(bp)),fy=ph<1.5?lerp(430,835,ap):lerp(835,420,ease(bp));
  return <>
    <Hero x={40} y={700} width={1000} t={t}/>
    {Array.from({length:10},(_,i)=><div key={i} style={{position:'absolute',left:170+i*72,top:868,width:22,height:22,borderRadius:'50%',background:C.lime,opacity:.25+.75*Math.max(0,Math.sin(t*9-i*.7)),boxShadow:'0 0 18px '+C.lime}}/>)}
    <At x={fx-80} y={fy-64} w={160}><Fly size={160} rot={ph<1.5?20:-20}/></At>
    <Ring x={520} y={850} p={(ph-1.5)/.6} color={C.lime}/>
    <Kw t={t} at={aF} y={200} text="FLY DEFENSE" size={134} hold={3.2}/>
    <Kw t={t} at={aB} y={1380} text="BAD RUNWAY" size={150} color={C.gold} hold={99} r={-3}/>
    {['CARO 2014','CARO 2019','KOJIMA 2019'].map((label,i)=>t<aE+i*.4?null:<At key={i} x={60+i*330} y={1640} w={320} s={back((t-aE-i*.4)/.35)}><div style={{background:C.cream,color:C.ink,fontSize:36,fontWeight:900,padding:'10px 0',borderRadius:40,textAlign:'center'}}>{label}</div></At>)}
  </>;
};

const SCENES=[S0,S1,S2,S3,S4,S5,S6,S7],CREAM=[1,4];
function Scene({index}:{index:number}){
  const frame=useCurrentFrame(),t=frame/FPS,s=plan.scenes[index],Body=SCENES[index],dark=!CREAM.includes(index);
  const cue=(phrase:string,fallback:number)=>{const norm=(v:string)=>v.toLowerCase().replace(/[^a-z0-9]/g,'');const target=phrase.split(' ').map(norm);const c=words.filter(w=>w.start>=s.start&&w.start<s.end);const k=c.findIndex((_,i)=>target.every((v,j)=>norm(c[i+j]?.text||'')===v));return k<0?fallback:c[k].start-s.start;};
  const ws=words.filter(w=>w.start>=s.start&&w.start<s.end),gt=t+s.start,gi=Math.max(0,ws.findIndex((w,i)=>gt>=w.start&&(!ws[i+1]||gt<ws[i+1].start))),g=Math.floor(gi/4)*4;
  const pop=ease(t/.45);
  return <AbsoluteFill style={{background:dark?C.ink:C.cream,color:dark?C.cream:C.ink,fontFamily:'DM Sans',overflow:'hidden'}}>
    <div style={{position:'absolute',inset:0,background:dark?'radial-gradient(ellipse at 50% 50%, #254052 0%, transparent 65%)':'radial-gradient(ellipse at 50% 50%, #fff9eb 0%, transparent 70%)'}}/>
    <div style={{position:'absolute',inset:0,backgroundImage:`radial-gradient(circle, ${dark?'rgba(255,255,255,.1)':'rgba(16,28,39,.09)'} 3px, transparent 4px)`,backgroundSize:'90px 90px',backgroundPosition:`${t*22}px ${t*15}px`}}/>
    <div style={{position:'absolute',inset:0,transform:`scale(${(1+(1-pop)*.05)*(1+t*.002)})`,transformOrigin:'50% 52%'}}><Body t={t} cue={cue}/></div>
    <div style={{position:'absolute',top:1790,left:40,right:40,textAlign:'center',whiteSpace:'nowrap',fontSize:56,fontWeight:850,letterSpacing:-2}}>{ws.slice(g,g+4).map((w,i)=><span key={g+i} style={{display:'inline-block',margin:'0 12px',color:g+i===gi?C.gold:(dark?C.cream:C.ink),opacity:g+i===gi?1:.75,transform:`scale(${g+i===gi?1+(1-ease((gt-w.start)/.2))*.35:1})`}}>{w.text}</span>)}</div>
    <Transition index={index} t={t}/>
  </AbsoluteFill>;
}

export const ZEBRA_FRAMES=Math.ceil(plan.duration*FPS);
export const ZebraVideo=()=><AbsoluteFill><style>{`@font-face{font-family:'DM Sans';src:url('${staticFile('DMSans.ttf')}')}*{box-sizing:border-box}`}</style>{plan.scenes.map((s,i)=><Sequence key={s.id} from={Math.round(s.start*FPS)} durationInFrames={Math.round(s.end*FPS)-Math.round(s.start*FPS)}><Scene index={i}/></Sequence>)}<Audio src={staticFile('zebra/narration.mp3')}/></AbsoluteFill>;
