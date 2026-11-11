import React from 'react';
import {AbsoluteFill,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import script from './script.json';
import {EZ,FPS,H,W,clip,ez} from '../remotion-explainer/coffee-sci/kit';

// Silent low-poly explainer in ONE continuous world (the reference has no cuts): a desk with a motherboard and the chip, and a workbench in
// front with one station per part in the order the narration introduces them. The camera flies between stations (script.waypoints) and then
// drifts; parts fly in once, on an arc, and stay. Every animated value is a pure function of useCurrentFrame() (never useFrame).
export const CPU_FRAMES=script.durationFrames;
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const K={wall:'#B9C4EE',wallLine:'#A5B2E4',desk:'#F2C48D',deskLine:'#E5B07A',bench:'#FCE6C4',board:'#7E8B99',boardDark:'#5F6B78',white:'#F4F6F8',gray:'#C9CFD8',
  mid:'#9AA3AE',dark:'#4B5563',lime:'#8BE04E',red:'#E5333B',term:'#FFD23F',hl:'#BEE3FF',mug:'#E58FA8',coffee:'#6B4A3A',warm:'#FFE6C2',heat:'#FF9A5C'};
const HEAT0=3900; // the narration reaches the heat at ~130 s: the die turns orange and warm cubes rise from it
type V3=[number,number,number];
const BENCH=['transistor','gate','adder','alu','clock','control','register','cache','ram','pipeline','core','heatsink'];
const TARGETS=['chip',...BENCH];
const PARTS=['TRANSISTOR','COMPUERTAS','COMPUERTA','ALU','RELOJ','REGISTRO','REGISTROS','CACHÉ','RAM','PIPELINE','NÚCLEOS','NÚCLEO','DISIPADOR'];
const P=120,CHIP:V3=[0,0,-6];
const POS:Record<string,V3>={chip:CHIP,...Object.fromEntries(BENCH.map((n,i)=>[n,[(i-5.5)*11,.6,9] as V3]))};
const DIST:Record<string,number>={wide:46,medium:32,close:20};
const wps=script.waypoints;

(function validate(){
  if(wps[0].focus!=='chip'||wps[0].dist!=='wide')throw new Error('the first waypoint must be chip/wide');
  wps.forEach((w,i)=>{
    if(!TARGETS.includes(w.focus)||!DIST[w.dist])throw new Error(`waypoint ${w.id}: invalid focus or dist`);
    if(i&&w.at-wps[i-1].at<script.flight)throw new Error(`waypoint ${w.id}: closer than one flight (${script.flight} frames) to the previous one`);
    if(!w.show)throw new Error(`waypoint ${w.id}: needs a description of what is on screen`);
  });
  if(!wps.some(w=>w.dist==='close'))throw new Error('the plan needs at least one close detail');
  const phrases=script.captions.filter(c=>c.style==='phrase');
  phrases.forEach((c,i)=>{
    if(c.text.split(' ').length>5)throw new Error(`caption ${c.id}: a phrase is at most five words`);
    if(i&&c.text.toLowerCase().startsWith(phrases[i-1].text.toLowerCase()))throw new Error(`caption ${c.id} accumulates on the previous phrase`);
  });
  script.events.forEach(e=>{if(!TARGETS.includes(e.target))throw new Error(`event ${e.id}: needs a valid target`);});
  script.captions.filter(c=>c.style==='term').forEach(c=>{if(!PARTS.includes(c.text))throw new Error(`term ${c.id}: "${c.text}" is not a real part name`);});
})();

const smooth=(t:number)=>t*t*(3-2*t);
const mixc=(a:string,b:string,t:number)=>new THREE.Color(a).lerp(new THREE.Color(b),clip(t)).getStyle();
const aim=(w:{focus:string}):V3=>{const p=POS[w.focus];return [p[0],p[1]+(w.focus==='chip'?1:1.4),p[2]];};
// a `close` shot of a station wider than the frame backs off a little so the active sub-part is not cropped
const distOf=(w:{focus:string,dist:string})=>DIST[w.dist]*(w.focus==='chip'?1.3:1)*(w.dist==='close'&&GLOW[w.focus][0]>8?1.3:1);

// ---- the camera: a fixed isometric-ish direction; it flies between waypoints and drifts slowly, one continuous move ----------------------
function camAt(gf:number){
  let k=0;for(let i=0;i<wps.length;i++)if(wps[i].at<=gf)k=i;
  const cur=wps[k],prev=wps[Math.max(0,k-1)],t=k===0?1:smooth(clip((gf-cur.at)/script.flight));
  const a=aim(prev),b=aim(cur),target=a.map((v,i)=>v+(b[i]-v)*t) as V3;
  const d=Math.exp(Math.log(distOf(prev))*(1-t)+Math.log(distOf(cur))*t)*(1+.035*Math.sin(gf/110));
  const yaw=.12*Math.sin(gf/170),dir=new THREE.Vector3(-.55,.4,.95).normalize().applyAxisAngle(new THREE.Vector3(0,1,0),yaw);
  return {target,pos:[target[0]+dir.x*d,target[1]+dir.y*d,target[2]+dir.z*d] as V3};
}
function Rig({gf}:{gf:number}){
  const {camera}=useThree(),c=camAt(gf);
  camera.position.set(...c.pos);(camera as THREE.PerspectiveCamera).fov=24;(camera as THREE.PerspectiveCamera).updateProjectionMatrix();
  camera.lookAt(...c.target);camera.updateMatrixWorld();
  return null;
}
function Sun({gf}:{gf:number}){
  const c=camAt(gf),tgt=React.useMemo(()=>new THREE.Object3D(),[]);
  return <>
    <ambientLight intensity={.5*Math.PI}/>
    <primitive object={tgt} position={c.target}/>
    <directionalLight target={tgt} position={[c.target[0]+10,c.target[1]+18,c.target[2]+12]} intensity={.85*Math.PI} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048}
      shadow-camera-left={-24} shadow-camera-right={24} shadow-camera-top={24} shadow-camera-bottom={-24} shadow-camera-near={.5} shadow-camera-far={70} shadow-bias={-.0004}/>
  </>;
}

