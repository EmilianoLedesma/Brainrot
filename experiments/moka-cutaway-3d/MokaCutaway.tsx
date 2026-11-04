import React,{useLayoutEffect,useMemo,useRef} from 'react';
import {AbsoluteFill,interpolate,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import {noise2D} from '@remotion/noise';
import * as THREE from 'three';
import script from './script.json';
import {EZ,FPS,H,W,clip,ez} from '../remotion-explainer/coffee-sci/kit';

// Silent low-poly 3D cutaway built with @remotion/three. Every animated value is a pure function of useCurrentFrame()
// (never useFrame), flat-shaded MeshStandardMaterial, procedural geometry only, script in script.json.
export const MOKA_FRAMES=script.durationFrames;
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const h=(i:number,s:number)=>{const v=Math.sin(i*127.1+s*311.7)*43758.5453;return v-Math.floor(v);}; // deterministic hash in [0,1)
const hv=(x:number,y:number,z:number,s:number)=>h(x*12.9898+y*78.233+z*37.719,s);
const DS=THREE.DoubleSide;

// Moka profile (world units): lower chamber widens down, upper chamber widens up, joined at the narrow waist.
const BOT=.35,WAIST=1.55,TOPY=2.85,RB=.85,RW=.6,RT=.8,WATER_Y=BOT+(WAIST-BOT)*.6;
const rLow=(y:number)=>RB+(RW-RB)*(y-BOT)/(WAIST-BOT),rUp=(y:number)=>RW+(RT-RW)*(y-WAIST)/(TOPY-WAIST);

function jitterIco(r:number,seed:number,detail:number,amt:number){
  const g=new THREE.IcosahedronGeometry(r,detail),p=g.attributes.position;
  for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i),k=1+amt*(hv(x,y,z,seed)-.5)*2;p.setXYZ(i,x*k,y*k,z*k);}
  g.computeVertexNormals();return g;
}
function gradient(g:THREE.BufferGeometry,y0:number,y1:number,lo:string,hi:string){
  const p=g.attributes.position,c=new Float32Array(p.count*3),a=new THREE.Color(lo),b=new THREE.Color(hi),t=new THREE.Color();
  for(let i=0;i<p.count;i++){t.lerpColors(a,b,clip((p.getY(i)-y0)/(y1-y0)));c.set([t.r,t.g,t.b],i*3);}
  g.setAttribute('color',new THREE.BufferAttribute(c,3));return g;
}

// Back half (z<=0) of a frustum: the cut plane faces the camera, so the interior is visible.
function Half({rTop,rBot,y0,y1,color,segs=12}:{rTop:number,rBot:number,y0:number,y1:number,color:string,segs?:number}){
  return <mesh position-y={(y0+y1)/2} castShadow receiveShadow>
    <cylinderGeometry args={[rTop,rBot,y1-y0,segs,1,true,Math.PI/2,Math.PI]}/><meshStandardMaterial color={color} flatShading side={DS}/></mesh>;
}
// Thin box along the cut edge of a wall, so the section reads as sheet metal.
function Strip({r1,y1,r2,y2,side}:{r1:number,y1:number,r2:number,y2:number,side:1|-1}){
  const dx=r2-r1,dy=y2-y1,len=Math.hypot(dx,dy);
  return <mesh position={[side*(r1+r2)/2,(y1+y2)/2,0]} rotation-z={-side*Math.atan2(dx,dy)} castShadow>
    <boxGeometry args={[.06,len,.06]}/><meshStandardMaterial color="#8E969E" flatShading/></mesh>;
}

function Grounds(){
  const ref=useRef<THREE.InstancedMesh>(null);
  useLayoutEffect(()=>{
    const m=ref.current!,o=new THREE.Object3D(),c=new THREE.Color();
    for(let i=0;i<200;i++){
      const y=1.64+h(i,1)*1.02,rmax=rUp(y)*.93-.05,rho=Math.sqrt(h(i,2))*rmax,a=h(i,3)*Math.PI,s=.07+h(i,4)*.05;
      o.position.set(rho*Math.cos(a),y,-rho*Math.sin(a));
      o.rotation.set(h(i,5)*6,h(i,6)*6,h(i,7)*6);o.scale.set(s,s*(.7+.5*h(i,8)),s*(.8+.4*h(i,9)));o.updateMatrix();
      m.setMatrixAt(i,o.matrix);m.setColorAt(i,c.set(i%2?'#3B2416':'#6B4428'));
    }
    m.instanceMatrix.needsUpdate=true;if(m.instanceColor)m.instanceColor.needsUpdate=true;
  },[]);
  return <instancedMesh ref={ref} args={[undefined,undefined,200]} castShadow receiveShadow>
    <icosahedronGeometry args={[1,0]}/><meshStandardMaterial color="#ffffff" flatShading/></instancedMesh>;
}

