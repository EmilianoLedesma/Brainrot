import React from 'react';
import {AbsoluteFill,Sequence,interpolate,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import {noise2D} from '@remotion/noise';
import * as THREE from 'three';
import script from './script.json';
import {EZ,FPS,H,W,clip,ez} from '../remotion-explainer/coffee-sci/kit';

// Silent low-poly explainer built from docs/motion-graphics-recipe-lowpoly.md: four shot types cut hard on caption
// beats, each shot with its own camera and its own ThreeCanvas. Every animated value is a pure function of
// useCurrentFrame() (never useFrame). Script in script.json (shots[], captions[], events[]).
export const SKY_FRAMES=script.durationFrames;
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const K={sky:'#58AEF7',blue:'#1E4BD8',blueHi:'#9CC8FF',red:'#E5333B',orange:'#FF8A2B',term:'#FFD23F',white:'#FFFFFF',cloud:'#FFFFFF',
  grass:'#7BC47F',grassFar:'#8AD08A',grassDeep:'#6DB872',tree:'#2E8B57',trunk:'#8B5A2B',sun:'#FFF4DC',mol:'#E9EDF2',dot:'#C4CCD6',pupil:'#12161C'};
const h=(i:number,s:number)=>{const v=Math.sin(i*127.1+s*311.7)*43758.5453;return v-Math.floor(v);};
type V3=[number,number,number];

// Event frame = the frame where the named caption word first appears (silent video: the caption is the "narration").
const cap=(id:string)=>script.captions.find(c=>c.id===id)!;
const norm=(w:string)=>w.toLowerCase().replace(/[^\p{L}]/gu,'');
const evAt=(id:string)=>{
  const e=script.events.find(x=>x.id===id)!,c=cap(e.caption),i=c.text.split(' ').findIndex(w=>norm(w)===e.word);
  if(i<0)throw new Error(`event ${id}: word "${e.word}" not in caption ${e.caption}`);
  return c.at+i*c.wordGap;
};

// ---- primitives ----------------------------------------------------------------------------------------------
const Y=new THREE.Vector3(0,1,0);
function Beam({a,b,r,color,progress=1,opacity=1,emissive=.9}:{a:V3,b:V3,r:number,color:string,progress?:number,opacity?:number,emissive?:number}){
  if(progress<=0||opacity<=0)return null;
  const A=new THREE.Vector3(...a),d=new THREE.Vector3(...b).sub(A),len=d.length()*progress,dir=d.normalize();
  const c=A.clone().addScaledVector(dir,len/2),q=new THREE.Quaternion().setFromUnitVectors(Y,dir);
  return <mesh position={c.toArray()} quaternion={q}><cylinderGeometry args={[r,r,Math.max(len,.0001),8]}/>
    <meshStandardMaterial color={color} emissive={color} emissiveIntensity={emissive} flatShading transparent={opacity<1} opacity={opacity}/></mesh>;
}
// Thin red force/direction arrow: the only use of red in the video.
function Arrow({from,dir,len,s}:{from:V3,dir:V3,len:number,s:number}){
  if(s<=0)return null;
  const d=new THREE.Vector3(...dir).normalize(),A=new THREE.Vector3(...from),L=len*s,tip=A.clone().addScaledVector(d,L),q=new THREE.Quaternion().setFromUnitVectors(Y,d);
  return <group>
    <Beam a={from} b={A.clone().addScaledVector(d,Math.max(L-.1,.001)).toArray() as V3} r={.014} color={K.red} emissive={.5}/>
    <mesh position={tip.clone().addScaledVector(d,-.06).toArray()} quaternion={q}><coneGeometry args={[.045,.12,6]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.5} flatShading/></mesh>
  </group>;
}
function Rig({cam}:{cam:{pos:number[],target:number[],fov:number}}){
  const {camera}=useThree();
  camera.position.set(cam.pos[0],cam.pos[1],cam.pos[2]);
  (camera as THREE.PerspectiveCamera).fov=cam.fov;(camera as THREE.PerspectiveCamera).updateProjectionMatrix();
  camera.lookAt(cam.target[0],cam.target[1],cam.target[2]);camera.updateMatrixWorld();
  return null;
}
const Lights=({shadows=false}:{shadows?:boolean})=><>
  <ambientLight intensity={.45*Math.PI}/>
  <directionalLight position={[5,8,6]} intensity={.8*Math.PI} castShadow={shadows} shadow-mapSize-width={2048} shadow-mapSize-height={2048}
    shadow-camera-left={-12} shadow-camera-right={12} shadow-camera-top={12} shadow-camera-bottom={-12} shadow-camera-near={.5} shadow-camera-far={50} shadow-bias={-.0004}/>
</>;

// ---- shot 1 / 5: establishing --------------------------------------------------------------------------------
const CLOUDS:{p:V3,v:number,s:number}[]=[{p:[-1.8,4.6,-3],v:.004,s:1},{p:[.2,5.3,-5],v:.003,s:1.2},{p:[2.2,3.9,-4],v:.0045,s:.9}];
const CLOUD_PARTS:[number,number,number,number][]=[[0,0,0,.55],[.6,-.1,.1,.42],[-.6,-.05,0,.4],[.25,.3,0,.4],[-.25,.25,.1,.35]];
function Establishing({gf}:{gf:number}){
  return <>
    <mesh rotation-x={-Math.PI/2} position={[0,0,-4]} receiveShadow><planeGeometry args={[40,22]}/><meshStandardMaterial color={K.grass} flatShading/></mesh>
    {([[-1.6,-2,3.2,1.6,2,K.grass],[2.4,-3,3.6,2.2,2.4,K.grassDeep],[0,-5.5,6,2.8,3,K.grassFar]] as [number,number,number,number,number,string][]).map(([x,z,sx,sy,sz,c],i)=>
      <mesh key={i} position={[x,0,z]} scale={[sx,sy,sz]} castShadow receiveShadow><sphereGeometry args={[1,8,4,0,Math.PI*2,0,Math.PI/2]}/><meshStandardMaterial color={c} flatShading/></mesh>)}
    {([[-2,.2,1.1],[1.5,-.3,.9],[2.3,.4,1.2]] as [number,number,number][]).map(([x,z,s],i)=>
      <group key={i} position={[x,0,z]} scale={s} rotation-z={.03*Math.sin(gf*.05+i*2)}>
        <mesh position-y={.2} castShadow><cylinderGeometry args={[.08,.1,.4,5]}/><meshStandardMaterial color={K.trunk} flatShading/></mesh>
        <mesh position-y={.95} castShadow><coneGeometry args={[.45,1.2,6]}/><meshStandardMaterial color={K.tree} flatShading/></mesh></group>)}
    <mesh position={[1.7,6.6,-4]} rotation={[gf*.004,gf*.01,0]}><icosahedronGeometry args={[.7,1]}/><meshStandardMaterial color={K.sun} emissive={K.sun} emissiveIntensity={.8} flatShading/></mesh>
    {CLOUDS.map((c,i)=><group key={i} position={[c.p[0]+c.v*gf,c.p[1]+.05*Math.sin(gf*.03+i),c.p[2]]} scale={c.s}>
      {CLOUD_PARTS.map((q,k)=><mesh key={k} position={[q[0],q[1],q[2]]} scale={[1,.8,1]} rotation={[k,k*2,0]}><icosahedronGeometry args={[q[3],1]}/><meshStandardMaterial color={K.cloud} flatShading/></mesh>)}</group>)}
  </>;
}

// ---- shot 2: cutaway interior (atmosphere column + white beam that turns out to be composed) -------------------
const BA:V3=[3.4,2.9,.1],BB:V3=[-3.0,-2.4,.1],STRIPES=['#FFC8A2','#FFE9D6','#FFFFFF','#CFE6FF','#CDBFFF'];
function Cutaway({gf}:{gf:number}){
  const start=script.shots[1].start,t=gf-start,ev=evAt('composed'),grow=ez(EZ.out,gf,start+2,16);
  const dir=new THREE.Vector3(...BB).sub(new THREE.Vector3(...BA)).normalize(),perp=new THREE.Vector3(-dir.y,dir.x,0);
  const spread=ez(EZ.inout,gf,ev,10),single=gf<ev;
  return <>
    <mesh><boxGeometry args={[2.4,5.2,.5]}/><meshStandardMaterial color="#DCEBFF" transparent opacity={.2} depthWrite={false} flatShading/></mesh>
    {([[0,2.6,2.4,.05],[0,-2.6,2.4,.05],[-1.2,0,.05,5.2],[1.2,0,.05,5.2]] as [number,number,number,number][]).map(([x,y,w,hh],i)=>
      <mesh key={i} position={[x,y,0]}><boxGeometry args={[w,hh,.06]}/><meshStandardMaterial color="#FFFFFF" flatShading/></mesh>)}
    {Array.from({length:70}).map((_,i)=>{
      const x=(h(i,1)-.5)*2.1+noise2D('mx'+i,gf*.03,i)*.07,y=(h(i,2)-.5)*4.8+noise2D('my'+i,gf*.03,i+9)*.07,z=(h(i,3)-.5)*.3,r=.035+h(i,4)*.035;
      return <mesh key={i} position={[x,y,z]} rotation={[gf*.01+i,gf*.013,0]}><icosahedronGeometry args={[r,0]}/><meshStandardMaterial color={i%2?K.dot:K.white} flatShading/></mesh>;})}
    {single
      ?<Beam a={BA} b={BB} r={.11} color={K.white} progress={grow} opacity={.92+.08*Math.sin(t*.4)}/>
      :STRIPES.map((c,i)=>{const o=(i-2)*.06*spread,off=perp.clone().multiplyScalar(o);
        return <Beam key={i} a={[BA[0]+off.x,BA[1]+off.y,BA[2]]} b={[BB[0]+off.x,BB[1]+off.y,BB[2]]} r={.036} color={c} opacity={.95+.05*Math.sin(t*.4+i)}/>;})}
  </>;
}

// ---- shot 3: insert macro (one molecule, beam splits: blue scatters, orange carries on) --------------------------
const BLUE_DEG=[100,160,275,335],IN_DEG=38,OUT_DEG=IN_DEG+180+7;
const ang=(deg:number):V3=>[Math.cos(deg*Math.PI/180),Math.sin(deg*Math.PI/180),0];
function Macro({gf}:{gf:number}){
  const ev=evAt('split'),jit:V3=[noise2D('jx',gf*.08,1)*.012,noise2D('jy',gf*.08,2)*.012,0],S=ez(EZ.out,gf,ev,8),R=.38;
  const inD=ang(IN_DEG),outD=ang(OUT_DEG);
  return <>
    <mesh position={jit} rotation={[gf*.01,gf*.02,0]}><icosahedronGeometry args={[R,1]}/><meshStandardMaterial color={K.mol} flatShading/></mesh>
    <Beam a={[inD[0]*3.2,inD[1]*3.2,0]} b={[inD[0]*R*.95,inD[1]*R*.95,0]} r={.07} color={K.white} progress={ez(EZ.out,gf,152,10)} opacity={.93+.07*Math.sin(gf*.5)}/>
    {S>0&&<Beam a={[outD[0]*R,outD[1]*R,0]} b={[outD[0]*3,outD[1]*3,0]} r={.05} color={K.orange} progress={S}/>}
    {S>0&&<Arrow from={[outD[0]*1.1-outD[1]*.14,outD[1]*1.1+outD[0]*.14,0]} dir={outD} len={.55} s={S}/>}
    {BLUE_DEG.map((d,j)=>{
      const u=ang(d),period=20,ph=gf<ev?-1:((gf-ev-j*4)%period+period)%period,p=ph/period;
      return <React.Fragment key={j}>
        {ph>=0&&gf>=ev+j*4&&<Beam a={[u[0]*(R+.2+p*.9),u[1]*(R+.2+p*.9),0]} b={[u[0]*(R+.6+p*.9),u[1]*(R+.6+p*.9),0]} r={.05} color={K.blue} opacity={1-clip((p-.7)/.3)}/>}
        <Arrow from={[u[0]*.8-u[1]*.14,u[1]*.8+u[0]*.14,0]} dir={u} len={.4} s={ez(EZ.out,gf,ev+j*2,8)}/>
      </React.Fragment>;})}
  </>;
}

// ---- shot 4: metaphor cutaway (simplified eye: scattered blue light reaches the pupil from every direction) ----
const SRC:V3[]=[[-1.1,1.5,.7],[1.2,1.6,.7],[-1.2,-1.5,.7],[1.1,-1.5,.7]],PUPIL:V3=[0,0,.7];
function Eye({gf}:{gf:number}){
  const ev=evAt('converge');
  return <>
    <group scale={.75} rotation-z={.03*Math.sin(gf*.04)}>
      <mesh scale={[1.5,1,.55]}><sphereGeometry args={[1,12,8]}/><meshStandardMaterial color="#F1F3F6" flatShading/></mesh>
      <mesh position-z={.57}><circleGeometry args={[.52,10]}/><meshStandardMaterial color="#AEB6C0" flatShading/></mesh>
      <mesh position-z={.58} scale={1+.05*Math.sin(gf*.1)}><circleGeometry args={[.27,10]}/><meshStandardMaterial color={K.pupil} flatShading/></mesh>
    </group>
    {SRC.map((s,j)=>{
      const g=ez(EZ.out,gf,ev+j*2,12);if(g<=0)return null;
      const pulse=((gf-ev-j*2)%24+24)%24/24,pa:V3=[s[0]+(PUPIL[0]-s[0])*Math.max(0,pulse-.12),s[1]+(PUPIL[1]-s[1])*Math.max(0,pulse-.12),.72],pb:V3=[s[0]+(PUPIL[0]-s[0])*pulse,s[1]+(PUPIL[1]-s[1])*pulse,.72];
      return <React.Fragment key={j}><Beam a={s} b={PUPIL} r={.035} color={K.blue} progress={g}/><Beam a={pa} b={pb} r={.05} color={K.blueHi} opacity={g}/></React.Fragment>;})}
  </>;
}

// ---- shots and captions --------------------------------------------------------------------------------------
function Shot({i}:{i:number}){
  const s=script.shots[i],local=useCurrentFrame(),gf=s.start+local;
  return <ThreeCanvas width={W} height={H} shadows flat camera={{fov:s.camera.fov,position:s.camera.pos as V3,near:.1,far:80}}>
    <color attach="background" args={[K.sky]}/><Rig cam={s.camera}/><Lights shadows={s.type==='establishing'}/>
    {s.type==='establishing'&&<Establishing gf={gf}/>}{s.type==='cutaway'&&<Cutaway gf={gf}/>}
    {s.type==='insert'&&<Macro gf={gf}/>}{s.type==='metaphor'&&<Eye gf={gf}/>}
  </ThreeCanvas>;
}
// Heavy black stroke without a background box: 16 hard text-shadows around each glyph.
const STROKE=Array.from({length:16},(_,k)=>{const a=k*Math.PI/8;return `${(4*Math.cos(a)).toFixed(1)}px ${(4*Math.sin(a)).toFixed(1)}px 0 #000`;}).join(',');
function Caption({c,f}:{c:typeof script.captions[number],f:number}){
  if(f<c.at||f>=c.until)return null;
  const out=ez(EZ.inout,f,c.until-6,6),color=c.style==='term'?K.term:K.white;
  return <div style={{position:'absolute',left:60,right:60,top:c.y,textAlign:'center',fontFamily:FONT,fontWeight:900,fontSize:c.size,lineHeight:1.12,color,textShadow:STROKE,opacity:1-out}}>
    {c.text.split(' ').map((w,i)=>{const t=f-(c.at+i*c.wordGap),sp=spring({frame:t,fps:FPS,config:{damping:13,stiffness:170,mass:.7}});
      return <span key={i} style={{display:'inline-block',margin:'0 .14em',opacity:t>=0?1:0,transform:`scale(${.7+.3*sp}) translateY(${(1-sp)*20}px)`}}>{w}</span>;})}
  </div>;
}

export function SkyBlue(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:K.sky}}>
    {script.shots.map((s,i)=><Sequence key={s.id} from={s.start} durationInFrames={s.end-s.start} layout="none"><Shot i={i}/></Sequence>)}
    {script.captions.map(c=><Caption key={c.id} c={c} f={f}/>)}
  </AbsoluteFill>;
}
