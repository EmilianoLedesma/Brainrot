import React from 'react';
import {Ball,RBox,Cyl,Cone,Capsule,Torus,Lathe,Tube,G,Slab,Scatter,Rock,Act,Move} from './kit';

export const GROUND=null;
export const SKY=['#1F6F9A','#8FD6E4'];
export const SHOTS=[{focus:'reef',az:.4,el:.3},{focus:'octopus',az:-.25,el:.2},{focus:'head',az:.35,el:.12},{focus:'octopus',az:.55,el:.42},{focus:'skin',az:-.1,el:.48}];

type P3=[number,number,number];
const SKIN='#EE7A5C',SKIN2='#F59A7C',SUCK='#F8D6C6',CAMO='#8E8670',CAMO_D='#5F5A48',CAMO_L='#C2B898',SAND='#E8D5A4',PATCH='#F4A58A';
const PIG=['#C8402F','#8A4A2A','#E9A93A'];
const T_CAMO=.44;
const OCT:P3=[0,0,2];
const HC:P3=[0,1.3,.45];
const MANTLE:[number,number][]=[[.42,0],[.95,.35],[1.15,.9],[1.1,1.5],[.8,2.0],[.35,2.3],[.001,2.36]];
const MANTLE_C=MANTLE.map(([r,y])=>[r+.035,y] as [number,number]);
const rAt=(y:number)=>{for(let i=0;i<MANTLE.length-1;i++){const [r0,y0]=MANTLE[i],[r1,y1]=MANTLE[i+1];if(y>=y0&&y<=y1)return r0+(r1-r0)*(y-y0)/(y1-y0);}return .5;};
const ang=(i:number)=>i/8*Math.PI*2+Math.PI/8;
const arm=(i:number):P3[]=>{const a=ang(i);const P=(R:number,b:number,y:number):P3=>[R*Math.sin(a+b),y,R*Math.cos(a+b)+.2];
  return [P(.45,0,.75),P(1.4,0,.34),P(2.5,.05,.22),P(3.3,.25,.22),P(3.55,.6,.3),P(3.1,.85,.48)];};
const norm=(d:number[]):P3=>{const L=Math.hypot(d[0],d[1],d[2]);return [d[0]/L,d[1]/L,d[2]/L];};
const pulse=(k:number)=>[{t:.2,s:.7},{t:.26+(k%5)*.01,s:1.3},{t:.34,s:1}];

function Seabed(){
  return <Slab w={44} d={44} top={SAND} layers={[{h:1,c:'#D4B880'},{h:1.6,c:'#A8845E'},{h:2.2,c:'#6E6A7E'}]}/>;
}

function Reef(){
  const ripples=[[-9,8,.2],[-4,10,-.1],[4,9.5,.15],[9,7.5,-.2],[-11,1,.3],[11,0,.1],[-8,-7,.2],[8,-8,-.1],[-2,11.5,.05],[6,11.5,.25],[-11,-4,-.2],[11,-5,.2]];
  return <G>
    {ripples.map(([x,z,r],i)=><RBox key={i} s={[3.2,.05,.14]} p={[x,.03,z]} rot={[0,r,0]} c='#D6BF8A' rad={.02}/>)}
    {[[-9,5],[9,4],[-10,-2],[10,-3],[-7,10],[7,10.5]].map(([x,z],i)=><Ball key={'p'+i} r={.18+i%3*.06} s={[1,.6,1]} p={[x,.06,z]} c={i%2?'#B9AFA0':'#CFC4B0'}/>)}
    <G p={[0,0,-10]}>
      <Rock r={3.2} c={CAMO} seed={3}/>
      <Rock r={1.8} p={[4.2,0,-.5]} c={CAMO_D} seed={7}/>
      <Rock r={1.5} p={[-4,0,.3]} c={CAMO} seed={5}/>
      {[[-1.1,2.7,1.7],[.8,2.9,1.4],[1.8,2,2.2],[-2.3,1.7,2.3],[0,3.4,.4],[.3,1.8,3.1]].map(([x,y,z],i)=><Ball key={i} r={.3} s={[1,.6,1]} p={[x,y,z]} c={i%2?CAMO_D:CAMO_L}/>)}
    </G>
  </G>;
}