function Water(){
  const rw=rLow(WATER_Y);
  const body=useMemo(()=>{const g=new THREE.CylinderGeometry(rw,RB,WATER_Y-BOT,12,1,true,Math.PI/2,Math.PI);g.translate(0,(BOT+WATER_Y)/2,0);return gradient(g,BOT,WATER_Y,'#3E7FBF','#A9D6F5');},[rw]);
  const face=useMemo(()=>{const s=new THREE.Shape();s.moveTo(-RB,BOT);s.lineTo(RB,BOT);s.lineTo(rw,WATER_Y);s.lineTo(-rw,WATER_Y);s.closePath();return gradient(new THREE.ShapeGeometry(s),BOT,WATER_Y,'#3E7FBF','#A9D6F5');},[rw]);
  const mat={vertexColors:true,transparent:true,opacity:.75,side:DS,depthWrite:false,flatShading:true};
  return <>
    <mesh geometry={body}><meshStandardMaterial {...mat}/></mesh>
    <mesh geometry={face} position-z={.002}><meshStandardMaterial {...mat}/></mesh>
    <mesh position-y={WATER_Y} rotation-x={-Math.PI/2}><circleGeometry args={[rw,12,0,Math.PI]}/><meshStandardMaterial color="#A9D6F5" transparent opacity={.75} side={DS} depthWrite={false} flatShading/></mesh>
  </>;
}

function Moka({f}:{f:number}){
  const st=script.steam,fade=clip((f-st.fadeFrom)/(st.fadeTo-st.fadeFrom));
  const puffGeo=useMemo(()=>jitterIco(.3,41,1,.3),[]);
  return <group>
    <Half rTop={RW} rBot={RB} y0={BOT} y1={WAIST} color="#D8DCE0"/>
    <Half rTop={RT} rBot={RW} y0={WAIST} y1={TOPY} color="#D8DCE0"/>
    <Strip r1={RB} y1={BOT} r2={RW} y2={WAIST} side={1}/><Strip r1={RB} y1={BOT} r2={RW} y2={WAIST} side={-1}/>
    <Strip r1={RW} y1={WAIST} r2={RT} y2={TOPY} side={1}/><Strip r1={RW} y1={WAIST} r2={RT} y2={TOPY} side={-1}/>
    <mesh position-y={BOT} castShadow><boxGeometry args={[RB*2,.06,.06]}/><meshStandardMaterial color="#8E969E" flatShading/></mesh>
    <mesh position-y={BOT} rotation-x={-Math.PI/2}><circleGeometry args={[RB,12,0,Math.PI]}/><meshStandardMaterial color="#C5CBD1" flatShading side={DS}/></mesh>
    <Half rTop={rUp(2.75)*.93} rBot={rUp(1.58)*.93} y0={1.58} y1={2.75} color="#2A1810"/>
    <Grounds/>
    <Half rTop={.56} rBot={.12} y0={1.1} y1={WAIST} color="#5A6168" segs={10}/>
    <mesh position-y={1.375}><cylinderGeometry args={[.05,.05,1.65,6,1,true,Math.PI/2,Math.PI]}/><meshStandardMaterial color="#5A6168" flatShading side={DS}/></mesh>
    <Water/>
    {Array.from({length:8}).map((_,k)=><group key={k} position={[0,TOPY+.05,0]} rotation-z={(-75+k*150/7)*Math.PI/180}>
      <mesh position-y={.32+.03*Math.sin(f*.2+k)*fade}><boxGeometry args={[.03,.3,.03]}/><meshStandardMaterial color="#9AA3AD" flatShading transparent opacity={fade}/></mesh></group>)}
    {st.puffBirths.map((b,i)=>{
      const p=(f-b)/st.puffLife;if(p<0||p>1)return null;
      const sc=interpolate(p,[0,1],[.3,1.4]),o=.5*clip(p/.08)*(1-clip((p-.35)/.65));
      return <mesh key={i} geometry={puffGeo} position={[noise2D('px'+i,p*1.5,i)*.4,TOPY+.1+p*1.3,-.05+noise2D('pz'+i,p*1.5,i)*.15]} scale={sc} rotation-y={i+p}>
        <meshStandardMaterial color="#E8E8E8" flatShading transparent opacity={o} depthWrite={false}/></mesh>;})}
  </group>;
}

