import React from 'react';

// Reusable on-screen devices chosen per scene by brainrot/motion.py (see skills/motion-graphics).
// Each one appears on a spoken cue (k = seconds since the cue) and stays until the scene ends.
const C={ink:'#101c27',cream:'#f5ead5',coral:'#ff765f',cyan:'#68d4e7',gold:'#ffd36b',lime:'#c8f560'};
const clip=(v:number)=>Math.max(0,Math.min(1,v));
const ease=(p:number)=>{p=clip(p);return p*p*(3-2*p);};
const back=(p:number)=>{p=clip(p);return 1+2.7*Math.pow(p-1,3)+1.7*Math.pow(p-1,2);};

export type DeviceT={kind:'stat'|'compare'|'checklist'|'steps'|'stamp'|'alert',title:string,big:string,items:string[],values:number[],highlight:number,at:number};
type P={d:DeviceT,k:number,dark:boolean,accent:string};

const panel=(dark:boolean,top:number,height:number,k:number):React.CSSProperties=>({position:'absolute',left:70,right:70,top,height,borderRadius:44,background:dark?'rgba(255,255,255,.07)':'rgba(16,28,39,.07)',border:`4px solid ${dark?'rgba(255,255,255,.22)':'rgba(16,28,39,.2)'}`,transform:`scale(${.85+.15*ease(k/.3)})`,opacity:ease(k/.25),padding:'38px 50px',overflow:'hidden'});
const label=(dark:boolean):React.CSSProperties=>({fontSize:50,fontWeight:850,letterSpacing:-1.5,lineHeight:1.05,color:dark?C.cream:C.ink});

function Stat({d,k,dark,accent}:P){
  const m=d.big.match(/^([^0-9]*)([0-9][0-9,.]*)(.*)$/),n=m?parseFloat(m[2].replace(/,/g,'')):NaN;
  const shown=m&&isFinite(n)?m[1]+(m[2].includes('.')?(n*ease(k/1.1)).toFixed(1):Math.round(n*ease(k/1.1)).toLocaleString('en-US').replace(/,/g,m[2].includes(',')?',':''))+m[3]:d.big;
  return <div style={{...panel(dark,1130,500,k),textAlign:'center'}}>
    <div style={{fontSize:d.big.length>6?170:230,fontWeight:900,letterSpacing:-8,lineHeight:1,color:accent,transform:`scale(${back((k-.1)/.4)})`}}>{shown}</div>
    <div style={{...label(dark),marginTop:24,opacity:ease((k-.4)/.3)}}>{d.title}</div>
  </div>;
}
function Compare({d,k,dark,accent}:P){
  const [a,b]=d.values,hi=Math.max(a,b);
  return <div style={panel(dark,1080,600,k)}>
    <div style={{display:'flex',gap:60,height:'100%',alignItems:'flex-end',justifyContent:'center'}}>
      {[a,b].map((v,i)=><div key={i} style={{flex:1,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'flex-end',height:'100%'}}>
        <div style={{width:'100%',height:`${(v/hi)*360*ease((k-.2-i*.25)/.7)}px`,borderRadius:26,background:v===hi?accent:(dark?'rgba(245,234,213,.45)':'rgba(16,28,39,.35)')}}/>
        <div style={{...label(dark),marginTop:22,textAlign:'center',fontSize:46}}>{d.items[i]}</div>
      </div>)}
    </div>
  </div>;
}
function List({d,k,dark,accent,steps}:P&{steps?:boolean}){
  const n=d.items.length,h=130*n+76;
  return <div style={panel(dark,1130,h,k)}>{d.items.map((it,i)=>{const e=k-.15-i*.4;if(e<0)return null;const hit=!steps&&d.highlight===i,out=!steps&&d.highlight>=0&&!hit;
    return <div key={i} style={{display:'flex',alignItems:'center',gap:26,height:130,transform:`translateX(${(1-ease(e/.3))*-120}px)`,opacity:ease(e/.25)}}>
      <div style={{flex:'none',width:78,height:78,borderRadius:steps?'50%':20,background:hit?accent:out?'transparent':(dark?'rgba(255,255,255,.14)':'rgba(16,28,39,.12)'),border:out?`4px solid ${C.coral}`:'none',color:hit?C.ink:out?C.coral:(dark?C.cream:C.ink),fontSize:50,fontWeight:900,display:'grid',placeItems:'center'}}>{steps?i+1:hit?'✓':out?'✕':'•'}</div>
      <div style={{...label(dark),opacity:out?.5:1,textDecoration:out?'line-through':'none',textDecorationThickness:5}}>{it}</div>
      {steps&&i<n-1&&<div style={{marginLeft:'auto',fontSize:56,color:accent,fontWeight:900}}>↓</div>}
    </div>;})}</div>;
}
function Stamp({d,k}:P){const p=back(k/.3);
  return <div style={{position:'absolute',left:70,right:70,top:1230,textAlign:'center',transform:`rotate(-6deg) scale(${1+(1-p)*1.8}) translate(${k<.45?Math.sin(k*90)*5:0}px,0)`}}>
    <span style={{display:'inline-block',color:C.coral,border:`10px solid ${C.coral}`,borderRadius:22,padding:'10px 34px',fontSize:d.title.length>14?64:88,fontWeight:900,letterSpacing:-2,background:'rgba(16,28,39,.82)',whiteSpace:'nowrap'}}>{d.title.toUpperCase()}</span></div>;
}
function Alert({d,k}:P){
  return <div style={{position:'absolute',left:110,right:110,top:300,transform:`translateY(${(1-ease(k/.4))*-340}px)`,display:'flex',alignItems:'center',gap:26,padding:'24px 32px',borderRadius:30,background:'rgba(16,28,39,.94)',border:`5px solid ${C.gold}`,boxShadow:'0 14px 0 rgba(0,0,0,.28)'}}>
    <div style={{flex:'none',width:66,height:66,borderRadius:'50%',background:C.gold,color:C.ink,fontSize:48,fontWeight:900,display:'grid',placeItems:'center'}}>!</div>
    <div style={{color:C.cream,fontSize:46,fontWeight:850,letterSpacing:-1.2,lineHeight:1.05}}>{d.title}</div></div>;
}

export function Device(p:P){
  if(p.k<0)return null;
  return p.d.kind==='stat'?<Stat {...p}/>:p.d.kind==='compare'?<Compare {...p}/>:p.d.kind==='checklist'?<List {...p}/>:p.d.kind==='steps'?<List {...p} steps/>:p.d.kind==='stamp'?<Stamp {...p}/>:<Alert {...p}/>;
}
