import React from 'react';
import {Ball,RBox,Cyl,Cone,Torus,Capsule,G,Slab,Tiles,Scatter,Tree,Pine,Mound,Cloud,Move,Act,useTime,ramp,mix} from './kit';

export const GROUND=null;
export const SKY=['#4F9FDB','#D3EEF8'];
export const SHOTS=[
  {focus:'plaza',az:.45,el:.34,zoom:.85},
  {focus:'reader',az:-.25,el:.12,zoom:2.2},
  {focus:'link',az:-.4,el:.28,zoom:1.35,dy:-1.5},
  {focus:'screen',az:-.1,el:.2,zoom:1.3},
  {focus:'dispenser',az:-.3,el:.42,zoom:2.0},
];

type P3=[number,number,number];
const BODY='#3E8FB0',SIDE='#2F6F8C',FASCIA='#D5E0E8',DARK='#22313D',HEAD='#2B5F7A',GLOW='#7FD8F0',SLOT='#0E1418';
const AMBER='#F6B04B',GREEN='#5ED19A',STONE='#E9DCC3',STONE2='#D6C6A8',GOLD='#F2C94C';
const lerp=(a:P3,b:P3,t:number):P3=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];

/* ---------- ATM body (kiosk) ---------- */
function Atm(){
  return <G>
    <RBox s={[2.7,.3,1.9]} p={[0,.15,0]} c={DARK} rad={.08}/>
    <RBox s={[2.3,3.9,1.5]} p={[0,2.25,-.05]} c={BODY} rad={.12}/>
    {[-1,1].map(s=><RBox key={s} s={[.18,3.9,1.62]} p={[s*1.2,2.25,-.04]} c={SIDE} rad={.08}/>)}
    {[-1,1].map(s=>[1.4,1.7,2.0].map(y=><RBox key={s+'v'+y} s={[.03,.08,.9]} p={[s*1.3,y,-.1]} c={DARK} rad={.02}/>))}
    <RBox s={[2.1,2.6,.08]} p={[0,2.45,.72]} c={FASCIA} rad={.05}/>
    <RBox s={[2.1,.6,.06]} p={[0,.65,.72]} c={SIDE} rad={.04}/>
    <RBox s={[2.75,.75,1.85]} p={[0,4.55,0]} c={HEAD} rad={.14}/>
    <RBox s={[2.3,.28,.06]} p={[0,4.55,.93]} c={GLOW} e={.7}/>
    <Cyl r={.24} h={.06} p={[0,4.55,.98]} rot={[Math.PI/2,0,0]} c={GOLD} e={.3}/>
    <Ball r={.12} p={[0,4.12,.84]} c={DARK}/>
    <RBox s={[.35,.05,.05]} p={[.85,2.1,.78]} c={SLOT} rad={.02}/>
    <Cyl r={.05} h={.7} p={[.7,5.27,-.4]} c={DARK}/>
    <Ball r={.11} p={[.7,5.65,-.4]} c={GLOW} e={.8}/>
  </G>;
}

