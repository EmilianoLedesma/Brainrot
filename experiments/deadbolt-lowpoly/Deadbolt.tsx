import React,{useMemo} from 'react';
import {AbsoluteFill,Sequence,interpolate,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import {noise2D} from '@remotion/noise';
import * as THREE from 'three';
import script from './script.json';
import {EZ,FPS,H,W,clip,ez} from '../remotion-explainer/coffee-sci/kit';

// Silent low-poly explainer built from the updated docs/motion-graphics-recipe-lowpoly.md. Camera motion, a named ambient
// field and environmental elements are required per shot; captions are independent phrases that replace each other.
// validate() throws at load, so a render with a locked-off camera, a null ambient field or an accumulating caption fails.
// Every animated value is a pure function of useCurrentFrame() (never useFrame).
export const DEADBOLT_FRAMES=script.durationFrames;
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const K={bg:'#C6B7F2',floor:'#EBCFA0',door:'#D5DCE5',doorHi:'#E6EBF1',frame:'#EFE8DA',steel:'#C9D3DC',steelMid:'#9AA7B3',steelDark:'#6B7886',
  pinKey:'#F2F6F9',pinDriver:'#9AA7B3',backdrop:'#46515D',spring:'#D5DDE5',slot:'#3A4452',red:'#E5333B',term:'#FFD23F',white:'#FFFFFF',glow:'#BEE3FF',seam:'#5B6876'};
type V3=[number,number,number];
const h=(i:number,s:number)=>{const v=Math.sin(i*127.1+s*311.7)*43758.5453;return v-Math.floor(v);};
const C=(hex:string)=>new THREE.Color(hex);
const smooth=(t:number)=>t*t*(3-2*t);
const AMBIENT=['sheen-dust','spring-wobble-sheen'];

(function validate(){
  for(const s of script.shots){
    if(!s.ambient||!AMBIENT.includes(s.ambient.kind)||!s.ambient.moving)throw new Error(`shot ${s.id}: ambient is required and must name what moves`);
    if(!s.camera.from||!s.camera.to||JSON.stringify(s.camera.from)===JSON.stringify(s.camera.to))throw new Error(`shot ${s.id}: the camera must move`);
    if((s.type==='establishing'||s.type==='cutaway')&&s.environment.length<2)throw new Error(`shot ${s.id}: needs at least two environmental elements`);
  }
  const phrases=script.captions.filter(c=>c.style==='phrase');
  phrases.forEach((c,i)=>{
    if(c.text.split(' ').length>5)throw new Error(`caption ${c.id}: a phrase is at most five words`);
    if(i&&c.text.toLowerCase().startsWith(phrases[i-1].text.toLowerCase()))throw new Error(`caption ${c.id} accumulates on the previous phrase`);
  });
})();
const ev=(id:string)=>script.events.find(e=>e.id===id)!.at;

// ---- primitives -----------------------------------------------------------------------------------------------
const Y=new THREE.Vector3(0,1,0);
function Beam({a,b,r,color}:{a:V3,b:V3,r:number,color:string}){
  const A=new THREE.Vector3(...a),d=new THREE.Vector3(...b).sub(A),len=d.length(),dir=d.normalize();
  return <mesh position={A.clone().addScaledVector(dir,len/2).toArray()} quaternion={new THREE.Quaternion().setFromUnitVectors(Y,dir)}>
    <cylinderGeometry args={[r,r,Math.max(len,.0001),8]}/><meshStandardMaterial color={color} emissive={color} emissiveIntensity={.5} flatShading/></mesh>;
}
// Thin red arrow: force/direction only.
function Arrow({from,dir,len,s}:{from:V3,dir:V3,len:number,s:number}){
  if(s<=0)return null;
  const d=new THREE.Vector3(...dir).normalize(),A=new THREE.Vector3(...from),L=len*s,tip=A.clone().addScaledVector(d,L),q=new THREE.Quaternion().setFromUnitVectors(Y,d);
  return <group>
    <Beam a={from} b={A.clone().addScaledVector(d,Math.max(L-.1,.001)).toArray() as V3} r={.02} color={K.red}/>
    <mesh position={tip.clone().addScaledVector(d,-.07).toArray()} quaternion={q}><coneGeometry args={[.06,.14,6]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.5} flatShading/></mesh>
  </group>;
}
// Flat-shaded metal with a highlight band that travels along one axis: the "surface sheen" ambient motion.
function SheenMesh({make,f,base,axis=0,speed=.08,k=3,pos=[0,0,0],rot=[0,0,0]}:{make:()=>THREE.BufferGeometry,f:number,base:string,axis?:0|1|2,speed?:number,k?:number,pos?:V3,rot?:V3}){
  const g=useMemo(()=>{const geo=make();geo.setAttribute('color',new THREE.BufferAttribute(new Float32Array(geo.attributes.position.count*3),3));return geo;},[]);
  const p=g.attributes.position,col=g.attributes.color as THREE.BufferAttribute,b=C(base),w=C('#FFFFFF');
  for(let i=0;i<p.count;i++){const v=axis===0?p.getX(i):axis===1?p.getY(i):p.getZ(i),s=Math.sin(v*k-f*speed),t=s>.6?.7:s>.2?.35:0;
    col.setXYZ(i,b.r+(w.r-b.r)*t,b.g+(w.g-b.g)*t,b.b+(w.b-b.b)*t);}
  col.needsUpdate=true;
  return <mesh geometry={g} position={pos} rotation={rot} castShadow receiveShadow><meshStandardMaterial vertexColors flatShading/></mesh>;
}
// Suspended dust: small flat-shaded icosahedra drifting on seeded noise (never 2D sprites).
function Dust({f,center,size,seed}:{f:number,center:V3,size:V3,seed:number}){
  return <>{Array.from({length:14}).map((_,i)=>
    <mesh key={i} position={[center[0]+(h(i,seed)-.5)*size[0]+noise2D('dx'+seed+i,f*.012,i)*.35,center[1]+(h(i,seed+1)-.5)*size[1]+noise2D('dy'+seed+i,f*.012,i+7)*.3,center[2]+(h(i,seed+2)-.5)*size[2]]} rotation={[f*.01+i,f*.013,0]}>
      <icosahedronGeometry args={[.02+.025*h(i,seed+9),0]}/><meshStandardMaterial color={K.white} flatShading transparent opacity={.75} depthWrite={false}/></mesh>)}</>;
}
function Rig({s,gf}:{s:typeof script.shots[number],gf:number}){
  const {camera}=useThree(),e=ez(EZ.inout,gf,s.start,s.end-s.start-1);
  const L=(a:number[],b:number[])=>a.map((v,i)=>v+(b[i]-v)*e),p=L(s.camera.from.pos,s.camera.to.pos),t=L(s.camera.from.target,s.camera.to.target);
  camera.position.set(p[0],p[1],p[2]);(camera as THREE.PerspectiveCamera).fov=s.camera.fov;(camera as THREE.PerspectiveCamera).updateProjectionMatrix();
  camera.lookAt(t[0],t[1],t[2]);camera.updateMatrixWorld();
  return null;
}
const Lights=()=><>
  <ambientLight intensity={.45*Math.PI}/>
  <directionalLight position={[5,8,6]} intensity={.8*Math.PI} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048}
    shadow-camera-left={-9} shadow-camera-right={9} shadow-camera-top={9} shadow-camera-bottom={-9} shadow-camera-near={.5} shadow-camera-far={40} shadow-bias={-.0004}/>