// Low-poly flame ring: nine flattened cones with a base-to-tip vertex gradient, flickering with sine + seeded noise.
const flameGeo=(()=>{const g=new THREE.ConeGeometry(.07,.34,3,1);g.translate(0,.17,0);
  const p=g.attributes.position,c=new Float32Array(p.count*3),lo=new THREE.Color('#2F8FE0'),hi=new THREE.Color('#8FD0F7');
  for(let i=0;i<p.count;i++){const t=p.getY(i)>.2?hi:lo;c.set([t.r,t.g,t.b],i*3);}g.setAttribute('color',new THREE.BufferAttribute(c,3));return g;})();
const NF=9;
function Stove({f}:{f:number}){
  return <group>
    <mesh position-y={.3} rotation-x={Math.PI/2} castShadow><torusGeometry args={[.75,.055,6,14]}/><meshStandardMaterial color="#1A1C20" flatShading/></mesh>
    {[0,1,2,3].map(k=><mesh key={k} position={[.75*Math.cos(Math.PI/4+k*Math.PI/2),.15,.75*Math.sin(Math.PI/4+k*Math.PI/2)]} castShadow>
      <cylinderGeometry args={[.03,.03,.3,5]}/><meshStandardMaterial color="#1A1C20" flatShading/></mesh>)}
    <group position-y={.1}>{Array.from({length:NF}).map((_,i)=>{
      const raw=.5*Math.sin(2*Math.PI*f/(9+(i%4)*2)+i*1.7)+.5*noise2D('fl'+i,f*.12,i),sy=1.05+.25*Math.max(-1,Math.min(1,raw));
      const ry=8*Math.PI/180*Math.sin(2*Math.PI*f/(13+(i%3)*3)+i*2.3);
      return <group key={i} rotation-y={i*2*Math.PI/NF}><group position-x={.4} rotation-z={-.55}>
        <mesh geometry={flameGeo} scale={[1,sy,.3]} rotation-y={ry}><meshStandardMaterial vertexColors flatShading emissive="#2F8FE0" emissiveIntensity={.5}/></mesh></group></group>;})}</group>
  </group>;
}

function Bubbles({f}:{f:number}){
  return <>{script.bubbleBirths.map((b,i)=>{
    const p=(f-b)/script.bubbleLife;if(p<0||p>1.2)return null;
    const rise=Math.min(p,1),pop=clip((p-1)/.2),r=(.035+.015*h(i,3))*(1+.3*rise);
    return <mesh key={i} scale={1+.6*pop} position={[(h(i,1)-.5)*.8+noise2D('bx'+i,p*2,i)*.03,.5+rise*(WATER_Y-.05-.5),-(.08+h(i,2)*.3)]}>
      <icosahedronGeometry args={[r,1]}/><meshStandardMaterial color="#E6F6FF" flatShading transparent opacity={.9*(1-pop)} depthWrite={false}/></mesh>;})}</>;
}

function Lemon({pos,rot,period,seed,f}:{pos:[number,number,number],rot:[number,number,number],period:number,seed:number,f:number}){
  const geo=useMemo(()=>jitterIco(.26,seed,1,.1),[seed]);
  return <group position={pos} rotation={[rot[0],rot[1]+2*Math.PI*f/period,rot[2]]}>
    <mesh geometry={geo} scale={[1.18,.84,.94]} castShadow receiveShadow><meshStandardMaterial color="#E8D23C" flatShading/></mesh>
    <mesh position={[.3,0,0]} rotation-z={-Math.PI/2} castShadow><coneGeometry args={[.055,.12,5]}/><meshStandardMaterial color="#E8D23C" flatShading/></mesh>
  </group>;
}
function Bowl({f}:{f:number}){
  const [p1,p2,p3]=script.lemonPeriods;
  return <group>
    <group position={[-2.4,0,.7]}>
      <mesh position-y={.2} castShadow receiveShadow><cylinderGeometry args={[.78,.52,.4,10]}/><meshStandardMaterial color="#F5EFE0" flatShading/></mesh>
      <mesh position-y={.395} rotation-x={-Math.PI/2}><circleGeometry args={[.7,10]}/><meshStandardMaterial color="#E0D8C3" flatShading/></mesh>
    </group>
    <Lemon pos={[-2.62,.55,.7]} rot={[.3,.4,.2]} period={p1} seed={1} f={f}/>
    <Lemon pos={[-2.2,.52,.82]} rot={[-.2,2.1,.5]} period={p2} seed={2} f={f}/>
    <Lemon pos={[-2.42,.88,.72]} rot={[.5,4.2,-.3]} period={p3} seed={3} f={f}/>
  </group>;
}