/* ---------- screen + keypad (changes colour with the transaction) ---------- */
function Screen(){
  const u=useTime();
  const sc=mix(mix(mix('#4D8FD6','#7FD8F0',ramp(u,.22,.3)),AMBER,ramp(u,.4,.46)),GREEN,ramp(u,.61,.67));
  return <G>
    <RBox s={[1.75,.1,.45]} p={[0,.62,.2]} c={SIDE}/>
    {[-1,1].map(s=><RBox key={s} s={[.08,1.2,.45]} p={[s*.86,.05,.2]} c={SIDE} rad={.03}/>)}
    <RBox s={[1.55,1.05,.1]} p={[0,0,.03]} c={DARK} rad={.04}/>
    <RBox s={[1.3,.82,.04]} p={[0,0,.09]} c={sc} e={.6} rad={.02}/>
    <Act keys={[{t:.2,s:1},{t:.24,s:0}]}><G p={[0,0,.12]}>
      <RBox s={[.36,.24,.02]} c='#EAF4FF' e={.4} rad={.03}/>
      <RBox s={[.08,.06,.02]} p={[-.08,.02,.01]} c={GOLD} e={.4} rad={.01}/>
    </G></Act>
    <Act keys={[{t:.22,s:0},{t:.26,s:1},{t:.61,s:1},{t:.64,s:0}]}>
      <Move from={[0,0,.12]} rot={[Math.PI/2,0,0]} spin={1.5}>
        {Array.from({length:6},(_,i)=>{const a=i/6*Math.PI*2;return <Ball key={i} r={.045} p={[Math.cos(a)*.17,0,Math.sin(a)*.17]} c='#F4FAFF' e={.5} o={.4+i*.1}/>;})}
      </Move>
    </Act>
    <Act keys={[{t:.63,s:0},{t:.68,s:1}]}><G p={[0,0,.12]}>
      <Torus R={.26} r={.03} c='#F4FFF8' e={.6}/>
      <RBox s={[.16,.06,.03]} p={[-.08,-.04,0]} rot={[0,0,-.8]} c='#F4FFF8' e={.6} rad={.02}/>
      <RBox s={[.3,.06,.03]} p={[.06,.03,0]} rot={[0,0,.9]} c='#F4FFF8' e={.6} rad={.02}/>
    </G></Act>
    <G p={[0,-.85,.3]} rot={[.5,0,0]}>
      <RBox s={[1.5,.1,.6]} c={SIDE} rad={.04}/>
      {Array.from({length:12},(_,i)=><RBox key={i} s={[.17,.05,.11]} p={[-.55+(i%3)*.22,.07,-.21+Math.floor(i/3)*.14]} c='#E9EEF2' rad={.02}/>)}
      {['#E5615B',GOLD,GREEN].map((c,i)=><RBox key={c} s={[.28,.05,.11]} p={[.3,.07,-.14+i*.14]} c={c} rad={.02}/>)}
    </G>
  </G>;
}

/* ---------- card reader with the card sliding in ---------- */
function Reader(){
  const u=useTime();
  const lip=mix('#4FC3E8',GREEN,ramp(u,.26,.32));
  const blink=.3+.9*(ramp(u,.2,.24)-ramp(u,.34,.38));
  return <G>
    <RBox s={[.5,.9,.08]} p={[0,0,.02]} c={SIDE} rad={.03}/>
    <RBox s={[.36,.26,.22]} p={[0,.08,.12]} c={DARK} rad={.06}/>
    <RBox s={[.22,.03,.06]} p={[0,.1,.22]} c={SLOT} rad={.01}/>
    <RBox s={[.26,.025,.03]} p={[0,.135,.235]} c={lip} e={blink}/>
    <RBox s={[.14,.09,.02]} p={[0,-.2,.07]} c={GLOW} e={.3} rad={.015}/>
    <Act keys={[{t:.2,s:0},{t:.23,s:1},{t:.34,s:1},{t:.38,s:0}]}><G p={[0,.1,.26]}><Ball r={.12} s={[1.4,.5,.6]} c={GLOW} e={1} o={.35}/></G></Act>
    <Act keys={[{t:0,p:[0,.1,.62]},{t:.18,p:[0,.1,.5]},{t:.3,p:[0,.1,.25]}]}>
      <RBox s={[.11,.006,.17]} c='#E8706A' rad={.003}/>
      <RBox s={[.025,.003,.03]} p={[0,.004,-.04]} c={GOLD} rad={.001}/>
      <RBox s={[.018,.003,.17]} p={[.035,-.004,0]} c={DARK} rad={.001}/>
    </Act>
  </G>;
}