function Kelp({h}:{h:number}){
  const n=Math.round(h/1.1);
  return <Move sway={.06}>
    {Array.from({length:n},(_,i)=><G key={i}>
      <Capsule r={.12} h={.9} p={[0,i*1.05+.55,0]} c='#4E9E6A'/>
      <Ball r={.35} s={[.4,1.2,.15]} p={[i%2?.28:-.28,i*1.05+.8,0]} rot={[0,0,i%2?-.6:.6]} c='#6BB87A'/>
    </G>)}
  </Move>;
}
function Coral({c,c2}:{c:string,c2:string}){
  return <G>
    <Cyl r={.25} r2={.35} h={1.2} p={[0,.6,0]} c={c}/>
    <Cyl r={.14} h={1.1} p={[.35,1.5,0]} rot={[0,0,-.5]} c={c}/>
    <Cyl r={.14} h={1.0} p={[-.38,1.4,.1]} rot={[0,0,.6]} c={c}/>
    <Cyl r={.13} h={1.0} p={[0,1.7,.3]} rot={[.4,0,0]} c={c}/>
    {[[.62,2.0,0],[-.66,1.85,.1],[0,2.2,.5]].map(([x,y,z],i)=><Ball key={i} r={.2} p={[x,y,z]} c={c2}/>)}
  </G>;
}
function Anemone(){
  return <G>
    <Cyl r={.45} r2={.55} h={.5} p={[0,.25,0]} c='#E58FB0'/>
    <Move sway={.05}>{Array.from({length:10},(_,i)=>{const a=i/10*Math.PI*2;return <G key={i} p={[Math.sin(a)*.32,.75,Math.cos(a)*.32]} rot={[Math.cos(a)*.4,0,-Math.sin(a)*.4]}>
      <Capsule r={.07} h={.4} c='#F7B7CF'/><Ball r={.08} p={[0,.3,0]} c='#FFE2EC'/></G>;})}</Move>
  </G>;
}
function SeaFan(){
  return <G><Cyl r={.08} h={.6} p={[0,.3,0]} c='#6E4F8F'/><Move sway={.04}><Ball r={1.4} s={[1,1.1,.1]} p={[0,1.9,0]} c='#9B6FD0' o={.95}/></Move></G>;
}
function Starfish(){
  return <G>{Array.from({length:5},(_,i)=><G key={i} rot={[0,i/5*Math.PI*2,0]}><RBox s={[.16,.08,.6]} p={[0,.05,.3]} c='#F2A65A' rad={.04}/></G>)}<Ball r={.16} s={[1,.5,1]} p={[0,.07,0]} c='#F7C27F'/></G>;
}
function MiniFish({c}:{c:string}){
  return <G><Ball r={.3} s={[1.8,1,.6]} c={c}/><Cone r={.22} h={.35} p={[-.6,0,0]} rot={[0,0,-Math.PI/2]} c={c}/></G>;
}
function Nature(){
  return <G>
    <Scatter n={10} seed={11} box={[-20,-20,20,-6]} avoid={[[0,-10,6.5],[0,2,9]]} render={(i,r)=><Kelp h={6+r()*4}/>}/>
    <Scatter n={5} seed={23} box={[-20,-20,20,-13]} avoid={[[0,-10,6]]} render={()=><SeaFan/>}/>
    <Scatter n={8} seed={5} box={[-20,-6,20,16]} avoid={[[0,2,10.5],[0,-10,6],[0,16,8]]} render={(i)=><Coral c={['#F08A7A','#F5B85A','#7FD1C8','#C68BE0'][i%4]} c2={['#FFC2B5','#FFE08A','#BDF2EA','#E8C2F5'][i%4]}/>}/>
    <Scatter n={5} seed={8} box={[-20,-2,20,18]} avoid={[[0,2,10.5],[0,16,8]]} render={()=><Anemone/>}/>
    <Scatter n={7} seed={14} box={[-20,-20,20,20]} avoid={[[0,2,10.5],[0,-10,6.5],[0,16,8]]} render={(i,r)=><Rock r={.5+r()*.8} c='#8A93A0' seed={i+2}/>}/>
    <Scatter n={7} seed={31} box={[-18,10,18,20]} avoid={[[0,2,10.5],[0,16,7]]} render={(i)=>i%2?<Starfish/>:<Ball r={.3} s={[1,.5,.8]} p={[0,.12,0]} c='#F4E1D2'/>}/>
    {[[-10,-14],[6,-15],[14,-9]].map(([x,z],i)=><Move key={'l'+i} sway={.03}><Cone r={3} h={20} p={[x,10,z]} c='#E6FAFF' o={.12} e={.4}/></Move>)}
    {[[-13,-9],[12,-8],[-15,5]].map(([x,z],i)=><G key={'b'+i}>{[0,1,2].map(k=><Move key={k} from={[x+k*.2,.5+k*.6,z]} to={[x+.4,10,z]} loop={2+k}><Ball r={.15} c='#E8FBFF' o={.7}/></Move>)}</G>)}
    {[0,1,2,3,4].map(i=><Move key={'f'+i} from={[-22-i*.9,8+(i%3)*.5,-15+(i%2)*.8]} to={[22-i*.9,8.6+(i%3)*.5,-15+(i%2)*.8]} loop={1}><MiniFish c={i%2?'#F6D55C':'#5FC6D9'}/></Move>)}
  </G>;
}

