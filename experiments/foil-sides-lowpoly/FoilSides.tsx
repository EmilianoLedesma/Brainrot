import React,{useEffect} from 'react';
import {AbsoluteFill,Sequence,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import script from './script.json';
import {EZ,FPS,H,W,clip,ez} from '../remotion-explainer/coffee-sci/kit';

// Silent low-poly explainer built from docs/motion-graphics-recipe-lowpoly.md. The hero is a foil sheet with a shiny
// and a matte face. Shots, events and captions come from script.json (built from the planner's plan.json); this file only
// interprets them. Every animated value is a pure function of useCurrentFrame() (never useFrame).
export const FOIL_FRAMES=script.durationFrames;
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const K={bg:'#8FE3C0',counter:'#F28F7B',white:'#FFFFFF',shinyLo:'#BFD3E2',shinyHi:'#FFFFFF',matte:'#A9B1B9',section:'#7F8A94',
  steel:'#CBD8E3',steelDark:'#8FA3B5',core:'#C9A36B',red:'#E5333B',term:'#FFD23F'};
type V3=[number,number,number];type P2=[number,number];
const h=(i:number,s:number)=>{const v=Math.sin(i*127.1+s*311.7)*43758.5453;return v-Math.floor(v);};
const C=(hex:string)=>new THREE.Color(hex);
const DS=THREE.DoubleSide;

// ---- primitives (same conventions as sky-blue-lowpoly) -----------------------------------------------------------
const Y=new THREE.Vector3(0,1,0);
function Beam({a,b,r,color,emissive=.5}:{a:V3,b:V3,r:number,color:string,emissive?:number}){
  const A=new THREE.Vector3(...a),d=new THREE.Vector3(...b).sub(A),len=d.length(),dir=d.normalize();
  return <mesh position={A.clone().addScaledVector(dir,len/2).toArray()} quaternion={new THREE.Quaternion().setFromUnitVectors(Y,dir)}>
    <cylinderGeometry args={[r,r,Math.max(len,.0001),8]}/><meshStandardMaterial color={color} emissive={color} emissiveIntensity={emissive} flatShading/></mesh>;
}
// Thin red force/direction arrow: the only use of red in the video.
function Arrow({from,dir,len,s}:{from:V3,dir:V3,len:number,s:number}){
  if(s<=0)return null;
  const d=new THREE.Vector3(...dir).normalize(),A=new THREE.Vector3(...from),L=len*s,tip=A.clone().addScaledVector(d,L),q=new THREE.Quaternion().setFromUnitVectors(Y,d);
  return <group>
    <Beam a={from} b={A.clone().addScaledVector(d,Math.max(L-.1,.001)).toArray() as V3} r={.02} color={K.red}/>
    <mesh position={tip.clone().addScaledVector(d,-.07).toArray()} quaternion={q}><coneGeometry args={[.06,.14,6]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.5} flatShading/></mesh>
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

// ---- the hero: a foil sheet swept along a 2D profile, shiny on one face and matte on the other -------------------
type ColorFn=(x:number,i:number)=>THREE.Color;
function sheetGeo(pts:P2[],w:number,t:number,top:ColorFn,bot:ColorFn){
  const n=pts.length,z=w/2;
  const nrm=pts.map((_,i)=>{const a=pts[Math.max(0,i-1)],b=pts[Math.min(n-1,i+1)],tx=b[0]-a[0],ty=b[1]-a[1],l=Math.hypot(tx,ty)||1;return [-ty/l,tx/l] as P2;});
  const off=(sd:number)=>pts.map((p,i)=>[p[0]+nrm[i][0]*t/2*sd,p[1]+nrm[i][1]*t/2*sd] as P2);
  const T=off(1),B=off(-1);
  const quads=()=>{const idx:number[]=[];for(let i=0;i<n-1;i++){const a=i*2;idx.push(a,a+1,a+2,a+2,a+1,a+3);}return idx;};
  const build=(pos:number[],col:number[])=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
    g.setAttribute('color',new THREE.Float32BufferAttribute(col,3));g.setIndex(quads());g.computeVertexNormals();return g;};
  const face=(P:P2[],fn:ColorFn)=>{const pos:number[]=[],col:number[]=[];P.forEach((p,i)=>{const c=fn(p[0],i);pos.push(p[0],p[1],-z,p[0],p[1],z);col.push(c.r,c.g,c.b,c.r,c.g,c.b);});return build(pos,col);};
  const sc=C(K.section),pos:number[]=[],col:number[]=[];
  for(let i=0;i<n;i++){pos.push(T[i][0],T[i][1],z,B[i][0],B[i][1],z);col.push(sc.r,sc.g,sc.b,sc.r,sc.g,sc.b);}
  return [face(T,top),face(B,bot),build(pos,col)];
}
function Sheet({pts,w,t,top,bot,pos=[0,0,0],rot=[0,0,0]}:{pts:P2[],w:number,t:number,top:ColorFn,bot:ColorFn,pos?:V3,rot?:V3}){
  const geos=sheetGeo(pts,w,t,top,bot);
  useEffect(()=>()=>geos.forEach(g=>g.dispose()),[geos]);
  return <group position={pos} rotation={rot}>{geos.map((g,i)=><mesh key={i} geometry={g} castShadow receiveShadow>
    <meshStandardMaterial vertexColors flatShading side={DS}/></mesh>)}</group>;
}
const flat=(x0:number,x1:number,n:number):P2[]=>Array.from({length:n},(_,i)=>[x0+(x1-x0)*i/(n-1),0] as P2);
// Shiny face: facets with a highlight band that travels along the sheet. Matte face: flat grey with a faint grain.
const shinyFn=(f:number,speed=.07,k=2.2):ColorFn=>x=>{const s=Math.sin(x*k-f*speed);return new THREE.Color().lerpColors(C(K.shinyLo),C(K.shinyHi),s>.55?1:s>.1?.55:0);};
const matteFn:ColorFn=(_x,i)=>C(K.matte).multiplyScalar(.96+.08*h(i,5));

function Roller({pos,r,len,spin}:{pos:V3,r:number,len:number,spin:number}){
  return <group position={pos} rotation-z={spin}>
    <mesh rotation-x={Math.PI/2} castShadow><cylinderGeometry args={[r,r,len,14]}/><meshStandardMaterial color={K.steel} flatShading/></mesh>
    {[0,1,2].map(k=><mesh key={k} position-z={len/2+.012} rotation-z={k*Math.PI/3}><boxGeometry args={[r*1.7,.07,.02]}/><meshStandardMaterial color={K.steelDark} flatShading/></mesh>)}
  </group>;
}

// ---- shots -----------------------------------------------------------------------------------------------------
function Establishing({gf}:{gf:number}){
  const n=30,L=1.6,k=.9+.35*Math.sin(gf*.03),pts:P2[]=[[0,.03]];let x=0,y=.03;
  for(let i=1;i<n;i++){const s=i/n,a=s>.75?k*(s-.75)*4:0;x+=L/n*Math.cos(a);y+=L/n*Math.sin(a);pts.push([x,y]);}
  const cols=Array.from({length:21},(_,i)=>(i-10)*.8),rows=Array.from({length:8},(_,j)=>j*.8);
  return <>
    <mesh rotation-x={-Math.PI/2} position={[0,0,-1]} receiveShadow><planeGeometry args={[30,14]}/><meshStandardMaterial color={K.counter} flatShading/></mesh>
    <mesh position={[0,3,-3]} receiveShadow><planeGeometry args={[30,8]}/><meshStandardMaterial color={K.bg} flatShading/></mesh>
    {cols.map((cx,i)=><mesh key={'c'+i} position={[cx,3,-2.97]}><boxGeometry args={[.04,8,.04]}/><meshStandardMaterial color={K.white} flatShading/></mesh>)}
    {rows.map((ry,j)=><mesh key={'r'+j} position={[0,ry,-2.97]}><boxGeometry args={[30,.04,.04]}/><meshStandardMaterial color={K.white} flatShading/></mesh>)}
    <group position={[0,.5,0]} rotation-z={-gf*.012}>
      <mesh rotation-x={Math.PI/2} castShadow><cylinderGeometry args={[.5,.5,1.5,14]}/><meshStandardMaterial color="#DDE8F1" flatShading/></mesh>
      {[-1,1].map(sd=><mesh key={sd} position-z={sd*.76} rotation-x={Math.PI/2}><cylinderGeometry args={[.2,.2,.04,10]}/><meshStandardMaterial color={K.core} flatShading/></mesh>)}
    </group>
    <Sheet pts={pts} w={1.5} t={.025} top={shinyFn(gf)} bot={matteFn}/>
  </>;
}
// cutaway, event force_arrows: the sheet is squeezed thinner while red arrows press on it.
function Squeeze({gf,ev}:{gf:number,ev:number}){
  const tk=.5-.4*ez(EZ.inout,gf,ev,24),s=ez(EZ.out,gf,ev,8),bob=.06*Math.sin(gf*.3);
  return <>
    <Sheet pts={flat(-.8,.8,24)} w={.8} t={tk} top={shinyFn(gf)} bot={matteFn}/>
    <Arrow from={[0,1.15+bob,.1]} dir={[0,-1,0]} len={.6} s={s}/><Arrow from={[0,-1.15-bob,.1]} dir={[0,1,0]} len={.6} s={s}/>
  </>;
}
// cutaway, event split: two laminated sheets separate; the faces that were pressed together are matte, the outer ones shiny.
function Split({gf,ev}:{gf:number,ev:number}){
  const sp=ez(EZ.inout,gf,ev,22);
  return <>
    <Sheet pts={flat(-.9,.9,20)} w={.9} t={.2} top={shinyFn(gf)} bot={matteFn} pos={[sp*.35,.11+sp*.95,sp*.1]} rot={[sp*.25,0,-sp*.3]}/>
    <Sheet pts={flat(-.9,.9,20)} w={.9} t={.2} top={matteFn} bot={shinyFn(gf)} pos={[0,-.11,0]}/>
  </>;
}
// cutaway, event curl: a corner of the sheet curls over to show its other face.
function Curl({gf,ev}:{gf:number,ev:number}){
  const c=ez(EZ.inout,gf,ev,36),n=40,L=1.8,pts:P2[]=[[-.9,0]];let x=-.9,y=0;
  for(let i=1;i<n;i++){const s=i/n,a=(s>.5?c*(s-.5)*8:0)+.04*Math.sin(gf*.06+s*4);x+=L/n*Math.cos(a);y+=L/n*Math.sin(a);pts.push([x,y]);}
  return <Sheet pts={pts} w={.8} t={.1} top={shinyFn(gf)} bot={matteFn}/>;
}
// metaphor: cross-section of the rolling mill, two sheets pass together between polished rollers.
function Mill({gf,ev}:{gf:number,ev:number}){
  const s=ez(EZ.out,gf,ev,10),parts:[number,number,number][]=[[-2.2,-.45,.11],[-.45,.45,.07],[.45,2.2,.06]];
  return <>
    <Roller pos={[0,.57,0]} r={.5} len={1.3} spin={-gf*.05}/><Roller pos={[0,-.57,0]} r={.5} len={1.3} spin={gf*.05}/>
    {parts.map(([x0,x1,t],i)=><React.Fragment key={i}>
      <Sheet pts={flat(x0,x1,12)} w={.9} t={t} top={shinyFn(gf,.09)} bot={matteFn} pos={[0,t/2,0]}/>
      <Sheet pts={flat(x0,x1,12)} w={.9} t={t} top={matteFn} bot={shinyFn(gf,.09)} pos={[0,-t/2,0]}/></React.Fragment>)}
    {[-1.6,.8,1.4].map((ax,i)=><Arrow key={i} from={[ax,.45,0]} dir={[1,0,0]} len={.55} s={ez(EZ.out,gf,ev+i*3,8)}/>)}
  </>;
}
// insert: a polished roller on the sheet; the face that passes under it comes out shiny.
function Insert({gf}:{gf:number}){
  const fn:ColorFn=(x,i)=>{const t=clip(x/.3+.5);return new THREE.Color().lerpColors(matteFn(x,i),shinyFn(gf,.05)(x,i),t);};
  return <>
    <Roller pos={[0,.66,0]} r={.6} len={1.2} spin={gf*.04}/>
    <Sheet pts={flat(-1.4,1.4,28)} w={.9} t={.06} top={fn} bot={matteFn}/>
  </>;
}
function Scene({i,gf}:{i:number,gf:number}){
  const s=script.shots[i],e=script.events.find(x=>x.shot===s.id),ev=e?e.at:s.start+30;
  if(s.type==='establishing')return <Establishing gf={gf}/>;
  if(s.type==='metaphor')return <Mill gf={gf} ev={ev}/>;
  if(s.type==='insert')return <Insert gf={gf}/>;
  if(e?.kind==='split')return <Split gf={gf} ev={ev}/>;
  if(e?.kind==='curl')return <Curl gf={gf} ev={ev}/>;
  return <Squeeze gf={gf} ev={ev}/>;
}
function Shot({i}:{i:number}){
  const s=script.shots[i],local=useCurrentFrame(),gf=s.start+local;
  return <ThreeCanvas width={W} height={H} shadows flat camera={{fov:s.camera.fov,position:s.camera.pos as V3,near:.1,far:80}}>
    <color attach="background" args={[K.bg]}/><Rig cam={s.camera}/><Lights shadows={s.type==='establishing'}/><Scene i={i} gf={gf}/>
  </ThreeCanvas>;
}

// ---- captions: white bold, heavy black stroke, no background box; the yellow term callout holds longer ------------
const STROKE=Array.from({length:16},(_,k)=>{const a=k*Math.PI/8;return `${(4*Math.cos(a)).toFixed(1)}px ${(4*Math.sin(a)).toFixed(1)}px 0 #000`;}).join(',');
function Caption({c,f}:{c:typeof script.captions[number],f:number}){
  if(f<c.at||f>=c.until)return null;
  const out=ez(EZ.inout,f,c.until-6,6),color=c.style==='term'?K.term:K.white;
  return <div style={{position:'absolute',left:60,right:60,top:c.y,textAlign:'center',fontFamily:FONT,fontWeight:900,fontSize:c.size,lineHeight:1.12,color,textShadow:STROKE,opacity:1-out}}>
    {c.words.map((w,i)=>{const t=f-w.at,sp=spring({frame:t,fps:FPS,config:{damping:13,stiffness:170,mass:.7}});
      return <span key={i} style={{display:'inline-block',margin:'0 .14em',opacity:t>=0?1:0,transform:`scale(${.7+.3*sp}) translateY(${(1-sp)*20}px)`}}>{w.text}</span>;})}
  </div>;
}

export function FoilSides(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:K.bg}}>
    {script.shots.map((s,i)=><Sequence key={s.id} from={s.start} durationInFrames={s.end-s.start} layout="none"><Shot i={i}/></Sequence>)}
    {script.captions.map(c=><Caption key={c.id} c={c} f={f}/>)}
  </AbsoluteFill>;
}