/* ---------- cash dispenser: shutter opens, notes slide out ---------- */
function Dispenser(){
  const u=useTime();
  const lc=mix(AMBER,GREEN,ramp(u,.78,.8));
  return <G>
    <RBox s={[1.0,.38,.12]} p={[0,0,.02]} c={SIDE} rad={.04}/>
    <RBox s={[.8,.12,.05]} p={[0,0,.08]} c={SLOT} rad={.02}/>
    {[-1,1].map(s=><Ball key={s} r={.04} p={[s*.45,.12,.09]} c={lc} e={.9}/>)}
    <Act keys={[{t:.78,p:[0,0,.11]},{t:.82,p:[0,.15,.11]}]}><RBox s={[.82,.13,.03]} c={FASCIA} rad={.02}/></Act>
    <Act keys={[{t:.82,p:[0,0,-.2]},{t:.92,p:[0,0,.22]}]}>
      {[0,1,2,3].map(i=><G key={i} p={[0,-.03+i*.015,i*.01]}>
        <RBox s={[.13,.012,.31]} c={i%2?'#86C79A':'#9FD8A8'} rad={.004}/>
        <RBox s={[.131,.014,.04]} p={[0,0,.06]} c='#E9F5E0' rad={.004}/>
      </G>)}
    </Act>
  </G>;
}

/* ---------- customer ---------- */
function Person(){
  const SKIN='#E9B48E',JACKET='#E08A5A',PANTS='#3D4F6B',HAIR='#4A3328';
  return <G>
    {[-1,1].map(s=><RBox key={'sh'+s} s={[.36,.18,.6]} p={[s*.22,.09,.08]} c={DARK} rad={.08}/>)}
    {[-1,1].map(s=><Capsule key={'lg'+s} r={.17} h={1.2} p={[s*.22,.95,0]} c={PANTS}/>)}
    <RBox s={[.98,.12,.57]} p={[0,1.62,0]} c={DARK} rad={.05}/>
    <RBox s={[.95,1.15,.55]} p={[0,2.15,0]} c={JACKET} rad={.2}/>
    <RBox s={[.04,1.0,.02]} p={[0,2.15,.28]} c={DARK} rad={.01}/>
    {[-1,1].map(s=><RBox key={'pk'+s} s={[.25,.18,.04]} p={[s*.25,1.85,.28]} c='#C9754B' rad={.03}/>)}
    <RBox s={[.5,.1,.3]} p={[0,2.72,.14]} c='#F4E6D8' rad={.04}/>
    <RBox s={[.7,.9,.3]} p={[0,2.2,-.42]} c='#3E8FB0' rad={.12}/>
    {[-1,1].map(s=><RBox key={'st'+s} s={[.08,.9,.06]} p={[s*.28,2.25,.26]} c='#2F6F8C' rad={.02}/>)}
    <Cyl r={.13} h={.2} p={[0,2.8,0]} c={SKIN}/>
    <Ball r={.32} p={[0,3.08,0]} c={SKIN}/>
    <Ball r={.33} s={[1,.75,1]} p={[0,3.2,-.04]} c={HAIR}/>
    {[-1,1].map(s=><Ball key={'ey'+s} r={.04} p={[s*.11,3.1,.29]} c={DARK}/>)}
    {[-1,1].map(s=><Ball key={'ea'+s} r={.07} p={[s*.31,3.07,0]} c={SKIN}/>)}
    <Ball r={.05} p={[0,3.03,.32]} c='#DDA07C'/>
    <G p={[.58,2.62,0]}><Capsule r={.12} h={.75} p={[0,-.5,0]} c={JACKET}/><Ball r={.12} p={[0,-1.0,0]} c={SKIN}/></G>
    <G p={[-.58,2.62,0]}>
      <Act keys={[{t:.05,rot:[0,0,0]},{t:.17,rot:[-1.85,0,.4]},{t:.36,rot:[-1.85,0,.4]},{t:.44,rot:[0,0,0]},{t:.8,rot:[0,0,0]},{t:.9,rot:[-1.04,0,.33]}]}>
        <Capsule r={.12} h={.75} p={[0,-.5,0]} c={JACKET}/>
        <Ball r={.12} p={[0,-1.0,0]} c={SKIN}/>
      </Act>
    </G>
  </G>;
}

