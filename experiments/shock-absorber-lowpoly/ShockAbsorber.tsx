import React from 'react';
import {AbsoluteFill,Sequence,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import script from './script.json';
import {EZ,FPS,H,W,clip,ez} from '../remotion-explainer/coffee-sci/kit';

// Silent low-poly explainer built from the consolidated docs/motion-graphics-recipe-lowpoly.md. Per shot: one camera move over the
// WHOLE shot (decoupled from the caption rhythm), a required ambient work cycle (a bump every `period` frames, the piston and
// the suspension ring down and settle), environmental elements, and captions that are independent phrases replacing each other.
// validate() throws at load. Every animated value is a pure function of useCurrentFrame() (never useFrame).
export const SHOCK_FRAMES=script.durationFrames;
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const K={bg:'#8FD9D2',road:'#4A5560',mark:'#F2F5F8',tire:'#2D3640',steel:'#C9D3DC',steelMid:'#9AA7B3',steelDark:'#6B7886',rod:'#E3EAF0',body:'#E3E8EE',cabin:'#D5DCE5',
  glass:'#3A4452',oil:'#F28C38',slot:'#2B323B',flow:'#EDEFF2',red:'#E5333B',term:'#FFD23F',white:'#FFFFFF',hl:'#BEE3FF'};
type V3=[number,number,number];
const AMBIENT=['damper-cycle','valve-cycle'];
const TARGETS=['spring','damper','piston','rod','valve','oil','cylinder','wheel','body','suspension'];
const PARTS=['PISTÓN','VÁLVULA','VÁLVULAS','AMORTIGUADOR','RESORTE','ACEITE','CILINDRO','VARILLA','SUSPENSIÓN','CARROCERÍA','RUEDA','LLANTAS','LLANTA'];

(function validate(){
  for(const s of script.shots){
    if(!s.ambient||!AMBIENT.includes(s.ambient.kind)||!s.ambient.moving||!(s.ambient.period>=30))throw new Error(`shot ${s.id}: ambient work cycle is required (kind, period, moving)`);
    if(!s.camera.from||!s.camera.to||JSON.stringify(s.camera.from)===JSON.stringify(s.camera.to))throw new Error(`shot ${s.id}: the camera must move`);
    if((s.type==='establishing'||s.type==='cutaway')&&s.environment.length<2)throw new Error(`shot ${s.id}: needs at least two environmental elements`);
  }
  const phrases=script.captions.filter(c=>c.style==='phrase');
  phrases.forEach((c,i)=>{
    if(c.text.split(' ').length>5)throw new Error(`caption ${c.id}: a phrase is at most five words`);
    if(i&&c.text.toLowerCase().startsWith(phrases[i-1].text.toLowerCase()))throw new Error(`caption ${c.id} accumulates on the previous phrase`);
  });
  script.events.filter(e=>e.kind==='highlight').forEach(e=>{if(!TARGETS.includes(e.target))throw new Error(`event ${e.id}: highlight needs a valid target`);});
  script.captions.filter(c=>c.style==='term').forEach(c=>{if(!PARTS.includes(c.text))throw new Error(`term ${c.id}: "${c.text}" is not a real part name`);});
})();

// ---- primitives -----------------------------------------------------------------------------------------------
const Y=new THREE.Vector3(0,1,0);
function Beam({a,b,r,color}:{a:V3,b:V3,r:number,color:string}){
  const A=new THREE.Vector3(...a),d=new THREE.Vector3(...b).sub(A),len=d.length(),dir=d.normalize();
  return <mesh position={A.clone().addScaledVector(dir,len/2).toArray()} quaternion={new THREE.Quaternion().setFromUnitVectors(Y,dir)}>
    <cylinderGeometry args={[r,r,Math.max(len,.0001),8]}/><meshStandardMaterial color={color} emissive={color} emissiveIntensity={.5} flatShading/></mesh>;
}
// Thin red arrow: force/direction only.
function Arrow({from,dir,len,s}:{from:V3,dir:V3,len:number,s:number}){
  if(s<=.02)return null;
  const d=new THREE.Vector3(...dir).normalize(),A=new THREE.Vector3(...from),L=len*s,tip=A.clone().addScaledVector(d,L),q=new THREE.Quaternion().setFromUnitVectors(Y,d);
  return <group>
    <Beam a={from} b={A.clone().addScaledVector(d,Math.max(L-.1,.001)).toArray() as V3} r={.025} color={K.red}/>
    <mesh position={tip.clone().addScaledVector(d,-.07).toArray()} quaternion={q}><coneGeometry args={[.07,.14,6]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.5} flatShading/></mesh>
  </group>;
}
function Rig({s,gf}:{s:typeof script.shots[number],gf:number}){
  const {camera}=useThree(),e=ez(EZ.inout,gf,s.start,s.end-s.start-1);  // one move over the whole shot
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
// Back half (z<0) of a cylinder along y. Closed ones get a flat cut face at z=0 so they read as solid sections.
function HalfSolid({r,h,y,color,z=0,opacity=1}:{r:number,h:number,y:number,color:string,z?:number,opacity?:number}){
  return <group position-y={y}>
    <mesh castShadow><cylinderGeometry args={[r,r,h,14,1,false,Math.PI/2,Math.PI]}/><meshStandardMaterial color={color} flatShading side={THREE.DoubleSide} transparent={opacity<1} opacity={opacity} depthWrite={opacity>=1}/></mesh>
    <mesh position={[0,0,z]}><boxGeometry args={[2*r,h,.01]}/><meshStandardMaterial color={color} flatShading transparent={opacity<1} opacity={opacity} depthWrite={opacity>=1}/></mesh>
  </group>;
}

// ---- the work cycle: a bump kicks the wheel every `period` frames; the response rings down. Ringing before a `damp` event
// (spring alone), settling quickly after it (spring + damper). Pure function of the global frame.
type Cyc={s:number,v:number,t:number,pulse:number};
function cyc(gf:number,P:number,dampAt:number|null):Cyc{
  const f=(g:number)=>{const t=((g%P)+P)%P,decay=dampAt!==null&&g<dampAt?.018:.11;return Math.max(-1,Math.min(1,1.35*Math.exp(-decay*t)*Math.sin(.55*t)));};
  const t=((gf%P)+P)%P;
  return {s:f(gf),v:(f(gf+1)-f(gf-1))/2,t,pulse:t<10?Math.sin(Math.PI*t/10):0};
}
const evAt=(sid:string,kind:string)=>script.events.find(e=>e.shot===sid&&e.kind===kind)?.at??null;
// The suspension rings (spring alone) until the first `damp` event anywhere in the video, then settles quickly in every shot.
const DAMP=script.events.find(e=>e.kind==='damp')?.at??null;

// ---- events: every event of a shot is drawn in its own timed window (arrow 1.5 s, highlight 1.3 s, flow 3 s) --------------------
type Ev={kind:string,at:number,target:string};
const shotEvents=(sid:string):Ev[]=>script.events.filter(e=>e.shot===sid);
const win=(gf:number,at:number,dur:number)=>{const t=gf-at;return t<0||t>dur?0:Math.min(1,t/6)*Math.min(1,(dur-t)/12);};
const act=(evs:Ev[],gf:number,kind:string,dur:number)=>Math.max(0,...evs.filter(e=>e.kind===kind).map(e=>win(gf,e.at,dur)));
type Glow={pos:V3,size:V3,rot?:number};
// A brief neutral pulse on a named part: pale blue, so it never reads as force (red), term (yellow) or flow (grey/white).
function Glows({evs,gf,map}:{evs:Ev[],gf:number,map:Record<string,Glow>}){
  return <>{evs.filter(e=>e.kind==='highlight'&&map[e.target]).map((e,i)=>{
    const a=win(gf,e.at,40),g=map[e.target];
    return a>0?<mesh key={i} position={g.pos} rotation-z={g.rot??0} renderOrder={5}><boxGeometry args={g.size}/>
      <meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.8} flatShading transparent opacity={.55*a*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>:null;})}</>;
}

// ---- establishing: wheel, suspension arm, chassis, road and the coil spring + damper strut -------------------------
function Establishing({gf,s}:{gf:number,s:typeof script.shots[number]}){
  const P=s.ambient.period,c=cyc(gf,P,DAMP),evs=shotEvents(s.id),aA=act(evs,gf,'force_arrows',45),lift=.14*c.pulse,b=.2*c.s,wy=.5+lift;
  const u=((c.t+P/2)%P)-P/2,bx=-.1*u*(60/P);  // the bump reaches the wheel at the start of each cycle
  const piv:V3=[-1.35,1.25+b,0],arm=new THREE.Vector3(piv[0],piv[1]-wy,0),k=.3/1.35,lowY=wy+(piv[1]-wy)*k,upY=1.52+b,sx=-.3;
  const strut:Glow={pos:[sx,(lowY+upY)/2,0],size:[.5,upY-lowY+.1,.5]};
  const map:Record<string,Glow>={spring:strut,damper:strut,piston:strut,rod:strut,valve:strut,oil:strut,cylinder:strut,
    wheel:{pos:[0,wy,0],size:[1.25,1.25,.6]},body:{pos:[-.4,1.9+b,0],size:[3.5,1.1,1.7]},suspension:{pos:[piv[0]/2,(piv[1]+wy)/2,0],size:[arm.length()+.25,.32,.4],rot:Math.atan2(arm.y,arm.x)}};
  return <>
    <Box size={[16,.2,3]} pos={[0,-.1,0]} color={K.road}/>
    {Array.from({length:14}).map((_,i)=><Box key={i} size={[.6,.02,.12]} pos={[((i*1.5-gf*.06)%21+21)%21-10.5,.012,.95]} color={K.mark}/>)}
    <mesh position={[bx,0,0]} rotation-x={Math.PI/2} scale={[1,1,.45]} castShadow><cylinderGeometry args={[.35,.35,3,10]}/><meshStandardMaterial color={K.steelDark} flatShading/></mesh>
    <group position={[0,wy,0]}>
      <mesh rotation-x={Math.PI/2} castShadow><cylinderGeometry args={[.5,.5,.36,14]}/><meshStandardMaterial color={K.tire} flatShading/></mesh>
      <group rotation-z={-gf*.12}>
        <mesh rotation-x={Math.PI/2} position-z={.19}><cylinderGeometry args={[.3,.3,.04,10]}/><meshStandardMaterial color={K.steel} flatShading/></mesh>
        {[0,1,2,3,4].map(i=><group key={i} rotation-z={i*Math.PI*2/5}><Box size={[.07,.24,.04]} pos={[0,.15,.21]} color={K.steelDark}/></group>)}
      </group>
    </group>
    <mesh position={[(piv[0])/2,(piv[1]+wy)/2,0]} rotation-z={Math.atan2(arm.y,arm.x)} castShadow><boxGeometry args={[arm.length(),.11,.16]}/><meshStandardMaterial color={K.steelMid} flatShading/></mesh>
    <Box size={[3.2,.45,1.5]} pos={[-.4,1.75+b,0]} color={K.body}/><Box size={[1.5,.4,1.3]} pos={[-.9,2.17+b,0]} color={K.cabin}/><Box size={[1.3,.22,1.32]} pos={[-.9,2.2+b,0]} color={K.glass}/>
    {Array.from({length:8}).map((_,i)=><mesh key={i} position={[sx,lowY+.1+(upY-lowY-.2)*(i+.5)/8,0]} rotation-x={Math.PI/2}><torusGeometry args={[.17,.035,6,10]}/><meshStandardMaterial color={K.steel} flatShading/></mesh>)}
    <mesh position={[sx,lowY+.22,0]}><cylinderGeometry args={[.075,.075,.44,8]}/><meshStandardMaterial color={K.steelDark} flatShading/></mesh>
    <mesh position={[sx,(lowY+.44+upY)/2,0]}><cylinderGeometry args={[.04,.04,Math.max(upY-lowY-.44,.01),8]}/><meshStandardMaterial color={K.rod} flatShading/></mesh>
    {aA>0&&<Arrow from={[.8,.05,.25]} dir={[0,1,0]} len={.75} s={aA}/>}
    <Glows evs={evs} gf={gf} map={map}/>
  </>;
}

// ---- cutaway / insert: the damper in section. Piston strokes through the oil; ports let oil through (flow chevrons) ------------
const PORTS=[-.36,-.18,.18,.36];
function Damper({gf,s,env}:{gf:number,s:typeof script.shots[number],env:boolean}){
  const P=s.ambient.period,c=cyc(gf,P,DAMP),evs=shotEvents(s.id),aF=act(evs,gf,'flow_chevrons',90),aA=act(evs,gf,'force_arrows',45);
  const yP=1.2+.45*c.s,yTop=yP+1.9,dir=-Math.sign(c.v)||1,mag=clip(Math.abs(c.v)*14);
  const tube:Glow={pos:[0,1.3,0],size:[1.3,2.4,.8]};
  const map:Record<string,Glow>={piston:{pos:[0,yP,0],size:[1.15,.4,.5]},valve:{pos:[0,yP,0],size:[.95,.45,.5]},rod:{pos:[0,(yP+yTop)/2,0],size:[.3,yTop-yP,.35]},
    oil:{pos:[0,1.3,0],size:[1.15,2.2,.6]},cylinder:tube,damper:tube,...(env?{spring:{pos:[0,(.3+yTop)/2,-.1],size:[1.95,yTop-.3,1.0]},body:{pos:[0,yTop+.3,-.1],size:[2.9,.55,1.6]},
      wheel:{pos:[0,-.05,-.1],size:[2.3,.5,1.2]},suspension:{pos:[0,-.05,-.1],size:[2.3,.5,1.2]}}:{})};
  return <>
    <HalfSolid r={.5} h={2.1} y={1.3} color={K.oil} z={-.02} opacity={.85}/>
    <mesh position-y={1.3} castShadow><cylinderGeometry args={[.56,.56,2.2,14,1,true,Math.PI/2,Math.PI]}/><meshStandardMaterial color={K.steelMid} flatShading side={THREE.DoubleSide}/></mesh>
    {[-.56,.56].map(x=><Box key={x} size={[.07,2.2,.06]} pos={[x,1.3,0]} color={K.steelDark}/>)}
    <Box size={[1.2,.12,.06]} pos={[0,.2,0]} color={K.steelDark}/>
    <HalfSolid r={.58} h={.2} y={2.5} color={K.steelDark}/>
    <HalfSolid r={.5} h={.22} y={yP} color={K.steel}/>
    {PORTS.map(x=><Box key={x} size={[.07,.26,.02]} pos={[x,yP,.012]} color={K.slot}/>)}
    <HalfSolid r={.4} h={.025} y={yP+.125} color={K.steelMid} z={.01}/>
    <HalfSolid r={.09} h={yTop-yP} y={(yP+yTop)/2} color={K.rod} z={.01}/>
    {env&&<>
      <Box size={[2.6,.32,1.4]} pos={[0,yTop+.3,-.1]} color={K.body}/><Box size={[.4,.14,.4]} pos={[0,yTop+.08,0]} color={K.steelDark}/>
      <Box size={[2.0,.3,1.0]} pos={[0,-.05,-.1]} color={K.steelMid}/>{[-.7,.7].map(x=><mesh key={x} position={[x,.14,.2]}><cylinderGeometry args={[.07,.07,.12,6]}/><meshStandardMaterial color={K.steelDark} flatShading/></mesh>)}
      {Array.from({length:9}).map((_,i)=><mesh key={i} position-y={.35+(yTop-.4)*(i+.5)/9} rotation-x={-Math.PI/2}><torusGeometry args={[.85,.045,6,12,Math.PI]}/><meshStandardMaterial color={K.steel} flatShading/></mesh>)}
    </>}
    {aF>0&&PORTS.map((x,pi)=>[0,1,2].map(kk=>{
      const ph=(gf*.025+kk/3+pi*.13)%1;
      return <mesh key={pi+'-'+kk} position={[x,yP+dir*(-.3+ph*.6),.1]} rotation-z={dir>0?0:Math.PI} scale={mag*aF*Math.sin(Math.PI*ph)+.001}><coneGeometry args={[.06,.16,4]}/><meshStandardMaterial color={K.flow} flatShading/></mesh>;}))}
    {aA>0&&(c.v<0?<Arrow from={[.8,yTop+1.0,.3]} dir={[0,-1,0]} len={.8} s={aA}/>:<Arrow from={[.8,yTop+.3,.3]} dir={[0,1,0]} len={.8} s={aA}/>)}
    <Glows evs={evs} gf={gf} map={map}/>
  </>;
}
function Scene({i,gf}:{i:number,gf:number}){
  const s=script.shots[i];
  return s.type==='establishing'?<Establishing gf={gf} s={s}/>:<Damper gf={gf} s={s} env={s.type==='cutaway'}/>;
}
function Shot({i}:{i:number}){
  const s=script.shots[i],local=useCurrentFrame(),gf=s.start+local;
  return <ThreeCanvas width={W} height={H} shadows flat camera={{fov:s.camera.fov,position:s.camera.from.pos as V3,near:.1,far:80}}>
    <color attach="background" args={[K.bg]}/><Rig s={s} gf={gf}/><Lights/><Scene i={i} gf={gf}/>
  </ThreeCanvas>;
}

// ---- captions: one independent phrase at a time, white bold with a heavy black stroke, no box ----------------------------
const STROKE=Array.from({length:16},(_,k)=>{const a=k*Math.PI/8;return `${(4*Math.cos(a)).toFixed(1)}px ${(4*Math.sin(a)).toFixed(1)}px 0 #000`;}).join(',');
function Caption({c,f}:{c:typeof script.captions[number],f:number}){
  if(f<c.at||f>=c.until)return null;
  const term=c.style==='term',sp=spring({frame:f-c.at,fps:FPS,config:{damping:13,stiffness:170,mass:.7}}),out=ez(EZ.inout,f,c.until-5,5);
  return <div style={{position:'absolute',left:60,right:60,top:term?1640:1480,textAlign:'center',fontFamily:FONT,fontWeight:900,fontSize:term?76:64,lineHeight:1.12,
    color:term?K.term:K.white,textShadow:STROKE,opacity:clip(sp*2)*(1-out),transform:`scale(${.85+.15*sp}) translateY(${(1-sp)*18}px)`}}>{c.text}</div>;
}

export function ShockAbsorber(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:K.bg}}>
    {script.shots.map((s,i)=><Sequence key={s.id} from={s.start} durationInFrames={s.end-s.start} layout="none"><Shot i={i}/></Sequence>)}
    {script.captions.map(c=><Caption key={c.id} c={c} f={f}/>)}
  </AbsoluteFill>;
}