// ---- primitives -------------------------------------------------------------------------------------------------------------
const B=({s,p,c,r=[0,0,0],e=0}:{s:V3,p:V3,c:string,r?:V3,e?:number})=>
  <mesh position={p} rotation={r} castShadow receiveShadow><boxGeometry args={s}/><meshStandardMaterial color={c} emissive={e?c:'#000000'} emissiveIntensity={e} flatShading/></mesh>;
const Cyl=({r,h,p,c,seg=8,rot=[0,0,0]}:{r:number,h:number,p:V3,c:string,seg?:number,rot?:V3})=>
  <mesh position={p} rotation={rot} castShadow receiveShadow><cylinderGeometry args={[r,r,h,seg]}/><meshStandardMaterial color={c} flatShading/></mesh>;
const Y=new THREE.Vector3(0,1,0);
function Beam({a,b,r,color}:{a:V3,b:V3,r:number,color:string}){
  const A=new THREE.Vector3(...a),d=new THREE.Vector3(...b).sub(A),len=d.length(),dir=d.normalize();
  return <mesh position={A.clone().addScaledVector(dir,len/2).toArray()} quaternion={new THREE.Quaternion().setFromUnitVectors(Y,dir)}>
    <cylinderGeometry args={[r,r,Math.max(len,.0001),8]}/><meshStandardMaterial color={color} emissive={color} emissiveIntensity={.5} flatShading/></mesh>;
}
function Arrow({from,dir,len,s}:{from:V3,dir:V3,len:number,s:number}){  // thin red arrow: force/direction only
  if(s<=.02)return null;
  const d=new THREE.Vector3(...dir).normalize(),A=new THREE.Vector3(...from),L=len*s,tip=A.clone().addScaledVector(d,L),q=new THREE.Quaternion().setFromUnitVectors(Y,d);
  return <group>
    <Beam a={from} b={A.clone().addScaledVector(d,Math.max(L-.3,.001)).toArray() as V3} r={.07} color={K.red}/>
    <mesh position={tip.clone().addScaledVector(d,-.2).toArray()} quaternion={q}><coneGeometry args={[.2,.4,6]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.5} flatShading/></mesh>
  </group>;
}
const pulse=(gf:number,period:number,off=0)=>((gf+off)%period)/period;