/* ---------- the bank ---------- */
function Bank(){
  const u=useTime();
  const kA=ramp(u,.45,.5),kG=ramp(u,.57,.62);
  const win=mix(mix('#5B7A99','#F6C65B',kA),'#7EE0A8',kG);
  const we=.15+.85*kA;
  return <G>
    <RBox s={[8,.25,6]} p={[0,.125,0]} c={STONE2} rad={.05}/>
    <RBox s={[7.6,.25,5.6]} p={[0,.375,-.1]} c={STONE} rad={.05}/>
    <RBox s={[7.2,.25,5.2]} p={[0,.625,-.2]} c={STONE2} rad={.05}/>
    <RBox s={[6.4,4.6,4.2]} p={[0,3.05,-.6]} c={STONE} rad={.1}/>
    {[-2.4,-.8,.8,2.4].map(x=><G key={x}>
      <RBox s={[.8,.2,.8]} p={[x,.85,2.0]} c={STONE2}/>
      <Cyl r={.3} h={4.2} p={[x,3.05,2.0]} c='#F4EBDA'/>
      <RBox s={[.8,.2,.8]} p={[x,5.05,2.0]} c={STONE2}/>
    </G>)}
    <RBox s={[7.0,.6,5.0]} p={[0,5.45,-.2]} c={STONE2} rad={.06}/>
    <Cone r={4.9} h={1.5} p={[0,6.5,-.2]} rot={[0,Math.PI/4,0]} c='#5D8FB5' seg={4}/>
    <Cyl r={.35} h={.08} p={[0,5.45,2.32]} rot={[Math.PI/2,0,0]} c={GOLD} e={.3}/>
    <RBox s={[1.3,2.4,.1]} p={[0,1.95,1.52]} c='#7A5638' rad={.04}/>
    <RBox s={[1.1,2.2,.04]} p={[0,1.95,1.58]} c={win} e={we*.6} rad={.03}/>
    {[-1,1].map(s=><RBox key={s} s={[.9,1.6,.08]} p={[s*1.6,3.0,1.52]} c={win} e={we} rad={.04}/>)}
    {[-1,1].map(s=><RBox key={'l'+s} s={[1.1,.12,.2]} p={[s*1.6,2.15,1.6]} c={STONE2}/>)}
    <Cyl r={.07} h={1.6} p={[3.1,6.55,1.6]} c={DARK}/>
    <Cyl r={.55} r2={.15} h={.25} p={[3.1,7.4,1.6]} rot={[.9,0,-.6]} c='#E6EBF1'/>
    <Ball r={.09} p={[3.1,7.45,1.6]} c={win} e={.9}/>
  </G>;
}

/* ---------- data link between ATM antenna and bank dish ---------- */
function Link(){
  const A:P3=[.7,5.85,-.4],M:P3=[-1.6,8.8,-4.2],B:P3=[-3.4,7.6,-7.9];
  const pts:P3[]=[A,lerp(A,M,.5),M,lerp(M,B,.5),B];
  const AMB=[{t:.39,s:0},{t:.42,s:1},{t:.56,s:1},{t:.59,s:0}];
  const GRN=[{t:.56,s:0},{t:.59,s:1},{t:.68,s:1},{t:.71,s:0}];
  return <G>
    {[0,1,2,3].map(i=>[.25,.5,.75].map(f=><Ball key={i+'d'+f} r={.06} p={lerp(pts[i],pts[i+1],f)} c={GLOW} o={.35}/>))}
    {[0,1,2,3].map(i=><Move key={'a'+i} from={pts[i]} to={pts[i+1]} loop={8}><Act keys={AMB}><Ball r={.22} c={AMBER} e={.9}/></Act></Move>)}
    {[0,1,2,3].map(i=><Move key={'g'+i} from={pts[i+1]} to={pts[i]} loop={8}><Act keys={GRN}><Ball r={.22} c={GREEN} e={.9}/></Act></Move>)}
    <Move from={A} to={[A[0],A[1]+.4,A[2]]} loop={6}><Act keys={AMB}><Torus R={.45} r={.03} rot={[Math.PI/2,0,0]} c={AMBER} e={.8}/></Act></Move>
    <Move from={B} to={[B[0],B[1]+.4,B[2]]} loop={6}><Act keys={GRN}><Torus R={.5} r={.03} rot={[Math.PI/2,0,0]} c={GREEN} e={.8}/></Act></Move>
  </G>;
}

