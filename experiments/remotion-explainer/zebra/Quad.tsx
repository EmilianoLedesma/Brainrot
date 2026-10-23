import React,{useId} from 'react';
import {useCurrentFrame} from 'remotion';

// Original flat-vector four-legged animal (zebra, horse in a coat, painted cow) and a biting fly.
// viewBox 640x440; body centre (300,190), rump (130,150), muzzle (608,95).
const OUT='#0a1219';
export type QuadProps={fill?:string,stripe?:string,stripes?:boolean,progress?:number,mane?:string,tail?:number,shift?:number,width?:number};

export function Quad({fill='#f6f1e4',stripe='#14202b',stripes=true,progress=1,mane='#14202b',tail=0,shift=0,width=640}:QuadProps){
  const id=useId().replace(/:/g,'');
  const shapes=<>
    <ellipse cx={300} cy={190} rx={180} ry={85}/>
    <path d="M425 150C465 112 497 74 520 38L578 70C562 112 538 160 502 218Z"/>
    <path d="M505 40C530 14 576 24 612 60C634 82 626 108 600 114C574 120 548 100 528 86Z"/>
    <path d="M522 36L516 -2L545 26Z"/>
    {[[400,230],[372,238],[130,230],[162,238]].map(([x,y],i)=><rect key={i} x={x} y={y} width={38} height={176} rx={14}/>)}
  </>;
  return <svg width={width} height={width*440/640} viewBox="-10 -10 660 450" style={{overflow:'visible'}}>
    <defs><clipPath id={id}>{shapes}</clipPath><clipPath id={id+'r'}><rect x={-10} y={-20} width={20+progress*680} height={460}/></clipPath></defs>
    <path d={`M128 150C92 172 86 224 102 276`} stroke={mane} strokeWidth={11} strokeLinecap="round" fill="none" transform={`rotate(${tail} 128 150)`}/>
    <g fill={OUT} stroke={OUT} strokeWidth={14} strokeLinejoin="round">{shapes}</g>
    <g fill={fill}>{shapes}</g>
    {stripes&&<g clipPath={`url(#${id})`}><g clipPath={`url(#${id}r)`} stroke={stripe} fill="none" strokeLinecap="round">
      {Array.from({length:12},(_,i)=>{const x=125+i*31+shift;return <path key={'b'+i} d={`M${x} 95Q${x+14} 190 ${x-8} 290`} strokeWidth={15}/>;})}
      {Array.from({length:6},(_,i)=><path key={'n'+i} d={`M${395+i*14+shift} ${200-i*26}L${490+i*14+shift} ${150-i*26}`} strokeWidth={12}/>)}
      {Array.from({length:5},(_,i)=><path key={'h'+i} d={`M${536+i*15+shift} 20L${528+i*13+shift} 100`} strokeWidth={7}/>)}
      {Array.from({length:6},(_,i)=><path key={'l'+i} d={`M100 ${295+i*24}H470`} strokeWidth={11}/>)}
      <ellipse cx={606} cy={96} rx={24} ry={18} fill={stripe} stroke="none"/>
    </g></g>}
    <path d="M432 140C462 100 492 62 516 30" stroke={mane} strokeWidth={20} strokeLinecap="round" fill="none"/>
    {[[400,392],[372,400],[130,392],[162,400]].map(([x,y],i)=><rect key={i} x={x-1} y={y} width={40} height={20} rx={7} fill={OUT}/>)}
  </svg>;
}

export function Fly({size=120,rot=0}:{size?:number,rot?:number}){
  const f=Math.sin(useCurrentFrame()*2.1);
  return <svg width={size} height={size*.8} viewBox="0 0 120 96" style={{overflow:'visible',transform:`rotate(${rot}deg)`}}>
    <ellipse cx={58} cy={30} rx={34} ry={11} fill="#d7ecff" opacity={.6} transform={`rotate(${-24+f*22} 70 46)`}/>
    <ellipse cx={72} cy={26} rx={30} ry={10} fill="#d7ecff" opacity={.5} transform={`rotate(${-8+f*18} 76 44)`}/>
    <path d="M40 66l-14 18M58 68l-6 22M74 66l8 22" stroke="#1d2730" strokeWidth={4} strokeLinecap="round"/>
    <ellipse cx={50} cy={52} rx={34} ry={15} fill="#2b3640"/><path d="M28 50h40M30 56h36" stroke="#4b5b69" strokeWidth={3}/>
    <circle cx={86} cy={48} r={15} fill="#3a4753"/><circle cx={102} cy={46} r={11} fill="#c23b32"/><circle cx={105} cy={43} r={3.5} fill="#ffd0c8"/>
  </svg>;
}