// ---- parts: each one runs a repeating work cycle all the time (ambient), in station-local coordinates (origin on the bench top) -----------
function Transistor({gf}:{gf:number}){
  const ph=(gf%P)/P,a=ph<.1?ph/.1:ph<.5?1:ph<.6?1-(ph-.5)/.1:0,lit=mixc(K.dark,K.lime,a);
  return <group>
    <B s={[5,.6,3.4]} p={[0,.3,0]} c={K.gray}/>
    <B s={[1.1,1.4,1.4]} p={[-1.9,1.3,0]} c={K.white}/><B s={[1.1,1.4,1.4]} p={[1.9,1.3,0]} c={K.white}/>
    <B s={[2.7,.4,.9]} p={[0,1.15,0]} c={lit} e={a*.5}/>
    <B s={[1.5,.25,.25]} p={[-3.3,1.2,0]} c={lit} e={a*.5}/><B s={[1.5,.25,.25]} p={[3.3,1.2,0]} c={lit} e={a*.5}/>
    <group position={[0,1.6,0]} rotation-z={(a*2-1)*.6}>
      <B s={[.3,2.2,.3]} p={[0,1.1,0]} c={K.mid}/>
      <mesh position={[0,2.3,0]} castShadow><icosahedronGeometry args={[.38,0]}/><meshStandardMaterial color={K.white} flatShading/></mesh>
    </group>
    {a>.5&&[0,1,2].map(i=><B key={i} s={[.3,.3,.3]} p={[-4+((gf*.08+i*2.7)%8),1.45,0]} c={K.lime} e={.8}/>)}
  </group>;
}
function Gate({gf}:{gf:number}){
  const x=-4.3+pulse(gf,100)*8.6,L=(gx:number)=>mixc(K.gray,K.lime,1-Math.abs(x-gx)/1.6);
  return <group>
    <B s={[9,.4,2.4]} p={[0,.2,0]} c={K.bench}/>
    <mesh position={[-2.8,1.2,0]} rotation={[0,0,-Math.PI/2]} castShadow><coneGeometry args={[1,1.7,3]}/><meshStandardMaterial color={L(-2.8)} flatShading/></mesh>
    <B s={[1.3,1.4,1.2]} p={[-.3,1.2,0]} c={L(0)}/><Cyl r={.7} h={1.2} p={[.6,1.2,0]} c={L(0)} rot={[Math.PI/2,0,0]}/>
    <mesh position={[2.8,1.2,0]} scale={[1.3,.9,.8]} castShadow><icosahedronGeometry args={[.9,0]}/><meshStandardMaterial color={L(2.8)} flatShading/></mesh>
    <B s={[8.6,.2,.2]} p={[0,.6,1.1]} c={K.mid}/>
    <B s={[.4,.4,.4]} p={[x,.9,1.1]} c={K.lime} e={.9}/>
  </group>;
}
function Adder({gf}:{gf:number}){
  const step=Math.floor(gf/45);
  return <group>
    <B s={[8.4,.4,2.6]} p={[0,.2,0]} c={K.bench}/>
    {[0,1,2,3].map(i=>{const bit=((step>>i)^(step>>(i+1)))&1,carry=(step+i)%4===0;
      return <group key={i} position={[-2.7+i*1.8,0,0]}>
        <B s={[1.4,1,1.8]} p={[0,.9,0]} c={K.white}/>
        <B s={[.4,.4,.4]} p={[-.3,1.7,0]} c={mixc(K.dark,K.white,bit)}/><B s={[.4,.4,.4]} p={[.3,1.7,0]} c={mixc(K.white,K.dark,bit)}/>
        <B s={[1,.2,.5]} p={[0,1.45,.95]} c={mixc(K.mid,K.lime,bit)} e={bit*.5}/>
        {i<3&&<B s={[.4,.25,.25]} p={[.9,1,0]} c={mixc(K.mid,K.lime,carry?1:0)} e={carry?.6:0}/>}
      </group>;})}
  </group>;
}
const aluGeo=(()=>{const sh=new THREE.Shape();sh.moveTo(-2.4,1.8);sh.lineTo(-.55,1.8);sh.lineTo(0,1);sh.lineTo(.55,1.8);sh.lineTo(2.4,1.8);sh.lineTo(1.2,-1.8);sh.lineTo(-1.2,-1.8);sh.closePath();
  const g=new THREE.ExtrudeGeometry(sh,{depth:1.4,bevelEnabled:false});g.translate(0,0,-.7);return g;})();