/* ---------- plaza furniture ---------- */
const Lamp=({p}:{p:P3})=><G p={p}>
  <Cyl r={.25} r2={.3} h={.3} p={[0,.15,0]} c={DARK}/>
  <Cyl r={.08} h={4.6} p={[0,2.6,0]} c='#3A4A58'/>
  <Cyl r={.3} r2={.2} h={.5} p={[0,5.15,0]} c='#3A4A58'/>
  <Ball r={.2} p={[0,5.15,0]} c='#FFE3A3' e={.7}/>
  <Cone r={.4} h={.3} p={[0,5.55,0]} c={DARK}/>
</G>;
const Planter=({p}:{p:P3})=><G p={p}>
  <RBox s={[1.4,.6,1.4]} p={[0,.3,0]} c='#B9A58C' rad={.08}/>
  <RBox s={[1.2,.05,1.2]} p={[0,.6,0]} c='#6E4A30'/>
  <Tree h={4.2} p={[0,.6,0]}/>
</G>;
const Bench=({p,r=0}:{p:P3,r?:number})=><G p={p} rot={[0,r,0]}>
  <RBox s={[2,.12,.6]} p={[0,.6,0]} c='#C98A55'/>
  <RBox s={[2,.45,.1]} p={[0,1.0,-.27]} c='#C98A55'/>
  {[-1,1].map(s=><RBox key={s} s={[.1,.6,.5]} p={[s*.85,.3,0]} c={DARK}/>)}
</G>;
const Bollard=({p}:{p:P3})=><G p={p}><Cyl r={.15} h={.85} p={[0,.425,0]} c='#3A4A58'/><Ball r={.15} p={[0,.85,0]} c='#3A4A58'/><Cyl r={.16} h={.08} p={[0,.65,0]} c={GOLD}/></G>;

function Plaza(){
  return <G>
    <Tiles w={12} d={10} nx={8} nz={7} c1='#D6DEE6' c2='#C3CED8' p={[0,0,.5]}/>
    {[-5.3,5.3].map(x=><Lamp key={'f'+x} p={[x,.1,4.3]}/>)}
    <Lamp p={[5.3,.1,-3.8]}/>
    <Planter p={[-4.5,.1,-1.5]}/>
    <Planter p={[4.6,.1,-2.4]}/>
    <Bench p={[-3.6,.1,3.0]} r={.3}/>
    {[-4,-2,0,2,4].map(x=><Bollard key={x} p={[x,.1,5.1]}/>)}
    <G p={[3.8,.1,-.6]}><Cyl r={.35} r2={.3} h={1} p={[0,.5,0]} c='#2F6F8C'/><Cyl r={.38} h={.1} p={[0,1.05,0]} c={DARK}/></G>
    <G p={[4.6,.1,2.2]}><Cyl r={.18} h={.7} p={[0,.35,0]} c='#E5615B'/><Ball r={.18} p={[0,.72,0]} c='#E5615B'/><Cyl r={.07} h={.5} p={[0,.45,0]} rot={[0,0,Math.PI/2]} c='#C94A45'/></G>
  </G>;
}

function Car(){
  return <G s={1.1}>
    <RBox s={[3,.8,1.5]} p={[0,.7,0]} c='#EE6C9C' rad={.25}/>
    <RBox s={[1.6,.7,1.3]} p={[-.1,1.3,0]} c='#F58AB2' rad={.25}/>
    <RBox s={[1.1,.4,1.32]} p={[-.1,1.35,0]} c='#BFE6FA' rad={.1}/>
    {[[-1,-.75],[1,-.75],[-1,.75],[1,.75]].map(([x,z],i)=><Cyl key={i} r={.38} h={.3} p={[x,.38,z]} rot={[Math.PI/2,0,0]} c='#2B2F3A'/>)}
  </G>;
}