function Eye({sx}:{sx:number}){
  const c:P3=[sx*.55,1.82,.88];
  return <G>
    <Ball r={.3} p={c} c='#F2C14E'/>
    <G p={[c[0]+sx*.1,c[1]+.02,c[2]+.25]} rot={[0,sx*.4,0]}>
      <Ball r={.17} s={[1,1,.35]} c='#D9892A'/>
      <RBox s={[.26,.07,.06]} p={[0,0,.05]} c='#3A2B33' rad={.03}/>
      <Ball r={.035} p={[sx*.06,.06,.08]} c='#FFF6E8' e={.5}/>
    </G>
    <Ball r={.34} s={[1.05,.5,1]} p={[c[0],c[1]+.2,c[2]-.05]} c={SKIN}/>
    <G p={[c[0],c[1]+.2,c[2]-.05]}><Move pop={T_CAMO}><Ball r={.355} s={[1.05,.5,1]} c={CAMO}/></Move></G>
    <G p={[c[0],c[1]+.32,c[2]-.08]}>
      <Act keys={[{t:0,s:.05},{t:.48,s:.05},{t:.56,s:1}]}>
        <Cone r={.1} h={.45} p={[0,.2,0]} c={CAMO_D}/>
        <Cone r={.06} h={.3} p={[sx*.16,.12,.08]} rot={[0,0,-sx*.45]} c={CAMO}/>
      </Act>
    </G>
  </G>;
}