function Alu({gf}:{gf:number}){
  const plus=(gf%90)<45,f=(i:number)=>mixc(K.mid,K.lime,((Math.floor(gf/12)+i)%5===0)?1:0);
  return <group>
    <B s={[6,.4,2.6]} p={[0,.2,0]} c={K.bench}/>
    <mesh geometry={aluGeo} position={[0,2.5,0]} castShadow><meshStandardMaterial color={K.white} flatShading/></mesh>
    {plus?<><B s={[1.3,.22,.1]} p={[0,2.3,.75]} c={K.dark}/><B s={[.22,1.3,.1]} p={[0,2.3,.75]} c={K.dark}/></>:<B s={[1.3,.22,.1]} p={[0,2.3,.75]} c={K.dark}/>}
    {[0,1,2,3].map(i=><B key={i} s={[.35,.35,.1]} p={[-1.2+i*.8,1.3,.75]} c={f(i)} e={.4}/>)}
    {[-1,1].map(s=><B key={s} s={[1.6,.25,.25]} p={[s*3.2,3.9,0]} c={K.mid}/>)}
    <B s={[.25,1.2,.25]} p={[0,.9,0]} c={K.mid}/>
    {[-1,1].map(s=><B key={'p'+s} s={[.35,.35,.35]} p={[s*(4.2-pulse(gf,90)*2),3.9,0]} c={K.lime} e={.9}/>)}
    <B s={[.35,.35,.35]} p={[0,.2+pulse(gf,90)*.9,0]} c={K.lime} e={.9}/>
  </group>;
}
function Clock({gf}:{gf:number}){
  return <group>
    <Cyl r={1.9} h={.8} p={[-1.2,.7,0]} c={K.white} seg={10}/>
    <group position={[-1.2,1.2,0]} rotation-y={-gf*2*Math.PI/40}><B s={[1.6,.15,.25]} p={[.8,0,0]} c={K.dark}/></group>
    {Array.from({length:8}).map((_,i)=><B key={i} s={[.2,.2,.35]} p={[-1.2+1.6*Math.cos(i*Math.PI/4),1.15,1.6*Math.sin(i*Math.PI/4)]} c={K.mid}/>)}
    <B s={[3.6,.2,.25]} p={[2.8,.8,0]} c={K.mid}/>
    {[0,1,2].map(i=><B key={i} s={[.35,.35,.35]} p={[1+pulse(gf,40,i*13)*4,.95,0]} c={K.lime} e={.9}/>)}
  </group>;
}
function Control({gf}:{gf:number}){
  const n=Math.floor(gf/40)%6,fr=smooth(clip((gf%40)/12)),x=(i:number)=>1.4-.1+i*.85-.2,at=n===0?x(0):x(n-1)+(x(n)-x(n-1))*fr;
  return <group>
    <B s={[6.6,.4,2.8]} p={[0,.2,0]} c={K.bench}/>
    <B s={[2.6,2,2.2]} p={[-2.2,1.4,0]} c={K.white}/>
    <mesh position={[-2.2,2.7,0]} castShadow><icosahedronGeometry args={[.35,0]}/><meshStandardMaterial color={mixc(K.mid,K.lime,(gf%60)<30?1:0)} emissive={K.lime} emissiveIntensity={(gf%60)<30?.6:0} flatShading/></mesh>
    <B s={[5,.3,1.6]} p={[2,.45,0]} c={K.mid}/>
    {Array.from({length:6}).map((_,i)=><B key={i} s={[.7,.5,1.3]} p={[x(i),.85,0]} c={mixc(K.gray,K.lime,i===n?1:0)} e={i===n?.5:0}/>)}
    <mesh position={[at,1.9,0]} rotation={[Math.PI,0,0]} castShadow><coneGeometry args={[.35,.8,4]}/><meshStandardMaterial color={K.dark} flatShading/></mesh>
  </group>;
}
function Register({gf}:{gf:number}){
  return <group>
    <B s={[4.4,.4,3]} p={[0,.2,0]} c={K.bench}/>
    {Array.from({length:8}).map((_,j)=>{const lit=((Math.floor(gf/15)+j)%8)<3;
      return <B key={j} s={[.8,.5,1.1]} p={[-1.5+(j%4)*1,.65,j<4?-.8:.8]} c={mixc(K.gray,K.lime,lit?1:0)} e={lit?.5:0}/>;})}
  </group>;
}
function Cache({gf}:{gf:number}){
  const lvl=[2,1,0],t=(gf%120)/120,on=(i:number)=>Math.max(0,1-Math.abs(t*4-(i+.5)));
  return <group>
    {[{w:4.6,d:3.2,y:.4},{w:3.4,d:2.4,y:1.2},{w:2.2,d:1.6,y:2}].map((s,i)=><group key={i}>
      <B s={[s.w,.8,s.d]} p={[0,s.y,0]} c={K.white}/>
      <B s={[s.w+.05,.12,s.d+.05]} p={[0,s.y+.3,0]} c={mixc(K.mid,K.lime,on(lvl[i]))} e={on(lvl[i])*.6}/>
    </group>)}
  </group>;
}
function Ram({gf}:{gf:number}){
  return <group>
    <B s={[4.4,.4,3.8]} p={[0,.2,0]} c={K.bench}/>
    {[-1.2,1.2].map((x,s)=><group key={s} position={[x,0,0]}>
      <B s={[.5,3,3.4]} p={[0,1.9,0]} c={K.board}/><B s={[.6,.3,3]} p={[0,.55,0]} c={K.dark}/>
      {[0,1,2,3].map(i=><B key={i} s={[.2,.7,.7]} p={[.35,1.4+(i>>1)*1,-.8+(i%2)*1.6]} c={mixc(K.dark,K.lime,((Math.floor(gf/20)+i+s)%4===0)?1:0)}/>)}
    </group>)}
  </group>;
}
function Pipeline({gf}:{gf:number}){
  const cols=['#F6B1C3','#BFD4FF','#CFF1B7','#FFE29A','#E2C6FF'];
  // branch prediction: the belt forks; a cone guesses a side; on every second cycle the guess is wrong and the work already sent down it is thrown off
  const cyc=Math.floor(gf/240),pick=cyc%2?1:-1,wrong=cyc%2===1,ph=(gf%240)/240,t=clip((ph-.2)/.7),show=ph>=.2&&ph<=.9;
  const fall=wrong?clip((t-.7)/.3):0,px=4.4+t*4.2,pz=pick*1.3*smooth(clip((px-5.3)/1.4)),sc=wrong?1-fall*.8:1-clip((t-.85)/.15);
  return <group>
    <B s={[10,.4,2.2]} p={[0,.4,0]} c={K.mid}/>
    <B s={[3,.3,.9]} p={[6.8,.4,-1.3]} r={[0,.35,0]} c={K.mid}/><B s={[3,.3,.9]} p={[6.8,.4,1.3]} r={[0,-.35,0]} c={K.mid}/>
    <mesh position={[5.4,2.6,pick*1.2]} rotation={[Math.PI,0,0]} castShadow><coneGeometry args={[.35,.8,4]}/><meshStandardMaterial color={K.dark} flatShading/></mesh>
    {show&&<mesh position={[px,.95-fall*2.2,pz]} rotation={[fall*3,fall*2,0]} scale={Math.max(.02,sc)} castShadow><boxGeometry args={[.9,.9,.9]}/><meshStandardMaterial color={K.dark} flatShading/></mesh>}
    {[-3.6,-1.2,1.2,3.6].map((x,i)=><group key={i} position={[x,0,0]}>
      <B s={[.25,1.6,.25]} p={[0,1.2,-1.2]} c={K.white}/><B s={[.25,1.6,.25]} p={[0,1.2,1.2]} c={K.white}/><B s={[.5,.3,2.7]} p={[0,2.1,0]} c={K.white}/></group>)}
    {cols.map((c,i)=><B key={i} s={[.9,.9,.9]} p={[-4.6+((gf*.05+i*1.84)%9.2),1.1,0]} c={c}/>)}
  </group>;
}
function Core({gf}:{gf:number}){
  return <group>
    <B s={[6.4,.4,6.4]} p={[0,.2,0]} c={K.bench}/>
    {[[-1.5,-1.5],[1.5,-1.5],[-1.5,1.5],[1.5,1.5]].map(([x,z],i)=>{const lit=(Math.floor(gf/30)+i)%4===0;
      return <group key={i} position={[x,0,z]}>
        <B s={[2.6,.6,2.6]} p={[0,.7,0]} c={K.mid}/>
        {[[-.5,-.5],[.5,-.5],[-.5,.5],[.5,.5]].map(([a,b],j)=><B key={j} s={[.8,.3,.8]} p={[a,1.15,b]} c={K.white}/>)}
        <B s={[2.2,.12,.3]} p={[0,1.05,1.2]} c={mixc(K.mid,K.lime,lit?1:0)} e={lit?.7:0}/>
      </group>;})}
  </group>;
}
function Heatsink({gf}:{gf:number}){
  return <group>
    <B s={[4,.4,4]} p={[0,.2,0]} c={K.gray}/>
    {Array.from({length:8}).map((_,i)=><B key={i} s={[.22,2.2,3.6]} p={[-1.75+i*.5,1.5,0]} c={K.white}/>)}
    <Cyl r={1.6} h={.3} p={[0,2.75,0]} c={K.dark} seg={12}/>
    <group position={[0,2.95,0]} rotation-y={gf*.35}>{[0,1,2,3].map(i=><B key={i} s={[1.4,.12,.45]} p={[Math.cos(i*Math.PI/2)*.8,0,Math.sin(i*Math.PI/2)*.8]} r={[0,-i*Math.PI/2,0]} c={K.mid}/>)}</group>
  </group>;
}
const PART:Record<string,React.FC<{gf:number}>>={transistor:Transistor,gate:Gate,adder:Adder,alu:Alu,clock:Clock,control:Control,register:Register,cache:Cache,ram:Ram,pipeline:Pipeline,core:Core,heatsink:Heatsink};
// glow size and red-arrow definition per station (station-local)
const GLOW:Record<string,V3>={chip:[8,2.4,8],transistor:[7.4,3.2,4],gate:[9.4,2.4,3],adder:[8.8,2.6,3],alu:[6.2,4,3],clock:[7,2.2,4.4],control:[6.8,3,3],register:[4.6,1.6,3.2],cache:[4.8,3,3.4],ram:[4.8,3.6,4],pipeline:[10.2,3,3],core:[6.6,2,6.6],heatsink:[4.4,3.4,4.4]};
const ARROW:Record<string,{from:V3,dir:V3}>={chip:{from:[-5,2.4,3],dir:[1,0,-.4]},transistor:{from:[-4.6,2.4,1.5],dir:[1,0,0]},gate:{from:[-4.4,2.6,1.6],dir:[1,0,0]},adder:{from:[-4.4,2.6,1.4],dir:[1,0,0]},
  alu:{from:[-4,5,0],dir:[1,-.5,0]},clock:{from:[1,2.2,1.8],dir:[1,0,0]},control:{from:[-1,3.6,0],dir:[1,-.4,0]},register:{from:[-1,2.8,1.8],dir:[0,-1,0]},
  cache:{from:[-3.4,3,0],dir:[1,0,0]},ram:{from:[-3.4,3,1.8],dir:[1,0,0]},pipeline:{from:[-5,2.8,1.6],dir:[1,0,0]},core:{from:[-4,2.4,0],dir:[1,0,0]},heatsink:{from:[0,3.6,0],dir:[0,1,0]}};