function Ground(){
  return <G>
    <Slab w={46} d={46} top='#86C27C' layers={[{h:.8,c:'#8E99A3'},{h:1.2,c:'#7A5C46'},{h:1.6,c:'#62666E'}]}/>
    <RBox s={[46,.06,6]} p={[0,.03,16.5]} c='#4A5260' rad={.02}/>
    <RBox s={[46,.2,.4]} p={[0,.1,13.4]} c='#C3CED8' rad={.04}/>
    {Array.from({length:9},(_,i)=><RBox key={i} s={[2,.03,.18]} p={[-20+i*5,.07,16.5]} c={GOLD}/>)}
    <RBox s={[2.4,.08,3.2]} p={[-6.5,.04,-5.2]} c='#C3CED8' rad={.03}/>
  </G>;
}

const Bldg=({p,w,h,d,c,c2}:{p:P3,w:number,h:number,d:number,c:string,c2:string})=>{
  const rows=Math.floor((h-1.5)/1.5),cols=Math.floor(w/1.3);
  return <G p={p}>
    <RBox s={[w,h,d]} p={[0,h/2,0]} c={c} rad={.15}/>
    <RBox s={[w+.2,.3,d+.2]} p={[0,h+.15,0]} c={c2}/>
    {Array.from({length:rows*cols},(_,i)=><RBox key={i} s={[.7,.9,.06]} p={[-w/2+(i%cols+.5)*w/cols,1.4+Math.floor(i/cols)*1.5,d/2+.02]} c='#BFE3F2' rad={.03}/>)}
  </G>;
};

export function Scene(){return <>
  <group name="ground"><Ground/>
    <Move from={[-24,0,17.5]} to={[24,0,17.5]} loop={1}><Car/></Move>
  </group>
  <group name="plaza"><Plaza/></group>
  <group name="atm" position={[0,.1,0]}><Atm/></group>
  <group name="screen" position={[-.25,3.25,.76]}><Screen/></group>
  <group name="reader" position={[.82,3.1,.76]}><Reader/></group>
  <group name="dispenser" position={[-.25,1.65,.76]}><Dispenser/></group>
  <group name="person" position={[1.9,.1,1.3]} rotation={[0,-1.8,0]}>
    <Act keys={[{t:.76,p:[0,0,0]},{t:.82,p:[.1,0,.45]}]}><Person/></Act>
  </group>
  <group name="bank" position={[-6.5,0,-9.5]}><Bank/></group>
  <group name="link"><Link/></group>
  <group name="city">
    <Bldg p={[7,0,-12]} w={5} h={9} d={4} c='#9DB8D0' c2='#6F8FAD'/>
    <Bldg p={[13,0,-7]} w={4} h={6} d={4} c='#B7C7D8' c2='#7F9AB5'/>
    <Bldg p={[-15,0,-13]} w={5} h={7.5} d={4} c='#A9C2D6' c2='#6F8FAD'/>
  </group>
  <group name="nature">
    <Scatter n={7} seed={3} box={[-20,-21,20,-15]} avoid={[[7,-12,4],[-15,-13,4]]} render={(i,r)=>i%2?<Pine h={5+r()*3}/>:<Tree h={5+r()*3}/>}/>
    <Scatter n={6} seed={7} box={[9,-3,20,6]} avoid={[[13,-7,3.5]]} render={(i,r)=>i%3?<Tree h={4.5+r()*2.5}/>:<Pine h={5+r()*2}/>}/>
    <Scatter n={5} seed={11} box={[-20,-6,-10,8]} render={(i,r)=>i%2?<Tree h={4.5+r()*2.5}/>:<Pine h={5+r()*2}/>}/>
    <Scatter n={6} seed={5} box={[-20,-12,20,11]} avoid={[[0,0,9],[-6.5,-9.5,5.5],[7,-12,4],[13,-7,3.5],[-15,-13,4]]} render={(i,r)=><Mound r={.6+r()*.5} c={i%2?'#5FA85A':'#4E9550'}/>}/>
    <Move from={[-22,14,-14]} to={[22,14,-14]} loop={1}><Cloud s={1.6}/></Move>
    <Move from={[-8,17,-18]} to={[26,17,-18]} loop={1}><Cloud s={2.1}/></Move>
    <Move from={[10,12,-16]} to={[-24,12,-16]} loop={1}><Cloud s={1.3}/></Move>
  </group>
</>;}