const MSPOTS=Array.from({length:16},(_,i)=>[[.5,.9,1.3,1.7][i>>2],[-1.3,-.45,.4,1.25][i&3]+((i>>2)%2)*.3]);
const HSPOTS=[[.6,.4,.7],[-.6,.4,.7],[.9,0,.4],[-.9,0,.4],[0,.5,.85],[.35,-.3,.9],[-.35,-.3,.9],[0,-.1,1]];
function Head(){
  const spots=[[.9,-.6],[.9,.3],[.9,1.2],[1.5,-.2],[1.5,.7],[1.5,-1.1],[2.0,.2],[2.0,-.7],[.6,0],[1.2,1.8],[1.2,-1.8],[1.8,1.4]];
  const headSpots=[[.5,.3,.8],[-.5,.3,.8],[.8,.1,.5],[-.8,.1,.5],[0,.2,1],[.3,-.2,.9],[-.3,-.2,.9]];
  return <G>
    <G p={[0,1.35,-.35]} rot={[-.5,0,0]}>
      <Lathe pts={MANTLE} c={SKIN}/>
      {MSPOTS.map(([y,b],i)=>{const r=rAt(y)-.08;return <G key={'m'+i} p={[r*Math.sin(b),y,r*Math.cos(b)]}><Act keys={pulse(i)}><Ball r={.12} c={PIG[i%3]}/></Act></G>;})}
      <Move pop={T_CAMO}><Lathe pts={MANTLE_C} c={CAMO}/></Move>
      {spots.map(([y,b],i)=>{const r=rAt(y)+.02;return <G key={i} p={[r*Math.sin(b),y,r*Math.cos(b)]}><Move pop={.46+i*.01}><Ball r={.16} c={i%2?CAMO_D:CAMO_L}/></Move></G>;})}
      {[[.4,.6],[-.4,.5],[0,.2],[.3,-.6],[-.35,-.4]].map(([x,z],i)=><G key={'c'+i} p={[x,2.15,z]}><Move pop={.5+i*.01}><Cone r={.08} h={.3} c={CAMO_D}/></Move></G>)}
    </G>
    <Ball r={.9} p={HC} c={SKIN2}/>
    {HSPOTS.map((d,i)=>{const n=norm(d);return <G key={'h'+i} p={[HC[0]+n[0]*.8,HC[1]+n[1]*.8,HC[2]+n[2]*.8]}><Act keys={pulse(i+2)}><Ball r={.12} c={PIG[(i+1)%3]}/></Act></G>;})}
    <G p={HC}><Move pop={T_CAMO}><Ball r={.925} c={CAMO}/></Move></G>
    {headSpots.map((d,i)=>{const n=norm(d);return <G key={i} p={[HC[0]+n[0]*.92,HC[1]+n[1]*.92,HC[2]+n[2]*.92]}><Move pop={.47+i*.01}><Ball r={.11} c={i%2?CAMO_D:CAMO_L}/></Move></G>;})}
    <Eye sx={-1}/>
    <Eye sx={1}/>
  </G>;
}

function Octopus(){
  const arms=Array.from({length:8},(_,i)=>arm(i));
  return <G>
    <Cone r={1.5} h={.8} p={[0,.45,.2]} c={SKIN} seg={8}/>
    <G p={[0,.45,.2]}><Move pop={T_CAMO}><Cone r={1.55} h={.82} c={CAMO} seg={8}/></Move></G>
    {arms.map((pts,i)=>{const a=ang(i);const ox=Math.cos(a)*.17,oz=-Math.sin(a)*.17;return <G key={i}>
      <Tube pts={pts} r={.2} c={SKIN}/><Tube pts={pts.slice(0,3)} r={.26} c={SKIN}/>
      {pts.slice(2).map((p,k)=><Ball key={k} r={.09} p={[p[0]+ox,Math.max(.12,p[1]-.08),p[2]+oz]} c={SUCK}/>)}
      {pts.slice(1,5).map((p,k)=><G key={'s'+k} p={[p[0],p[1]+.1,p[2]]}><Act keys={pulse(i+k)}><Ball r={.12} c={PIG[(i+k)%3]}/></Act></G>)}
    </G>;})}
    <Move pop={T_CAMO}>{arms.map((pts,i)=><G key={i}>
      {i===0?<Tube pts={pts.slice(0,2)} r={.3} c={CAMO}/>:<G><Tube pts={pts} r={.24} c={CAMO}/><Tube pts={pts.slice(0,3)} r={.3} c={CAMO}/></G>}
    </G>)}</Move>
    <Cyl r={.14} r2={.2} h={.55} p={[.85,1.0,-.1]} rot={[0,0,-1.1]} c={SKIN2}/>
    {[0,1,2,3].map(k=><Move key={k} from={[1.15,1.15,-.1]} to={[1.6+k*.15,4.5,-.2]} loop={2+k}><Ball r={.12+k*.03} c='#E8FBFF' o={.75}/></Move>)}
  </G>;
}

