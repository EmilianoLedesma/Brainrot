import React from 'react';

// Four scene-transition styles cycle by scene index: side wipe, vertical wipe, iris, staggered bars.
const C={coral:'#ff765f',cyan:'#68d4e7',gold:'#ffd36b',cream:'#f5ead5'};
const ease=(p:number)=>{p=Math.max(0,Math.min(1,p));return p*p*(3-2*p);};
const TC=[C.coral,C.cyan,C.gold,C.cream];
export function Transition({index,t}:{index:number,t:number}){
  const w=ease(t/.45);if(index===0||w>=1)return null;const col=TC[index%4],v=index%4;
  if(v===0)return <div style={{position:'absolute',inset:0,background:col,transform:`translateX(${w*105}%)`}}/>;
  if(v===1)return <div style={{position:'absolute',inset:0,background:col,transform:`translateY(${-w*105}%)`}}/>;
  if(v===2)return <div style={{position:'absolute',inset:0,background:col,clipPath:`circle(${(1-w)*80}% at 50% 50%)`}}/>;
  return <>{Array.from({length:5},(_,i)=><div key={i} style={{position:'absolute',left:0,right:0,top:i*384,height:385,background:col,transform:`translateX(${(i%2?-1:1)*ease(t/.45-i*.08)*105}%)`}}/>)}</>;
}
