import React from 'react';

// Narration-timed pop-ups (chat bubbles, alerts, stamps) and varied scene transitions.
// Texts only restate the narration of their scene; `at` is a spoken phrase from words.json.
const C={ink:'#101c27',cream:'#f5ead5',coral:'#ff765f',cyan:'#68d4e7',gold:'#ffd36b'};
const clip=(v:number)=>Math.max(0,Math.min(1,v));
const ease=(p:number)=>{p=clip(p);return p*p*(3-2*p);};
const back=(p:number)=>{p=clip(p);return 1+2.7*Math.pow(p-1,3)+1.7*Math.pow(p-1,2);};

type Item={kind:'bubble'|'alert'|'stamp';text:string;at:string;fb:number;x?:number;y?:number;flip?:boolean;hot?:boolean};
const ITEMS:Item[][]=[
 [{kind:'bubble',text:'The metal feels colder!',at:'the metal feels',fb:4,x:60,y:1340},{kind:'alert',text:'Same room, same temperature',at:'same temperature',fb:9,y:390},{kind:'bubble',text:'What is my hand telling me?',at:'hand actually',fb:12,x:380,y:1340,flip:true}],
 [{kind:'alert',text:'Both read 22°C',at:'twenty two',fb:6,y:390},{kind:'stamp',text:'NOT THE SAME THING',at:'does not describe',fb:9,y:1270}],
 [{kind:'alert',text:'Warm skin → cooler material',at:'energy flows',fb:5,y:390},{kind:'bubble',text:'Same direction!',at:'the direction is',fb:9,x:60,y:1340}],
 [{kind:'alert',text:'More energy leaves your skin',at:'allowing more',fb:4,y:390},{kind:'bubble',text:'Brr, cold!',at:'feels cold',fb:10,x:60,y:1340}],
 [{kind:'alert',text:'Slower transfer from skin',at:'less quickly',fb:9,y:390},{kind:'bubble',text:'This feels warmer',at:'feels warmer',fb:12,x:60,y:1340}],
 [{kind:'bubble',text:'Same reading, different feel',at:'two matching',fb:10,x:60,y:1340},{kind:'alert',text:'22°C and 22°C',at:'two matching',fb:10,y:390}],
 [{kind:'alert',text:'Hotter than skin',at:'somewhere hotter',fb:2,y:390,hot:true},{kind:'stamp',text:'DIRECTION REVERSES',at:'direction reverses',fb:4,y:1270},{kind:'bubble',text:'Ouch, hot!',at:'feel hotter',fb:9,x:60,y:1340,flip:true}],
 [{kind:'alert',text:'Ice test: illustrative',at:'place matching',fb:3,y:390},{kind:'bubble',text:'Metal melts it faster',at:'typically melts',fb:9,x:60,y:1340}],
 [{kind:'stamp',text:'NOT A CONTRADICTION',at:'not a contradiction',fb:3,y:1270},{kind:'alert',text:'Colder ice gains energy',at:'colder ice gains',fb:8,y:390}],
 [{kind:'alert',text:'Same temperature, different speed',at:'does not',fb:6,y:390},{kind:'bubble',text:'It is an exchange!',at:'not giving',fb:10,x:60,y:1340}]
];

const Bubble=({it,k}:{it:Item,k:number})=><div style={{position:'absolute',left:it.x??60,top:it.y??1340,transform:`scale(${back(k/.4)})`,transformOrigin:it.flip?'85% 100%':'15% 100%'}}><div style={{background:'#fff',color:C.ink,fontSize:50,fontWeight:850,letterSpacing:-1.5,lineHeight:1.05,padding:'26px 36px',borderRadius:44,maxWidth:640,boxShadow:'0 14px 0 rgba(0,0,0,.28)'}}>{it.text}</div><div style={{position:'absolute',bottom:-22,[it.flip?'right':'left']:70,width:44,height:44,background:'#fff',transform:'rotate(45deg)',borderRadius:6}}/></div>;
const Alert=({it,k}:{it:Item,k:number})=>{const c=it.hot?C.coral:C.gold;return <div style={{position:'absolute',left:110,right:110,top:it.y??390,transform:`translateY(${(1-ease(k/.4))*-340}px)`,display:'flex',alignItems:'center',gap:26,padding:'24px 32px',borderRadius:30,background:'rgba(16,28,39,.92)',border:`5px solid ${c}`,boxShadow:'0 14px 0 rgba(0,0,0,.28)'}}><div style={{flex:'none',width:66,height:66,borderRadius:'50%',background:c,color:C.ink,fontSize:48,fontWeight:900,display:'grid',placeItems:'center'}}>!</div><div style={{color:C.cream,fontSize:48,fontWeight:850,letterSpacing:-1.2,lineHeight:1.05}}>{it.text}</div></div>;};
const Stamp=({it,k}:{it:Item,k:number})=>{const p=back(k/.3);return <div style={{position:'absolute',left:70,right:70,top:it.y??1270,textAlign:'center',transform:`rotate(-6deg) scale(${1+(1-p)*1.8}) translate(${k<.45?Math.sin(k*90)*5:0}px,0)`}}><span style={{display:'inline-block',color:C.coral,border:`10px solid ${C.coral}`,borderRadius:22,padding:'10px 34px',fontSize:76,fontWeight:900,letterSpacing:-2,background:'rgba(16,28,39,.78)'}}>{it.text}</span></div>;};

export function Overlays({index,t,cue}:{index:number,t:number,cue:(phrase:string,fallback:number)=>number}){
  return <>{(ITEMS[index]||[]).map((it,i)=>{const k=t-cue(it.at,it.fb);if(k<0||k>3.1)return null;const out=1-clip((k-2.8)/.3);
    return <div key={i} style={{position:'absolute',inset:0,opacity:out}}>{it.kind==='bubble'?<Bubble it={it} k={k}/>:it.kind==='alert'?<Alert it={it} k={k}/>:<Stamp it={it} k={k}/>}</div>;})}</>;
}

// Four transition styles cycle by scene: side wipe, vertical wipe, iris, staggered bars.
const TC=[C.coral,C.cyan,C.gold,C.cream];
export function Transition({index,t}:{index:number,t:number}){
  const w=ease(t/.45);if(index===0||w>=1)return null;const col=TC[index%4],v=index%4;
  if(v===0)return <div style={{position:'absolute',inset:0,background:col,transform:`translateX(${w*105}%)`}}/>;
  if(v===1)return <div style={{position:'absolute',inset:0,background:col,transform:`translateY(${-w*105}%)`}}/>;
  if(v===2)return <div style={{position:'absolute',inset:0,background:col,clipPath:`circle(${(1-w)*80}% at 50% 50%)`}}/>;
  return <>{Array.from({length:5},(_,i)=><div key={i} style={{position:'absolute',left:0,right:0,top:i*384,height:385,background:col,transform:`translateX(${(i%2?-1:1)*ease(t/.45-i*.08)*105}%)`}}/>)}</>;
}