const A0=arm(0);
const lerp=(a:P3,b:P3,t:number):P3=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
const CELLS:P3[]=(()=>{const out:P3[]=[];[[1,2],[2,3]].forEach(([i0,i1])=>{const a=A0[i0],b=A0[i1];const dx=b[0]-a[0],dz=b[2]-a[2];const L=Math.hypot(dx,dz);const px=dz/L,pz=-dx/L;
  [.2,.5,.8].forEach((t,k)=>[-1,1].forEach(sd=>{const q=lerp(a,b,t+(sd>0?.08:0));const off=sd*.08;out.push([q[0]+px*off,q[1]+Math.sqrt(.28*.28-off*off)-.015,q[2]+pz*off]);}));});return out;})();
function Skin(){
  return <G>
    <Tube pts={[A0[1],A0[2],A0[3]]} r={.28} c={PATCH}/>
    {CELLS.map((p,i)=><G key={i} p={p}>
      <Torus R={.075} r={.012} rot={[Math.PI/2,0,0]} c='#B5523C'/>
      <Act keys={[{t:0,s:.3},{t:.82+i*.006,s:.3},{t:.88+i*.006,s:1},{t:.93,s:.6},{t:.98,s:1.05}]}>
        <Cyl r={.065} h={.03} c={PIG[i%3]} e={.15}/>
        <Cyl r={.025} h={.04} p={[0,.005,0]} c='#4A2A22'/>
      </Act>
    </G>)}
  </G>;
}

function Fish(){
  return <G>
    <Ball r={1} s={[1.9,1,.7]} c='#3F7FB8'/>
    <Ball r={.85} s={[1.7,.7,.62]} p={[.1,-.25,0]} c='#9FD3E8'/>
    {[-.7,0,.7].map((x,i)=><Ball key={i} r={.16} s={[.6,2.6,1]} p={[x,.2,0]} c='#2E6596'/>)}
    <Cone r={.75} h={1.1} p={[-2.25,0,0]} rot={[0,0,-Math.PI/2]} c='#2E6596'/>
    <Cone r={.5} h={.9} p={[-.1,.95,0]} c='#2E6596'/>
    {[-1,1].map(s=><G key={s}>
      <Ball r={.2} p={[1.3,.25,s*.45]} c='#FFF4D8'/><Ball r={.1} p={[1.4,.27,s*.6]} c='#2B2030'/>
      <Ball r={.35} s={[1,.4,.2]} p={[.3,-.35,s*.65]} rot={[0,0,.5]} c='#5C9BD0'/>
    </G>)}
    <RBox s={[.3,.08,.4]} p={[1.85,-.15,0]} c='#2B4E73' rad={.03}/>
  </G>;
}

export function Scene(){return <>
  <group name="seabed"><Seabed/></group>
  <group name="reef"><Reef/></group>
  <group name="nature"><Nature/></group>
  <group name="octopus" position={OCT} scale={2}><Octopus/></group>
  <group name="head" position={OCT} scale={2}><Head/></group>
  <group name="skin" position={OCT} scale={2}><Skin/></group>
  <group name="fish"><Act keys={[{t:0,p:[-24,6,-6.5]},{t:.58,p:[-24,6,-6.5]},{t:.8,p:[24,6.4,-6.5]}]}><Fish/></Act></group>
</>;}
