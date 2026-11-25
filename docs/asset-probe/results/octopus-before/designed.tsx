import React from 'react';
import {Ball,RBox,Cyl,Cone,Torus,Lathe,Tube,G,Move} from './kit';
export const GROUND='#EAD9B8';
export const SHOTS=[{focus:'all',az:.15,el:.2},{focus:'octopus',az:-.2,el:.14},{focus:'head',az:.3,el:.1},{focus:'octopus',az:.55,el:.42},{focus:'skin',az:-.35,el:.26},{focus:'octopus',az:-.45,el:.2}];
type P3=[number,number,number];
const OCT='#E8735A',OCT2='#F29A7E',DEEP='#B8483F',SUCK='#FFD3C4',ROCK='#B9A58C',ROCK2='#9C8B78',CAMO='#A89880',CAMO2='#C2B39C',DARK='#3A2A30',SEA='#6FBF8E',SEA2='#4FA578',BUB='#E8F7FF';
const CAMO_T=.5;
const BODY:[number,number][]=[[.001,1.2],[1.0,1.3],[1.25,1.8],[1.2,2.6],[1.3,3.2],[1.38,3.8],[1.2,4.5],[.75,5.0],[.001,5.2]];
const BODY_C:[number,number][]=BODY.map(([r,y])=>[r===.001?.001:r*1.04,y+(r===.001&&y>2?.03:0)] as [number,number]);
function Arm({a,i}:{a:number,i:number}){
  const c=Math.cos(a),s=Math.sin(a);
  const pt=(r:number,y:number):P3=>[c*r,y,s*r];
  const pts:P3[]=[pt(.5,1.6),pt(1.3,1.0),pt(2.1,.62),pt(2.9,.5),pt(3.5,.62)];
  const tipBase=pt(3.5,.62);
  const tip:P3[]=[[0,0,0],[c*.45,.25,s*.45],[c*.3,.6,s*.3]];
  const suck:[number,number][]=[[1.6,.85],[2.2,.65],[2.8,.52]];
  const bumps:[number,number][]=[[1.5,1.15],[2.2,.86],[2.9,.74]];
  return <G>
    <Tube pts={pts} r={.26-(i%2)*.03} c={i%2?OCT:OCT2}/>
    {suck.map(([r,y],k)=><Ball key={k} r={.11-k*.02} p={[c*r-s*.2,y,s*r+c*.2]} c={SUCK} s={[1,.6,1]}/>)}
    <Move pop={CAMO_T}><G>
      <Tube pts={pts} r={.29-(i%2)*.03} c={CAMO}/>
      {bumps.map(([r,y],k)=><Ball key={k} r={.1} p={pt(r,y)} c={k%2?CAMO2:ROCK2}/>)}
    </G></Move>
    <Move from={tipBase} sway={.12+(i%3)*.04}><G>
      <Tube pts={tip} r={.13} c={OCT}/>
      <Move pop={CAMO_T}><Tube pts={tip} r={.15} c={CAMO}/></Move>
    </G></Move>
  </G>;
}
function Eyes(){
  return <G>
    {[-1,1].map(sd=><G key={sd} p={[sd*1.05,2.3,.55]}>
      <Ball r={.42} s={[1,1,.8]} c={OCT}/>
      <Move pop={CAMO_T}><Ball r={.44} s={[1,1,.8]} p={[0,0,-.06]} c={CAMO}/></Move>
      <Ball r={.32} p={[0,0,.12]} c='#FFF0C8'/>
      <RBox s={[.36,.09,.06]} p={[0,0,.43]} c={DARK} rad={.03}/>
      <Move sway={.15}><G>
        <Ball r={.36} s={[1.05,.45,.9]} p={[0,.24,.06]} c={DEEP}/>
        <Move pop={CAMO_T}><Ball r={.38} s={[1.05,.47,.92]} p={[0,.24,.06]} c={ROCK2}/></Move>
      </G></Move>
      <Cone r={.08} h={.3} p={[sd*.1,.45,0]} c={OCT2}/>
      <Move pop={CAMO_T}><Cone r={.1} h={.42} p={[sd*.1,.5,0]} c={CAMO2}/></Move>
    </G>)}
  </G>;
}
function Head(){
  const spots:P3[]=[[.5,3.6,1.22],[-.6,3.2,1.15],[.2,4.3,1.08],[-.4,2.9,1.1],[.9,2.8,.85]];
  const pap:[number,number,number][]=[[-1.1,2.9,1.3],[-.4,3.3,1.38],[.3,3.0,1.36],[1.0,3.4,1.4],[-.8,3.9,1.44],[.1,4.0,1.42],[.8,4.1,1.36],[-.3,4.6,1.2],[.5,4.6,1.18],[1.4,2.8,1.3],[-1.5,3.6,1.44],[0,3.5,1.42]];
  return <Move bob={.06}><G>
    <Lathe pts={BODY} c={OCT}/>
    {spots.map((p,i)=><Ball key={i} r={.22} s={[1,1,.4]} p={p} c={DEEP}/>)}
    <Cyl r={.18} r2={.24} h={.6} p={[1.2,1.75,.3]} rot={[0,0,1.2]} c={DEEP}/>
    <Eyes/>
    <Move pop={CAMO_T}><G>
      <Lathe pts={BODY_C} c={CAMO}/>
      <Cyl r={.2} r2={.26} h={.62} p={[1.2,1.75,.3]} rot={[0,0,1.2]} c={ROCK2}/>
      {spots.map((p,i)=><Ball key={i} r={.26} s={[1,1,.45]} p={[p[0]*1.04,p[1],p[2]*1.04]} c={ROCK2}/>)}
    </G></Move>
    {pap.map(([a,y,R],i)=><Move key={'p'+i} pop={CAMO_T+.01+(i%5)*.012}>
      {i%2?<Cone r={.13} h={.34} p={[Math.sin(a)*R,y,Math.cos(a)*R]} c={ROCK2}/>:<Ball r={.16} p={[Math.sin(a)*R,y,Math.cos(a)*R]} c={CAMO2}/>}
    </Move>)}
  </G></Move>;
}
function Octopus(){
  const arms=Array.from({length:8},(_,i)=>i/8*Math.PI*2+Math.PI/8);
  return <G>
    <Ball r={3.4} s={[1,.2,.9]} p={[0,.05,0]} c={ROCK2}/>
    <Ball r={1.2} s={[1,.5,1]} p={[2.2,.4,-1.6]} c={ROCK}/>
    {arms.map((a,i)=><Arm key={i} a={a} i={i}/>)}
    <Lathe pts={[[.001,1.0],[1.3,1.15],[1.0,1.7],[.5,1.95]]} c={DEEP}/>
    <Move pop={CAMO_T}><Lathe pts={[[.001,1.0],[1.36,1.15],[1.05,1.72],[.5,1.98]]} c={ROCK2}/></Move>
  </G>;
}
function Skin(){
  const cells:[number,number,string][]=[[-.8,.6,'#E2453A'],[.6,.9,'#F2B33D'],[0,-.1,'#8A4B2F'],[-.9,-.8,'#F2B33D'],[.9,-.6,'#E2453A'],[.1,-1.2,'#8A4B2F']];
  return <G>
    <Cyl r={.18} h={2.2} p={[0,1.1,0]} c={ROCK2}/>
    <Cyl r={.7} h={.2} p={[0,.1,0]} c={ROCK2}/>
    <G p={[0,3.9,0]}>
      <Cyl r={1.9} h={.35} rot={[Math.PI/2,0,0]} c={SUCK}/>
      <Torus R={1.95} r={.14} c={DEEP}/>
      {cells.map(([x,y,c],i)=><G key={i} p={[x,y,.2]}>
        {[0,1,2,3,4,5].map(k=><Cyl key={k} r={.03} h={.75} p={[Math.cos(k)*.3,Math.sin(k)*.3,0]} rot={[0,0,k+Math.PI/2]} c={OCT2}/>)}
        <Ball r={.12} s={[1,1,.4]} c={c}/>
        <Move pop={.3+i*.05}><Ball r={.42} s={[1,1,.3]} p={[0,0,.05]} c={c} o={.85}/></Move>
      </G>)}
    </G>
  </G>;
}
function Reef(){
  const rocks:[number,number,number,number][]=[[-7,-7,2.6,1.0],[-3,-9,2.0,.8],[4,-8,3.0,1.1],[8.5,-6,2.2,.9],[-9.5,-3,1.8,.8]];
  const corals:[number,number,string][]=[[-5,-6,'#F4A3A8'],[2,-6.5,'#FF8C6B'],[6.5,-4.5,'#F4A3A8'],[-8,-1,'#FF8C6B']];
  return <G>
    {rocks.map(([x,z,r,sy],i)=><Ball key={i} r={r} s={[1.2,sy,1]} p={[x,r*sy*.6,z]} c={i%2?ROCK:ROCK2}/>)}
    {corals.map(([x,z,c],i)=><G key={'c'+i} p={[x,0,z]}>
      <Cyl r={.25} r2={.35} h={2.2} p={[0,1.1,0]} c={c}/>
      <Cyl r={.18} h={1.6} p={[.6,2.0,0]} rot={[0,0,-.6]} c={c}/>
      <Cyl r={.18} h={1.4} p={[-.55,2.1,0]} rot={[0,0,.6]} c={c}/>
      <Ball r={.3} p={[1.05,2.65,0]} c={c}/>
      <Ball r={.3} p={[-.95,2.7,0]} c={c}/>
      <Ball r={.32} p={[0,2.3,0]} c={c}/>
    </G>)}
    {[[-4,-4],[5,-3],[-2,-6]].map(([x,z],i)=><Ball key={'s'+i} r={.35} s={[1,.6,1]} p={[x,.2,z]} c='#F6E6C8'/>)}
  </G>;
}
function Seaweed(){
  const spots:[number,number,number][]=[[-6,-4,5],[-5.2,-4.6,4],[5,-5.5,6],[5.8,-5,4.5],[-3.5,-7.5,6.5],[8,-2,4]];
  return <G>
    {spots.map(([x,z,h],i)=><Move key={i} sway={.08+(i%3)*.03}><G p={[x,0,z]}>
      <Tube pts={[[0,0,0],[.4,h*.3,0],[-.3,h*.6,0],[.2,h,0]]} r={.16} c={i%2?SEA:SEA2}/>
      <Ball r={.35} s={[1.6,.4,.8]} p={[.4,h*.45,0]} rot={[0,0,.4]} c={SEA}/>
      <Ball r={.3} s={[1.6,.4,.8]} p={[-.4,h*.75,0]} rot={[0,0,-.4]} c={SEA2}/>
    </G></Move>)}
  </G>;
}
function Fish(){
  const school:[number,number,number,string][]=[[0,6,0,'#5CC6E8'],[1.2,6.6,.6,'#F2B33D'],[-1,7.0,-.4,'#5CC6E8']];
  return <G>
    {school.map(([x,y,z,c],i)=><Move key={i} from={[x-4.5,y,z]} to={[x+4.5,y,z]} loop={1+i%2} bob={.1}><G>
      <Ball r={.5} s={[1.4,.8,.5]} c={c}/>
      <Cone r={.35} h={.5} p={[-.85,0,0]} rot={[0,0,Math.PI/2]} c={c}/>
      <Ball r={.09} p={[.45,.12,.22]} c={DARK}/>
    </G></Move>)}
    {[[-1,0],[.5,.3],[1.5,-.5],[-2,.4]].map(([x,z],i)=><Move key={'b'+i} from={[x,3,z]} to={[x+.3,7.5,z]} loop={2+i%2}><Ball r={.18+i*.03} c={BUB} o={.7}/></Move>)}
  </G>;
}
export function Scene(){return <>
  <group name="reef" position={[0,0,-1]} rotation={[0,0,0]}><Reef/></group>
  <group name="seaweed" position={[0,0,0]} rotation={[0,0,0]}><Seaweed/></group>
  <group name="octopus" position={[-1,0,1]} rotation={[0,.15,0]}>
    <Octopus/>
    <group name="head" position={[0,0,0]} rotation={[0,0,0]}><Head/></group>
  </group>
  <group name="skin" position={[5.5,0,2]} rotation={[0,-.35,0]}><Skin/></group>
  <group name="fish" position={[0,0,-4]} rotation={[0,0,0]}><Fish/></group>
</>;}