</>;
const Box=({size,pos,color}:{size:V3,pos:V3,color:string})=><mesh position={pos} castShadow receiveShadow><boxGeometry args={size}/><meshStandardMaterial color={color} flatShading/></mesh>;

// ---- key: extruded profile with bitting flats; the tip is at x=0 and the blade extends to -len -------------------
type Flat={off:number,c:number};
function keyGeo(flats:Flat[],len:number){
  const s=new THREE.Shape();s.moveTo(0,-1.1);s.lineTo(0,-.95);
  [...flats].sort((a,b)=>b.off-a.off).forEach(({off,c})=>{s.lineTo(off+.2,-.95);s.lineTo(off+.09,c);s.lineTo(off-.09,c);s.lineTo(off-.2,-.95);});
  s.lineTo(-len,-.95);s.lineTo(-len,-1.1);s.closePath();
  const g=new THREE.ExtrudeGeometry(s,{depth:.2,bevelEnabled:false});g.translate(0,0,-.1);return g;
}
function Key({flats,len,tx,bow=true}:{flats:Flat[],len:number,tx:number,bow?:boolean}){
  const g=useMemo(()=>keyGeo(flats,len),[]);
  return <group position={[tx,0,0]}>
    <mesh geometry={g} castShadow><meshStandardMaterial color={K.steel} flatShading/></mesh>
    {bow&&<mesh position={[-len-.35,-.55,0]} rotation-x={Math.PI/2} castShadow><cylinderGeometry args={[.42,.42,.2,10]}/><meshStandardMaterial color={K.steelMid} flatShading/></mesh>}
  </group>;
}
const Spring=({x,y0,y1,wob}:{x:number,y0:number,y1:number,wob:number})=><>{[0,1,2,3,4].map(j=>
  <mesh key={j} position={[x,y0+(y1-y0)*(j+.5)/5+wob*(j%2?1:-1)*.4,0]} rotation-x={Math.PI/2}><torusGeometry args={[.085,.022,6,8]}/><meshStandardMaterial color={K.spring} flatShading/></mesh>)}</>;