type Ev={kind:string,at:number,target:string};
const win=(gf:number,at:number,dur:number)=>{const t=gf-at;return t<0||t>dur?0:Math.min(1,t/6)*Math.min(1,(dur-t)/12);};
const act=(gf:number,kind:string,target:string,dur:number)=>Math.max(0,...script.events.filter((e:Ev)=>e.kind===kind&&e.target===target).map((e:Ev)=>win(gf,e.at,dur)));

// ---- a part that is introduced flies in on an arc, rotates and settles with a small bounce; it never pops in ----------------------------
const firstSeen=(name:string):number=>{
  const w=wps.find(x=>x.focus===name),e=script.events.find((x:Ev)=>x.target===name);
  return Math.min(w?w.at+10:1e9,e?e.at-20:1e9);
};
const ARRIVE:Record<string,number>=Object.fromEntries(BENCH.map(n=>[n,firstSeen(n)]));
function arrive(gf:number,at:number,from:V3){
  if(gf<at)return null;
  const s=spring({frame:gf-at,fps:FPS,config:{damping:9,stiffness:110,mass:.8}}),a=clip(s),lift=Math.sin(Math.PI*a)*3;
  return {pos:[from[0]*(1-s),from[1]*(1-s)+lift,from[2]*(1-s)] as V3,rot:1.1*(1-s)};
}

