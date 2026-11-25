import React from 'react';
import {Ball,RBox,Cyl,Cone,G,Slab,Scatter,Pine,Tree,Rock,Cloud,Act,Move} from '../kit';
// Example 2 (topic: how a bridge holds a road over a river). What to copy: the world is a DIORAMA (two ground blocks with visible soil layers, a river between them,
// trees scattered around, clouds in a gradient sky), the hero is big, and the motion is the explanation: the car crosses at the moment the narration says so.
export const GROUND=null;
export const SKY=['#7EC3F2','#E3F3FC'];
// The wide shot frames the ground block (`banks`), not 'all': clouds and far scenery would shrink it. Shots must look from where nothing stands in front of the subject.
export const SHOTS=[{focus:'banks',az:.6,el:.3},{focus:'deck',az:-.35,el:.22},{focus:'pier',az:.1,el:.08},{focus:'car',az:.15,el:.2},{focus:'banks',az:-.5,el:.6}];
const ROAD='#3B3F47',LINE='#F2C94C',CONC='#C9CCD1',CONC2='#B3B7BD',SOIL='#8B5E3C',SOIL2='#6E4A30',STONE='#8E9299',WATER='#3F9BE0';
function Banks(){
  return <G>
    {[-1,1].map(s=><G key={s} p={[s*10.5,0,0]}>
      <Slab w={11} d={26} top='#6CBF5A' layers={[{h:1.6,c:SOIL},{h:1.2,c:SOIL2},{h:1.8,c:STONE}]}/>
    </G>)}
    {[-1,1].map(sd=><G key={sd} p={[sd*10.5,0,0]}><RBox s={[9,.06,4.4]} p={[sd*1.5,.03,0]} c={ROAD} rad={.02}/>{Array.from({length:5},(_,i)=><RBox key={i} s={[.9,.03,.12]} p={[sd*(-2.4+i*1.6)+sd*1.5,.07,0]} c={LINE}/>)}</G>)}
    <RBox s={[10,.1,26]} p={[0,-3.1,0]} c={WATER} rad={.04} o={.92}/>
    {[-8,-3,2,7].map((z,i)=><Move key={i} from={[-3.5,-1.65,z]} to={[3.5,-1.65,z]} loop={2+i%2}><RBox s={[1.4,.04,.25]} c='#FFFFFF' o={.7}/></Move>)}
  </G>;
}
function Deck(){
  return <G p={[0,0,0]}>
    <RBox s={[13,.7,5]} p={[0,.35,0]} c={CONC} rad={.1}/>
    <RBox s={[13,.08,4.4]} p={[0,.74,0]} c={ROAD} rad={.02}/>
    {Array.from({length:9},(_,i)=><RBox key={i} s={[.9,.03,.12]} p={[-5.8+i*1.45,.8,0]} c={LINE}/>)}
    {[-1,1].map(s=><RBox key={s} s={[13,.45,.2]} p={[0,1,s*2.4]} c={CONC2} rad={.06}/>)}
  </G>;
}
function Pier(){
  return <G>
    <RBox s={[1.6,3.4,4.2]} p={[0,-1.45,0]} c={CONC2} rad={.12}/>
    <RBox s={[2.6,.5,4.6]} p={[0,.0,0]} c={CONC} rad={.08}/>
    {[-1.6,0,1.6].map(z=><Cyl key={z} r={.38} h={3.2} p={[0,-4.6,z]} c={STONE}/>)}
  </G>;
}
function Car(){
  return <G s={.8}>
    <RBox s={[3,.8,1.5]} p={[0,.7,0]} c='#EE6C9C' rad={.25}/>
    <RBox s={[1.6,.7,1.3]} p={[-.1,1.3,0]} c='#F58AB2' rad={.25}/>
    <RBox s={[1.1,.4,1.32]} p={[-.1,1.35,0]} c='#BFE6FA' rad={.1}/>
    {[[-1,-.75],[1,-.75],[-1,.75],[1,.75]].map(([x,z],i)=><Cyl key={i} r={.38} h={.3} p={[x,.38,z]} rot={[Math.PI/2,0,0]} c='#2B2F3A'/>)}
  </G>;
}
export function Scene(){return <>
  <group name="banks"><Banks/></group>
  <group name="deck" position={[0,0,0]}><Deck/></group>
  <group name="pier" position={[0,0,0]}><Pier/></group>
  <group name="car"><Act keys={[{t:0,p:[-13,.78,.7]},{t:.35,p:[-13,.78,.7]},{t:.8,p:[11,.78,.7]}]}><Car/></Act></group>
  <group name="nature">
    <Scatter n={9} seed={4} box={[-15.5,-12,-6,12]} avoid={[[-10.5,0,6]]} render={(i,r)=>i%3?<Pine h={4+r()*3}/>:<Tree h={4+r()*2.5}/>}/>
    <Scatter n={9} seed={9} box={[6,-12,15.5,12]} avoid={[[10.5,0,6]]} render={(i,r)=>i%3?<Pine h={4+r()*3}/>:<Tree h={4+r()*2.5}/>}/>
    <Scatter n={4} seed={2} box={[-15,-12,15,12]} avoid={[[0,0,7]]} render={(i,r)=><Rock r={.4+r()*.5}/>}/>
    <Move from={[-18,13,-8]} to={[18,13,-8]} loop={1}><Cloud s={1.6}/></Move>
    <Move from={[-6,16,-14]} to={[24,16,-14]} loop={1}><Cloud s={2.1}/></Move>
  </group>
</>;}
