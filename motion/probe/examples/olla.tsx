import React from 'react';
import {Ball,RBox,Cyl,Cone,Torus,Lathe,HalfCyl,G,Move} from '../kit';
export const GROUND='#BFE3D2';
export const SHOTS=[{focus:'all',az:.5,el:.3},{focus:'pot',az:-.15,el:.14},{focus:'lid',az:.45,el:.34},{focus:'pot',az:.3,el:.5}];
const STEEL='#C9D1DC',STEEL2='#E6EBF1',DARK='#2B2F3A',BLUE='#4DA3FF',RED='#E5333B';
const HALF=[Math.PI/2,Math.PI] as const;  // back half: the cut faces the camera
function Pot(){
  const bubbles=[[-1.4,1.3,-1.2,.2],[.4,1.9,-.9,.26],[1.5,1.1,-1.3,.18],[-.4,.7,-1.8,.22],[1.0,2.3,-.5,.16],[-1.7,2.0,-.6,.15],[.1,1.2,-.4,.14]] as const;
  const food=[[-1.6,.55,-.9],[-.6,.5,-1.5],[.7,.55,-1.0],[1.6,.5,-1.6],[-.1,.45,-.4],[1.2,.5,-.2]] as const;
  return <G>
    <Cyl r={2.95} h={.18} p={[0,.2,0]} c='#A9B3C1'/>
    <Lathe pts={[[2.7,.2],[3,.3],[3.04,3.3],[2.9,3.3],[2.88,.35]]} c={STEEL} phi0={HALF[0]} phi={HALF[1]} seg={48}/>
    <Lathe pts={[[2.88,.35],[2.9,3.3]]} c={STEEL2} phi0={HALF[0]} phi={HALF[1]} seg={48}/>
    <HalfCyl r={2.86} h={2.3} p={[0,.35,0]} c='#5AB6F0' o={.88}/>
    {food.map(([x,y,z],i)=><Ball key={i} r={.38} p={[x,y,z]} c={i%2?'#E8C36A':'#D9A441'} s={[1.1,.8,1]}/>)}
    {bubbles.map(([x,y,z,r],i)=><Move key={'b'+i} from={[x,y-.5,z]} to={[x,y+.7,z]} loop={2+i%3} bob={.03}><Ball r={r} c='#F4FAFF' o={.8}/></Move>)}
    {[-1,1].map(sd=><RBox key={sd} s={[1.3,.32,.5]} p={[sd*3.5,2.7,-.4]} c={DARK} rad={.14}/>)}
  </G>;
}
function Lid(){
  return <G p={[0,0,0]}>
    <Lathe pts={[[3.2,3.3],[3.2,3.55],[2.9,3.85],[1.4,4.1],[.001,4.15]]} c={STEEL2} phi0={HALF[0]} phi={HALF[1]} seg={48}/>
    <Torus R={3.0} r={.1} p={[0,3.32,0]} rot={[Math.PI/2,0,0]} c={DARK} arc={Math.PI} />
    <RBox s={[1.2,.4,.55]} p={[0,4.35,-.2]} c={DARK} rad={.15}/>
    <Cyl r={.28} h={.6} p={[0,4.6,-.2]} c='#6B7686'/>
    <Cyl r={.42} h={.28} p={[0,5.0,-.2]} c={DARK}/>
    {[[.15,5.5,-.2,.34],[.5,6.2,-.1,.42],[-.1,7.0,-.3,.5]].map(([x,y,z,r],i)=><Move key={i} from={[x,y,z]} to={[x+.3,y+1.2,z]} loop={3} sway={.1}><Ball r={r} c='#FFFFFF' o={.85-i*.2}/></Move>)}
    <RBox s={[.5,.5,.5]} p={[1.6,4.0,-1.2]} c='#E7A93A' rad={.12}/>
  </G>;
}
function Burner(){
  return <G>
    <RBox s={[9,.6,9]} p={[0,-.4,0]} c={DARK} rad={.18}/>
    <Torus R={2.4} r={.26} p={[0,0,0]} rot={[Math.PI/2,0,0]} c='#59606E'/>
    {Array.from({length:16},(_,i)=>{const a=i/16*Math.PI*2;return <Cone key={i} r={.2} h={.7} p={[Math.sin(a)*2.4,.35,Math.cos(a)*2.4]} c={BLUE} seg={8}/>;})}
    {Array.from({length:16},(_,i)=>{const a=(i+.5)/16*Math.PI*2;return <Cone key={'f'+i} r={.12} h={.45} p={[Math.sin(a)*2.4,.25,Math.cos(a)*2.4]} c='#BFE0FF' seg={6}/>;})}
  </G>;
}
export function Scene(){return <>
  <group name="burner" position={[0,0,0]}><Burner/></group>
  <group name="pot" position={[0,.5,0]}><Pot/></group>
  <group name="lid" position={[0,.5,0]}><Lid/></group>
</>;}