// ---- the world --------------------------------------------------------------------------------------------------------------------
const LID0=250;
function Chip({gf}:{gf:number}){
  const p1=smooth(clip((gf-LID0)/30)),p2=smooth(clip((gf-LID0-30)/40));
  const lid:V3=[11*p2,(1.55+3.2*p1)*(1-p2)+.85*p2,4*p2];
  const icons:[V3,string][]=[[[-6,6,2],'#8EC5FF'],[[6,7,-5],'#F6B1C3'],[[-2,8.5,-11],'#FFFFFF']];
  const hook=1-clip((gf-190)/50),bitsOn=gf<LID0+10,hot=clip((gf-HEAT0)/90);
  return <group position={CHIP}>
    <B s={[22,.5,18]} p={[0,.25,0]} c={K.board}/><B s={[9,.3,9]} p={[0,.65,0]} c={K.boardDark}/>
    {Array.from({length:6}).map((_,i)=><B key={i} s={[.18,.06,8]} p={[-3+i*1.2,.55,11]} c={K.mid}/>)}
    {[[-9,-7],[9,-7],[-9,7],[9,7]].map(([x,z],i)=><Cyl key={i} r={.7} h={1.2} p={[x,1.1,z]} c={K.mid}/>)}
    <B s={[7,1,7]} p={[0,1.3,0]} c={K.white}/>
    {Array.from({length:6}).flatMap((_,i)=>Array.from({length:6}).map((_,j)=>{const on=p2>.5&&Math.sin(gf/14-(i+j)*.7)>.2?1:0;
      return <B key={i+'-'+j} s={[.7,.25,.7]} p={[-2.1+i*.84,1.9,-2.1+j*.84]} c={mixc(K.dark,mixc(K.lime,K.heat,hot),on)} e={on*.6}/>;}))}
    <group position={[lid[0],lid[1]+.2,lid[2]]} rotation-y={p2*.6}><B s={[7.2,.4,7.2]} p={[0,0,0]} c={K.gray}/><B s={[1.4,.1,1.4]} p={[-2.4,.25,2.4]} c={K.mid}/></group>
    {bitsOn&&icons.map(([ip,col],k)=><React.Fragment key={k}>
      <group position={ip} scale={Math.max(.001,hook)} rotation-y={gf/60+k}><B s={[2.2,2.2,.4]} p={[0,0,0]} c={col}/><B s={[1.2,.25,.1]} p={[0,.2,.25]} c={K.dark}/><B s={[.8,.25,.1]} p={[0,-.4,.25]} c={K.dark}/></group>
      {Array.from({length:7}).map((_,j)=>{const u=((gf*.012+j/7+k*.13)%1);
        return <B key={j} s={[.36,.36,.36]} p={[ip[0]*(1-u),ip[1]*(1-u)+2.2*u,ip[2]*(1-u)]} c={(j+k)%2?K.dark:K.white}/>;})}
    </React.Fragment>)}
  </group>;
}
function Env(){
  return <>
    <B s={[300,70,.5]} p={[0,30,-30]} c={K.wall}/>
    {Array.from({length:61}).map((_,i)=><B key={'v'+i} s={[.14,70,.6]} p={[(i-30)*5,30,-29.7]} c={K.wallLine}/>)}
    {Array.from({length:14}).map((_,i)=><B key={'h'+i} s={[300,.14,.6]} p={[0,-4+i*5,-29.7]} c={K.wallLine}/>)}
    <B s={[300,.5,150]} p={[0,-.25,45]} c={K.desk}/>
    {Array.from({length:30}).map((_,i)=><B key={'d'+i} s={[300,.04,.25]} p={[0,.02,-28+i*4.4]} c={K.deskLine}/>)}
    <B s={[160,.6,8]} p={[0,.3,9]} c={K.bench}/>
    <Cyl r={1.7} h={3.4} p={[18,1.7,-5]} c={K.mug} seg={10}/><Cyl r={1.5} h={.1} p={[18,3.35,-5]} c={K.coffee} seg={10}/>
    <mesh position={[19.9,1.8,-5]} castShadow><torusGeometry args={[.9,.25,5,8]}/><meshStandardMaterial color={K.mug} flatShading/></mesh>
    <Cyl r={.25} h={5} p={[-16,.25,3]} c={K.term} seg={6} rot={[0,0,Math.PI/2]}/>
    <B s={[12,.5,4.2]} p={[-26,.25,21]} c={K.gray}/>
    {[0,1,2].flatMap(r=>Array.from({length:11}).map((_,c)=><B key={'k'+r+'-'+c} s={[.8,.3,.8]} p={[-30.4+c*.88,.62,19.8+r*1.05]} c={K.white}/>))}
    <B s={[1.6,.5,2.2]} p={[-14,.25,21]} c={K.gray}/>
    <B s={[7,.4,9]} p={[27,.2,22]} c={K.white}/><B s={[6.4,.1,8.4]} p={[27,.45,22]} c={K.wall}/>
    <B s={[9,7,.3]} p={[-40,16,-29.5]} c={K.white}/><B s={[7.6,5.6,.2]} p={[-40,16,-29.3]} c={K.hl}/>
    <B s={[7,9,.3]} p={[33,18,-29.5]} c={K.white}/><B s={[5.6,7.6,.2]} p={[33,18,-29.3]} c={K.warm}/>
    <Cyl r={2} h={3} p={[40,1.5,-14]} c={K.mug} seg={8}/>
    {[[0,4.4,0],[-1.4,5.4,.6],[1.2,5.6,-.4]].map((p,i)=><mesh key={'pl'+i} position={[40+p[0],p[1],-14+p[2]]} castShadow><icosahedronGeometry args={[1.5-i*.2,0]}/><meshStandardMaterial color={'#8DC8A0'} flatShading/></mesh>)}
    <B s={[1.8,2.6,.3]} p={[-20,5,-29.4]} c={K.white}/><B s={[.3,.5,.3]} p={[-20.3,5.4,-29.2]} c={K.dark}/><B s={[.3,.5,.3]} p={[-19.7,5.4,-29.2]} c={K.dark}/>
  </>;
}
function World({gf}:{gf:number}){
  const heatT=script.installHeatsink===null?0:smooth(clip((gf-script.installHeatsink)/40));
  return <>
    <Env/><Chip gf={gf}/>
    {BENCH.map(n=>{
      const a=arrive(gf,ARRIVE[n],[(POS[n][0]>0?1:-1)*5,9,7]);if(!a)return null;
      const Part=PART[n],base=POS[n],inst=n==='heatsink'&&heatT>0;
      const top:V3=[CHIP[0],2.45,CHIP[2]];
      const off:V3=inst?[(top[0]-base[0])*heatT,(top[1]-base[1])*heatT+Math.sin(Math.PI*heatT)*5,(top[2]-base[2])*heatT]:a.pos;
      const gl=act(gf,'highlight',n,40),ar=act(gf,'force_arrows',n,45),g=GLOW[n];
      return <group key={n} position={[base[0]+off[0],base[1]+off[1],base[2]+off[2]]} rotation-z={inst?0:a.rot}>
        <Part gf={gf}/>
        {gl>0&&<mesh position={[0,g[1]/2,0]} renderOrder={5}><boxGeometry args={g}/><meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.8} flatShading transparent opacity={.5*gl*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>}
        {ar>0&&<Arrow from={ARROW[n].from} dir={ARROW[n].dir} len={2.6} s={ar}/>}
      </group>;
    })}
    {(()=>{const g=act(gf,'highlight','chip',40);return g>0?<mesh position={[CHIP[0],CHIP[1]+1.5,CHIP[2]]} renderOrder={5}><boxGeometry args={GLOW.chip}/><meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.8} flatShading transparent opacity={.5*g*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>:null;})()}
    {(()=>{const g=act(gf,'force_arrows','chip',45);return g>0?<group position={CHIP}><Arrow from={ARROW.chip.from} dir={ARROW.chip.dir} len={3} s={g}/></group>:null;})()}
    {gf>HEAT0&&[0,1,2,3,4,5,6].map(i=>{const u=pulse(gf,90,i*13),y0=heatT>=1?5.6:2.4;return <B key={i} s={[.45,.45,.45]} p={[CHIP[0]-2.4+i*.8,y0+u*4.5,CHIP[2]+Math.sin(u*6+i)*.8]} c={i%2?K.heat:K.warm}/>;})}
  </>;
}