function Wall(){
  const TW=.62,TH=.8;
  const cols=useMemo(()=>Array.from({length:27},(_,k)=>(k-13)*TW),[]),rows=useMemo(()=>Array.from({length:17},(_,j)=>j*TH),[]);
  return <group>
    <mesh position={[0,5.6,-3]} receiveShadow><planeGeometry args={[17,13]}/><meshStandardMaterial color="#2F6FED" flatShading/></mesh>
    {cols.map((x,k)=><mesh key={'c'+k} position={[x,6.4,-2.97]} castShadow receiveShadow><boxGeometry args={[.04,12.8,.05]}/><meshStandardMaterial color="#FFFFFF" flatShading/></mesh>)}
    {rows.map((y,j)=><mesh key={'r'+j} position={[0,y,-2.97]} castShadow receiveShadow><boxGeometry args={[17,.04,.05]}/><meshStandardMaterial color="#FFFFFF" flatShading/></mesh>)}
  </group>;
}
function Counter(){
  const geo=useMemo(()=>{const g=new THREE.PlaneGeometry(16,8,64,32),p=g.attributes.position,c=new Float32Array(p.count*3),base=new THREE.Color('#2D3038');
    for(let i=0;i<p.count;i++){const k=.88+.24*h(i,11);c.set([base.r*k,base.g*k,base.b*k],i*3);p.setZ(i,(h(i,12)-.5)*.016);}
    g.setAttribute('color',new THREE.BufferAttribute(c,3));g.computeVertexNormals();return g;},[]);
  return <mesh geometry={geo} rotation-x={-Math.PI/2} position={[0,0,.5]} receiveShadow><meshStandardMaterial vertexColors flatShading roughness={1}/></mesh>;
}

function Rig({f}:{f:number}){
  const {camera}=useThree(),k=script.cam;
  const at=(key:'dist'|'tx'|'ty')=>interpolate(f,k.map(c=>c.f),k.map(c=>c[key]),{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const az=script.orbit.degrees*Math.PI/180*Math.sin(2*Math.PI*f/script.orbit.period),el=12*Math.PI/180,D=at('dist'),tx=at('tx'),ty=at('ty');
  camera.position.set(tx+D*Math.sin(az)*Math.cos(el),ty+D*Math.sin(el),D*Math.cos(az)*Math.cos(el));
  camera.lookAt(tx,ty,0);camera.updateMatrixWorld();
  return null;
}

function Caption({f}:{f:number}){
  const c=script.caption;if(f<c.from||f>=c.to)return null;
  const sp=spring({frame:f-c.from,fps:FPS,config:{damping:13,stiffness:170,mass:.7}}),out=ez(EZ.inout,f,c.to-8,8);
  return <svg width={W} height={H} style={{position:'absolute',inset:0}}>
    <text x={540} y={c.y} textAnchor="middle" fontFamily={FONT} fontWeight={900} fontSize={c.size} fill="#FFFFFF" stroke="#000000" strokeWidth={8} strokeLinejoin="round" paintOrder="stroke fill"
      opacity={clip(sp*2)*(1-out)} transform={`translate(540 ${c.y}) scale(${.8+.2*sp}) translate(-540 ${-c.y})`}>{c.text}</text></svg>;
}

export function MokaCutaway(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:'#2F6FED'}}>
    <ThreeCanvas width={W} height={H} shadows flat camera={{fov:35,position:[0,3,14],near:.1,far:80}}>
      <color attach="background" args={['#2F6FED']}/>
      <Rig f={f}/>
      <ambientLight intensity={.5*Math.PI}/> {/* three >= r155 no longer scales by pi: x pi keeps the classic 0.5 / 0.8 look */}
      <directionalLight position={[5,9,6]} intensity={.8*Math.PI} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048}
        shadow-camera-left={-9} shadow-camera-right={9} shadow-camera-top={9} shadow-camera-bottom={-9} shadow-camera-near={.5} shadow-camera-far={40} shadow-bias={-.0004}/>
      <Wall/><Counter/><Bowl f={f}/><Stove f={f}/><Moka f={f}/><Bubbles f={f}/>
    </ThreeCanvas>
    <Caption f={f}/>
  </AbsoluteFill>;
}
