import React from 'react';
import {Ball,RBox,Cyl,Cone,Capsule,Torus,Lathe,Tube,G,Move} from './kit';
export const GROUND='#E4F0F8';
export const SHOTS=[{focus:'all',az:.1,el:.2},{focus:'person',az:-.2,el:.14},{focus:'goggles',az:.15,el:.1},{focus:'snow_glare',az:-.3,el:.42},{focus:'carving',az:.35,el:.5},{focus:'goggles',az:-.22,el:.26}];
const BONE='#EADBB8',BONE2='#D6C298',SLIT='#3A3340',SOOT='#5A4A3E',SKIN='#C98E64',PARKA='#7FA7C9',PARKA2='#5E86AD',FUR='#EFE6D2',PANTS='#6A7FA0',HIDE='#8A6A4E',SNOW='#F2F7FB',ICE='#BFD6EA',GLOW='#FFF6C8';
// one carved bone band: closed cross-section swept around a curve (centre of curvature 0.5 behind the face)
const BAND:[number,number][]=[[.49,-.09],[.535,-.09],[.546,.03],[.535,.08],[.49,.08],[.49,-.09]];
const BROW:[number,number][]=[[.53,.06],[.57,.075],[.565,.1],[.515,.105],[.515,.06]];
const ARC0=-.78,ARC=1.56;
const onArc=(a:number,r:number)=>({x:Math.sin(a)*r,z:Math.cos(a)*r-.5});
function Goggles({strap=true}:{strap?:boolean}){
  return <G>
    <Lathe pts={BAND} p={[0,0,-.5]} c={BONE} seg={24} phi0={ARC0} phi={ARC}/>
    <Lathe pts={BROW} p={[0,0,-.5]} c={BONE2} seg={24} phi0={ARC0} phi={ARC}/>
    {[-1,1].map(sd=>{const a=sd*.3,q=onArc(a,.545);return <RBox key={'s'+sd} s={[.19,.022,.03]} p={[q.x,0,q.z]} rot={[0,a,0]} c={SLIT} rad={.008}/>;})}
    {[-1,1].map(sd=>{const a=sd*.72,q=onArc(a,.54);return <Ball key={'h'+sd} r={.022} p={[q.x,0,q.z]} c={SLIT}/>;})}
    {[-.5,-.15,.15,.5].map((a,i)=>{const q=onArc(a,.548);return <Ball key={'d'+i} r={.011} p={[q.x,-.065,q.z]} c={SOOT}/>;})}
    {strap&&<Tube pts={[[.35,0,-.1],[.44,0,-.4],[.32,0,-.76],[0,0,-.86],[-.32,0,-.76],[-.44,0,-.4],[-.35,0,-.1]]} r={.018} c={HIDE}/>}
    <Move pop={.25} spin={.6}><G p={[.32,.09,.0]}>
      <RBox s={[.1,.012,.012]} c={GLOW} e={1} rad={.004}/>
      <RBox s={[.012,.1,.012]} c={GLOW} e={1} rad={.004}/>
    </G></Move>
  </G>;
}
function Person(){
  return <G>
    {[-1,1].map(sd=><G key={sd}>
      <Capsule r={.2} h={.7} p={[sd*.25,.75,0]} c={PANTS}/>
      <RBox s={[.36,.4,.55]} p={[sd*.25,.2,.08]} c={HIDE} rad={.14}/>
      <Torus R={.2} r={.05} p={[sd*.25,.42,.02]} rot={[Math.PI/2,0,0]} c={FUR}/>
      <Capsule r={.16} h={.9} p={[sd*.68,1.95,0]} rot={[0,0,sd*.2]} c={PARKA}/>
      <Torus R={.15} r={.06} p={[sd*.78,1.45,0]} rot={[Math.PI/2,0,0]} c={FUR}/>
      <Ball r={.17} p={[sd*.8,1.32,.05]} c={HIDE}/>
    </G>)}
    <Lathe pts={[[.001,1.15],[.7,1.2],[.66,1.6],[.58,2.2],[.42,2.5],[.2,2.62],[.001,2.62]]} c={PARKA}/>
    <Torus R={.69} r={.09} p={[0,1.2,0]} rot={[Math.PI/2,0,0]} c={FUR}/>
    <RBox s={[.9,.12,.1]} p={[0,1.5,.6]} c={PARKA2} rad={.05}/>
    <RBox s={[.12,.9,.1]} p={[0,1.9,.56]} c={PARKA2} rad={.05}/>
    <Ball r={.48} p={[0,3.0,-.2]} c={PARKA}/>
    <Ball r={.36} p={[0,2.95,0]} c={SKIN}/>
    <Torus R={.42} r={.11} p={[0,2.95,.16]} c={FUR}/>
    <Ball r={.06} p={[0,2.85,.36]} c='#B57A52'/>
    <RBox s={[.14,.03,.03]} p={[0,2.74,.33]} c='#8E5A44' rad={.01}/>
    <G p={[0,3,-1]}><Move sway={.08}>
      {Array.from({length:10},(_,i)=>{const a=i/10*Math.PI*2;return <RBox key={i} s={[.12,1.1,.04]} p={[Math.sin(a)*1.25,Math.cos(a)*1.25,0]} rot={[0,0,-a]} c={GLOW} e={.9} o={.55} rad={.05}/>;})}
    </Move></G>
    <Move sway={.03}>
      <Cyl r={.04} h={4} p={[.85,2,.15]} c={HIDE}/>
      <Cone r={.07} h={.35} p={[.85,4.15,.15]} c={BONE}/>
    </Move>
  </G>;
}
function Igloo(){
  return <G>
    <Lathe pts={[[.001,4],[1.3,3.78],[2.4,3.2],[3.3,2.25],[3.85,1.1],[4,0]]} c={SNOW} seg={40}/>
    {[1,2,3].map(y=><Torus key={y} R={Math.sqrt(16-y*y)} r={.05} p={[0,y,0]} rot={[Math.PI/2,0,0]} c={ICE}/>)}
    {[0,1,2,3,4,5].map(i=>{const a=i/6*Math.PI*2+.3;return <RBox key={i} s={[.06,.9,.06]} p={[Math.sin(a)*3.75,1.5,Math.cos(a)*3.75]} rot={[0,a,0]} c={ICE} rad={.02}/>;})}
    <Cyl r={1.2} h={2.4} p={[0,.3,4.2]} rot={[Math.PI/2,0,0]} c={SNOW}/>
    <Ball r={.8} s={[1,1,.2]} p={[0,.6,5.4]} c='#3D5875'/>
    <RBox s={[.8,.6,.1]} p={[2.2,2.4,2.4]} rot={[0,.75,0]} c='#FFE3A8' e={.6} o={.85} rad={.05}/>
    {[0,1,2].map(i=><Move key={i} from={[0,4,0]} to={[.6,6,0]} loop={2+i}><Ball r={.35} c='#FFFFFF' o={.6}/></Move>)}
  </G>;
}
function Sun(){
  return <G>
    <Ball r={1.6} c='#FFF1B8' e={1}/>
    <Ball r={2.4} c='#FFF6D6' e={.6} o={.3}/>
    <Move spin={.15}>{[0,1,2,3,4,5,6,7].map(i=>{const a=i/8*Math.PI*2;return <RBox key={i} s={[.25,1.2,.1]} p={[Math.sin(a)*3.2,Math.cos(a)*3.2,0]} rot={[0,0,-a]} c='#FFE8A0' e={.8} o={.6} rad={.1}/>;})}</Move>
  </G>;
}
function Glare(){
  const sp=[[-1.2,.1,.6],[-.4,.08,1.4],[.6,.1,.4],[1.6,.08,1.3],[2.9,.1,.2],[3.6,.08,1.6],[0,.1,2.2],[1.2,.08,-.6],[-.6,.1,-.5],[2.4,.1,2.4],[-3.4,.1,1.8],[3.8,.1,-.6]] as const;
  return <G>
    <Cone r={1.6} h={4.6} p={[.3,2.3,.4]} c={GLOW} e={.6} o={.16} seg={20}/>
    <Torus R={1.3} r={.05} p={[.3,.03,.4]} rot={[Math.PI/2,0,0]} c={GLOW} e={.8} o={.6}/>
    {sp.map(([x,y,z],i)=><Move key={i} from={[x,y,z]} to={[x,y+.15,z]} loop={3+i%3}><Ball r={.12} s={[1,.4,1]} c='#FFFDF0' e={1}/></Move>)}
  </G>;
}
function Ridges(){
  const r=[[-10,2.2,1.4],[-6,3,1.8],[-1.5,2.4,1.5],[3,3.4,2],[8,2.6,1.6],[11,2,1.3]] as const;
  return <G>
    {r.map(([x,h,w],i)=><Cone key={i} r={w} h={h} p={[x,h/2,i%2?-.6:0]} c={i%2?ICE:'#D3E4F2'} seg={6}/>)}
    {[-8,-3,2,7].map((x,i)=><Ball key={'d'+i} r={2} s={[1.6,.35,1]} p={[x,0,2]} c={SNOW}/>)}
  </G>;
}
function Backdrop(){
  return <G>
    <Lathe pts={[[30,-.1],[30,24]]} c='#CFE4F4' seg={48} phi0={Math.PI/2} phi={Math.PI}/>
    <Lathe pts={[[29.8,-.1],[29.8,5]]} c='#E2EFF8' seg={48} phi0={Math.PI/2} phi={Math.PI}/>
    {[-26,-20,-14,14,20,26].map((x,i)=><Cone key={i} r={3} h={4+i%3} p={[x,(4+i%3)/2,-22]} c={i%2?ICE:'#D3E4F2'} seg={6}/>)}
    {[-22,-14,14,22].map((x,i)=><Ball key={'m'+i} r={3} s={[2,.4,1.4]} p={[x,0,-8]} c={SNOW}/>)}
  </G>;
}
function Carving(){
  return <G>
    <RBox s={[3.4,1.1,1.8]} p={[0,.55,0]} c={SNOW} rad={.12}/>
    <RBox s={[3.2,.08,1.5]} p={[0,1.14,0]} c={HIDE} rad={.03}/>
    <G p={[-.4,1.66,.1]} rot={[-1.25,0,0]} s={3}><Goggles strap={false}/></G>
    <Tube pts={[[.7,1.25,-.55],[1.05,1.3,-.5],[1.45,1.4,-.4]]} r={.07} c={BONE2}/>
    <Move sway={.12}>
      <G p={[1.25,1.42,.35]}>
        <Cyl r={.22} h={.025} rot={[Math.PI/2,0,0]} c='#A9B6C4'/>
        <RBox s={[.36,.09,.07]} p={[0,.21,0]} c={HIDE} rad={.03}/>
      </G>
    </Move>
    {[[.5,.2],[.7,.35],[.6,.5]].map(([x,z],i)=><Move key={i} from={[x,1.35,z]} to={[x+.3,1.2,z+.3]} loop={2+i} pop={.5}><RBox s={[.1,.025,.05]} c={BONE} rad={.008}/></Move>)}
  </G>;
}
export function Scene(){return <>
  <group position={[0,0,0]}><Backdrop/></group>
  <group name="ridges" position={[0,0,-15]}><Ridges/></group>
  <group name="sun" position={[7,10,-16]}><Sun/></group>
  <group name="igloo" position={[-7,0,-7]} rotation={[0,.5,0]}><Igloo/></group>
  <group name="snow_glare" position={[2.5,0,1.2]}><Glare/></group>
  <group name="person" position={[0,0,0]}><Move bob={.015}><Person/></Move></group>
  <group name="goggles" position={[0,2.97,.4]}><Move bob={.015}><Goggles/></Move></group>
  <group name="carving" position={[5,0,.5]} rotation={[0,-.4,0]}><Carving/></group>
</>;}