// ---- captions: one independent phrase at a time, white bold with a heavy black stroke, no box ------------------------------------------
const STROKE=Array.from({length:16},(_,k)=>{const a=k*Math.PI/8;return `${(4*Math.cos(a)).toFixed(1)}px ${(4*Math.sin(a)).toFixed(1)}px 0 #000`;}).join(',');
function Caption({c,f}:{c:typeof script.captions[number],f:number}){
  if(f<c.at||f>=c.until)return null;
  const term=c.style==='term',sp=spring({frame:f-c.at,fps:FPS,config:{damping:13,stiffness:170,mass:.7}}),out=ez(EZ.inout,f,c.until-5,5);
  return <div style={{position:'absolute',left:60,right:60,top:term?1660:1500,textAlign:'center',fontFamily:FONT,fontWeight:900,fontSize:term?76:64,lineHeight:1.12,
    color:term?K.term:K.white,textShadow:STROKE,opacity:clip(sp*2)*(1-out),transform:`scale(${.85+.15*sp}) translateY(${(1-sp)*18}px)`}}>{c.text}</div>;
}

export function Cpu(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:K.wall}}>
    <ThreeCanvas width={W} height={H} shadows flat camera={{fov:24,position:[0,30,60],near:.5,far:400}}>
      <color attach="background" args={[K.wall]}/><Rig gf={f}/><Sun gf={f}/><World gf={f}/>
    </ThreeCanvas>
    {script.captions.map(c=><Caption key={c.id} c={c} f={f}/>)}
  </AbsoluteFill>;
}