// ---- shot 2: cutaway of the cylinder lock: five pin stacks, the key lifts them to the shear line ------------------
const PX=[-1,-.5,0,.5,1],PL=[.5,.35,.6,.4,.45],GAP=.13,TIP_END=1.35,OFFS=PX.map(x=>x-TIP_END);
const FLATS:Flat[]=PX.map((_,i)=>({off:OFFS[i],c:-PL[i]}));
const segs=(y0:number,y1:number):[number,number,number,number][]=>{
  const edges=[-1.6,...PX.flatMap(x=>[x-GAP,x+GAP]),1.6],out:[number,number,number,number][]=[];
  for(let i=0;i<edges.length;i+=2)out.push([(edges[i]+edges[i+1])/2,(y0+y1)/2,edges[i+1]-edges[i],y1-y0]);return out;
};
function Cutaway({gf,wobble}:{gf:number,wobble:boolean}){
  const push=ev('e1'),align=ev('e2'),a=ez(EZ.out,gf,align,10),tx=-4.65+(TIP_END+4.65)*ez(EZ.inout,gf,push-6,56);
  return <>
    <Box size={[4.8,4.4,.2]} pos={[.3,0,-.6]} color={K.door}/>
    <Box size={[3.2,2.7,.05]} pos={[0,-.05,-.3]} color={K.backdrop}/>
    {segs(0,1.15).map((s,i)=><Box key={'h'+i} size={[s[2],s[3],.7]} pos={[s[0],s[1],0]} color={K.steelMid}/>)}
    <Box size={[3.2,.15,.7]} pos={[0,1.225,0]} color={K.steelMid}/>
    {segs(-.1,0).map((s,i)=><Box key={'p'+i} size={[s[2],s[3],.7]} pos={[s[0],s[1],0]} color={K.steel}/>)}
    <SheenMesh make={()=>new THREE.BoxGeometry(3.2,.2,.7)} f={gf} base={K.steel} pos={[0,-1.3,0]}/>
    <Box size={[.15,1.4,.7]} pos={[1.525,-.7,0]} color={K.steel}/>
    <Box size={[.3,.8,.5]} pos={[1.75,-.7,0]} color={K.steelMid}/>
    <SheenMesh make={()=>new THREE.BoxGeometry(1.0,.28,.4)} f={gf} base={K.steel} pos={[2.4,-.7,0]}/>
    {[[-1.4,1.0],[1.4,1.0],[-1.4,-1.25],[1.4,-1.25]].map(([x,y],i)=><mesh key={i} position={[x,y,.36]} rotation-x={Math.PI/2}><cylinderGeometry args={[.07,.07,.04,6]}/><meshStandardMaterial color={K.steelDark} flatShading/></mesh>)}
    {PX.map((x,i)=>{
      const lift=smooth(clip((tx+OFFS[i]-(x-.3))/.2)),rest=-.9+PL[i],top=rest+(0-rest)*lift,drTop=top+.5,w=wobble?.015*Math.sin(gf*.15+i*1.3):0;
      return <React.Fragment key={i}>
        <Box size={[.2,PL[i],.2]} pos={[x,top-PL[i]/2,0]} color={K.pinKey}/><Box size={[.2,.5,.2]} pos={[x,top+.25,0]} color={K.pinDriver}/>
        <Spring x={x} y0={drTop} y1={1.15} wob={w}/></React.Fragment>;})}
    <Box size={[3.2,.03+.03*a,.04]} pos={[0,0,.37]} color={a>.01?K.glow:K.seam}/>
    <Key flats={FLATS} len={2.55} tx={tx}/>
    <Arrow from={[-1.5,-1.85,.4]} dir={[1,0,0]} len={.9} s={ez(EZ.out,gf,push,8)}/>
    <Dust f={gf} center={[.3,.3,.9]} size={[3.5,3,.8]} seed={4}/>
  </>;
}
// ---- shot 3: insert macro, one pin stack lining up at the shear line -----------------------------------------------
function Insert({gf,wobble}:{gf:number,wobble:boolean}){
  const t0=ev('e3'),tx=-.9+1.1*ez(EZ.inout,gf,t0,25),lift=smooth(clip((tx-.2+.3)/.2)),top=-.4+.4*lift,w=wobble?.015*Math.sin(gf*.15):0;
  return <>
    <Box size={[1.4,2.4,.05]} pos={[0,-.15,-.3]} color={K.backdrop}/>
    {[[-.415,.285],[.415,.285]].map(([x,w2],i)=><React.Fragment key={i}><Box size={[w2*2,.9,.7]} pos={[x,.45,0]} color={K.steelMid}/><Box size={[w2*2,.1,.7]} pos={[x,-.05,0]} color={K.steel}/></React.Fragment>)}
    <Box size={[1.4,.1,.7]} pos={[0,.95,0]} color={K.steelMid}/>
    <SheenMesh make={()=>new THREE.BoxGeometry(1.4,.1,.7)} f={gf} base={K.steel} pos={[0,-1.25,0]}/>
    <Box size={[.2,.5,.2]} pos={[0,top-.25,0]} color={K.pinKey}/><Box size={[.2,.5,.2]} pos={[0,top+.25,0]} color={K.pinDriver}/>
    <Spring x={0} y0={top+.5} y1={.9} wob={w}/>
    <Box size={[1.4,.03+.03*lift,.04]} pos={[0,0,.37]} color={lift>.99?K.glow:K.seam}/>
    <Key flats={[{off:-.2,c:-.5}]} len={1.6} tx={tx} bow={false}/>
    <Arrow from={[0,-1.6,.4]} dir={[0,1,0]} len={.6} s={ez(EZ.out,gf,t0,8)}/>
  </>;
}
// ---- shots 1 and 4: the door; the payoff is the bolt of the same deadbolt retracting ---------------------------------
const LOCK:V3=[.65,2.0,.09];
function Door({gf,ext,keyAng,showKey,dust}:{gf:number,ext:number,keyAng:number,showKey:boolean,dust:boolean}){
  const bx=.55+.6*ext;
  return <>
    <mesh position={[0,3,-.7]} receiveShadow><planeGeometry args={[40,20]}/><meshStandardMaterial color={K.bg} flatShading/></mesh>
    <mesh rotation-x={-Math.PI/2} position={[0,0,2]} receiveShadow><planeGeometry args={[30,12]}/><meshStandardMaterial color={K.floor} flatShading/></mesh>
    <Box size={[.3,4.1,.35]} pos={[-1.3,2.05,.075]} color={K.frame}/><Box size={[.3,4.1,.35]} pos={[1.6,2.05,.075]} color={K.frame}/><Box size={[3.2,.3,.35]} pos={[.15,3.95,.075]} color={K.frame}/>
    <Box size={[2.15,3.8,.15]} pos={[-.075,1.9,0]} color={K.door}/>
    <Box size={[1.6,1.3,.04]} pos={[-.1,2.9,.09]} color={K.doorHi}/><Box size={[1.6,1.3,.04]} pos={[-.1,.95,.09]} color={K.doorHi}/>
    <Box size={[.04,.7,.3]} pos={[1.43,2,.02]} color={K.steelMid}/><Box size={[.05,.22,.2]} pos={[1.45,2,.02]} color={K.slot}/>
    <SheenMesh make={()=>new THREE.BoxGeometry(.8,.24,.14)} f={gf} base={K.steel} pos={[bx,2,0]}/>
    <mesh position={[LOCK[0],1.35,.1]} rotation-x={Math.PI/2} castShadow><cylinderGeometry args={[.25,.25,.05,10]}/><meshStandardMaterial color={K.steelMid} flatShading/></mesh>
    <SheenMesh make={()=>new THREE.IcosahedronGeometry(.15,1)} f={gf} base={K.steel} pos={[LOCK[0],1.35,.22]}/>
    <mesh position={LOCK} rotation-x={Math.PI/2} castShadow><cylinderGeometry args={[.32,.32,.05,12]}/><meshStandardMaterial color={K.steelMid} flatShading/></mesh>
    <SheenMesh make={()=>new THREE.CylinderGeometry(.2,.2,.08,12)} f={gf} base={K.steel} pos={[LOCK[0],LOCK[1],LOCK[2]+.04]} rot={[Math.PI/2,0,0]}/>
    <group position={[LOCK[0],LOCK[1],LOCK[2]+.1]} rotation-z={-keyAng}>
      <Box size={[.04,.22,.02]} pos={[0,0,0]} color={K.slot}/>
      {showKey&&<><Box size={[.07,.3,.05]} pos={[0,.12,.06]} color={K.steelMid}/>
        <mesh position={[0,.34,.06]} rotation-x={Math.PI/2}><cylinderGeometry args={[.17,.17,.05,10]}/><meshStandardMaterial color={K.steelMid} flatShading/></mesh></>}
    </group>
    {showKey&&<Arrow from={[1.18,2.15,.35]} dir={[0,-1,0]} len={.45} s={ez(EZ.out,gf,ev('e4'),8)}/>}
    {showKey&&<Arrow from={[1.35,2.4,.2]} dir={[-1,0,0]} len={.6} s={ez(EZ.out,gf,ev('e5'),8)}/>}
    {dust&&<Dust f={gf} center={[.2,2,1.4]} size={[4,4,2.5]} seed={2}/>}
  </>;
}
function Scene({i,gf}:{i:number,gf:number}){
  const s=script.shots[i],amb=s.ambient.kind,dust=amb.includes('dust'),wobble=amb.includes('spring-wobble');
  if(s.id==='s1')return <Cutaway gf={gf} wobble={wobble}/>;
  if(s.id==='s2')return <Insert gf={gf} wobble={wobble}/>;
  if(s.id==='s3')return <Door gf={gf} ext={1-ez(EZ.inout,gf,ev('e5'),18)} keyAng={ez(EZ.inout,gf,ev('e4'),16)*Math.PI/2} showKey dust={dust}/>;
  return <Door gf={gf} ext={1} keyAng={0} showKey={false} dust={dust}/>;
}
function Shot({i}:{i:number}){
  const s=script.shots[i],local=useCurrentFrame(),gf=s.start+local;
  return <ThreeCanvas width={W} height={H} shadows flat camera={{fov:s.camera.fov,position:s.camera.from.pos as V3,near:.1,far:80}}>
    <color attach="background" args={[K.bg]}/><Rig s={s} gf={gf}/><Lights/><Scene i={i} gf={gf}/>
  </ThreeCanvas>;
}

