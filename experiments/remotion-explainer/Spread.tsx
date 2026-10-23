import React from 'react';

const ink = '#182c36';
const warm = '#f47752';
const clamp = (n:number) => Math.max(0, Math.min(1,n));

// A schematic: energy is shown by color and travelling pulses, never as a
// numerical temperature scale. Both materials start with the same cool color.
const Material: React.FC<{x:number;y:number;w:number;h:number;t:number;wood:boolean;hot:boolean}> = ({x,y,w,h,t,wood,hot}) => {
  const p = clamp(t / 4);
  const reach = (wood ? .12 : .88) * p;
  const cols = 12;
  const rows = 6;
  const contact = y+h*.5;
  const cooling = p*(wood?.12:.7);
  const skinColor=`rgb(${Math.round(239-80*cooling)},${Math.round(146+40*cooling)},${Math.round(125+90*cooling)})`;
  return <g>
    <rect x={x} y={y} width={w} height={h} rx={22} fill={wood?'#e5c697':'#adcbd3'} stroke={ink} strokeWidth={7}/>
    {wood && <g fill="none" stroke="#bd935c" strokeWidth={4} opacity={.65}>
      {[.2,.43,.7,.86].map((v,i)=><path key={i} d={`M${x+22} ${y+h*v} Q${x+w*.35} ${y+h*v-26} ${x+w*.58} ${y+h*v+9} T${x+w-22} ${y+h*v-5}`}/>)}
    </g>}
    {Array.from({length:cols},(_,c)=>Array.from({length:rows},(_,r)=>{
      const nx=(c+.5)/cols;
      const ny=(r+.5)/rows;
      const distance=Math.sqrt(nx*nx+Math.pow((ny-.5)*.42,2));
      const heated=clamp((reach-distance)*12);
      return <g key={`${c}-${r}`}>
        <circle cx={x+nx*w} cy={y+ny*h} r={9} fill={wood?'#bd935c':'#6595a5'} opacity={.65}/>
        <circle cx={x+nx*w} cy={y+ny*h} r={9+heated*3} fill={hot?'#ef6549':warm} opacity={heated}/>
      </g>;
    }))}
    {/* Flat skin cross-section presses against the left edge. */}
    <path d={`M${x-116} ${contact-92} H${x-39} Q${x-4} ${contact-92} ${x-4} ${contact-57} V${contact+57} Q${x-4} ${contact+92} ${x-39} ${contact+92} H${x-116}`} fill={skinColor} stroke={ink} strokeWidth={7} strokeLinejoin="round"/>
    <path d={`M${x-37} ${contact-64} V${contact+64}`} stroke="#ffc7a4" strokeWidth={10} strokeLinecap="round"/>
    {p>0 && [0,1,2].map(i=>{
      const pulse=((Math.max(0,t)* (wood?.18:.65)+i/3)%1);
      const xx=x+15+pulse*w*(wood?.14:.8)*p;
      return <g key={i} opacity={Math.sin(pulse*Math.PI)*.85*p} stroke={warm} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" fill="none">
        <path d={`M${xx-10} ${contact} h27 m-12 -12 12 12 -12 12`}/>
      </g>;
    })}
  </g>;
};

export const Spread: React.FC<{t:number;compare?:boolean;wood?:boolean;hot?:boolean}> = ({t,compare=false,wood=false,hot=false}) => <svg width="100%" height="100%" viewBox="0 0 1080 1920" xmlns="http://www.w3.org/2000/svg">
  {compare ? <>
    <text x={320} y={610} textAnchor="middle" fill="#5399aa" fontFamily="DM Sans" fontSize={44} fontWeight={900}>METAL</text>
    <text x={800} y={610} textAnchor="middle" fill="#b37f36" fontFamily="DM Sans" fontSize={44} fontWeight={900}>WOOD</text>
    <Material x={195} y={700} w={295} h={580} t={t} wood={false} hot={hot}/>
    <Material x={675} y={700} w={295} h={580} t={t} wood={true} hot={hot}/>
    <path d="M540 700 V1280" stroke={ink} strokeWidth={3} opacity={.18} strokeDasharray="10 16"/>
  </> : <Material x={300} y={740} w={650} h={520} t={t} wood={wood} hot={hot}/>}
</svg>;