// ---- captions: one independent phrase at a time, white bold with a heavy black stroke, no box -----------------------
const STROKE=Array.from({length:16},(_,k)=>{const a=k*Math.PI/8;return `${(4*Math.cos(a)).toFixed(1)}px ${(4*Math.sin(a)).toFixed(1)}px 0 #000`;}).join(',');
function Caption({c,f}:{c:typeof script.captions[number],f:number}){
  if(f<c.at||f>=c.until)return null;
  const term=c.style==='term',sp=spring({frame:f-c.at,fps:FPS,config:{damping:13,stiffness:170,mass:.7}}),out=ez(EZ.inout,f,c.until-6,6);
  return <div style={{position:'absolute',left:60,right:60,top:term?1640:1480,textAlign:'center',fontFamily:FONT,fontWeight:900,fontSize:term?76:64,lineHeight:1.12,
    color:term?K.term:K.white,textShadow:STROKE,opacity:clip(sp*2)*(1-out),transform:`scale(${.8+.2*sp}) translateY(${(1-sp)*24}px)`}}>{c.text}</div>;
}

export function Deadbolt(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:K.bg}}>
    {script.shots.map((s,i)=><Sequence key={s.id} from={s.start} durationInFrames={s.end-s.start} layout="none"><Shot i={i}/></Sequence>)}
    {script.captions.map(c=><Caption key={c.id} c={c} f={f}/>)}
  </AbsoluteFill>;
}
