import React from 'react';
import {AbsoluteFill,Sequence,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import script from './script.json';
import {EZ,FPS,H,W,clip,ez} from '../remotion-explainer/coffee-sci/kit';

// Silent low-poly explainer built from the updated docs/motion-graphics-recipe-lowpoly.md: a zipper whose slider travels up and down in a
// continuous cycle. Every held shot sustains itself one of two ways: a moving camera (the jacket and wall stripes slide past), or a locked
// camera while the zipper is BUILT part by part (each part flies in on an arc and settles). A detail callout can be a push-in/pull-out of the
// same camera. validate() throws at load. Every animated value is a pure function of useCurrentFrame() (never useFrame).
export const ZIPPER_FRAMES=script.durationFrames;
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const K={bg:'#F5A9B8',stripe:'#EE9DAD',denim:'#8EA6C4',denimDark:'#6F87A6',stitch:'#DCE6F2',steel:'#C9D3DC',steelMid:'#9AA7B3',steelDark:'#6B7886',tape:'#D5DCE5',
  toothL:'#C9D3DC',toothR:'#E3EAF0',hanger:'#8896A4',red:'#E5333B',term:'#FFD23F',white:'#FFFFFF',hl:'#BEE3FF',slot:'#3A4452'};
type V3=[number,number,number];
const TARGETS=['tape','teeth','slider','tab','stop'];
const PUSH=['neck','slider','teeth','tab'];
const AMBIENT=['slider-cycle','assembly-cycle'];
const PARTS=['DIENTE','DIENTES','CINTA','CURSOR','CORREDERA','JALADOR','TIRADOR','LENGÜETA','TOPE','TOPES','CUÑA','DIVISOR'];
const SL_P=120,SL_AMP=1.5;

(function validate(){
  for(const s of script.shots){
    if(!s.ambient||!AMBIENT.includes(s.ambient.kind)||!s.ambient.moving||s.ambient.period!==SL_P)throw new Error(`shot ${s.id}: ambient work cycle is required (kind, period ${SL_P}, moving)`);
    if(s.sustain!=='camera'&&s.sustain!=='assembly')throw new Error(`shot ${s.id}: sustain must be camera or assembly`);
    const still=JSON.stringify(s.camera.from)===JSON.stringify(s.camera.to);
    const att=script.events.filter(e=>e.shot===s.id&&e.kind==='attach');
    if(s.sustain==='camera'&&still)throw new Error(`shot ${s.id}: a camera-driven shot must move the camera`);
    if(s.sustain==='assembly'){
      const ts=att.map(e=>e.at).sort((a,b)=>a-b),targets=new Set(att.map(e=>e.target));
      if(targets.size<3)throw new Error(`shot ${s.id}: an assembly shot needs at least three distinct attach events`);
      if(ts.some((t,i)=>i&&t-ts[i-1]>180)||ts[0]-s.start>180)throw new Error(`shot ${s.id}: assembly stalls for more than 6 s`);
    }
    if((s.type==='establishing'||s.type==='cutaway')&&s.environment.length<2)throw new Error(`shot ${s.id}: needs at least two environmental elements`);
  }
  const phrases=script.captions.filter(c=>c.style==='phrase');
  phrases.forEach((c,i)=>{
    if(c.text.split(' ').length>5)throw new Error(`caption ${c.id}: a phrase is at most five words`);
    if(i&&c.text.toLowerCase().startsWith(phrases[i-1].text.toLowerCase()))throw new Error(`caption ${c.id} accumulates on the previous phrase`);
  });
  script.events.forEach(e=>{
    if((e.kind==='highlight'||e.kind==='attach')&&!TARGETS.includes(e.target))throw new Error(`event ${e.id}: ${e.kind} needs a valid target`);
    if(e.kind==='pushin'&&!PUSH.includes(e.target))throw new Error(`event ${e.id}: pushin needs a valid target`);
  });
  if(!script.events.some(e=>e.kind==='pushin'))throw new Error('the plan needs at least one push-in/pull-out detail callout');
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
const Lights=()=><>
  <ambientLight intensity={.45*Math.PI}/>
  <directionalLight position={[5,8,6]} intensity={.8*Math.PI} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048}
    shadow-camera-left={-9} shadow-camera-right={9} shadow-camera-top={9} shadow-camera-bottom={-9} shadow-camera-near={.5} shadow-camera-far={40} shadow-bias={-.0004}/>
</>;
const Box=({size,pos,color,rot=0}:{size:V3,pos:V3,color:string,rot?:number})=><mesh position={pos} rotation-z={rot} castShadow receiveShadow><boxGeometry args={size}/><meshStandardMaterial color={color} flatShading/></mesh>;
const smooth=(t:number)=>t*t*(3-2*t);

// ---- the work cycle: the slider travels up and back down every SL_P frames (up = zipping, down = unzipping) -----------------------
const sliderY=(gf:number)=>SL_AMP*Math.sin(2*Math.PI*gf/SL_P);
const sliderV=(gf:number)=>sliderY(gf+1)-sliderY(gf-1);
// Teeth above the slider are pried apart (the tapes diverge); teeth below it are interlocked. Centre x of a tooth at height y.
function toothX(y:number,yS:number,side:number){
  const d=y-yS,open=smooth(clip(d/.25)),gap=.2+.55*Math.min(1,Math.max(0,d)/1.4);
  return side*(.17+open*gap/2);
}

// ---- events: every event of a shot is drawn in its own timed window ---------------------------------------------------------
type Ev={kind:string,at:number,target:string};
const shotEvents=(sid:string):Ev[]=>script.events.filter(e=>e.shot===sid);
const win=(gf:number,at:number,dur:number)=>{const t=gf-at;return t<0||t>dur?0:Math.min(1,t/6)*Math.min(1,(dur-t)/12);};
const act=(evs:Ev[],gf:number,kind:string,dur:number)=>Math.max(0,...evs.filter(e=>e.kind===kind).map(e=>win(gf,e.at,dur)));
const pushW=(gf:number,at:number)=>smooth(clip(Math.min((gf-at)/40,(at+150-gf)/40)));  // ~5 s: in, hold, out
type Glow={pos:V3,size:V3};
// A brief neutral pulse on a named part: pale blue, so it never reads as force (red), term (yellow) or flow (grey/white).
function Glows({evs,gf,map}:{evs:Ev[],gf:number,map:Record<string,Glow[]>}){
  return <>{evs.filter(e=>e.kind==='highlight'&&map[e.target]).flatMap((e,i)=>{
    const a=win(gf,e.at,40);
    return a>0?map[e.target].map((g,j)=><mesh key={i+'-'+j} position={g.pos} renderOrder={5}><boxGeometry args={g.size}/>
      <meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.8} flatShading transparent opacity={.55*a*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>):[];})}</>;
}
function Rig({s,gf}:{s:typeof script.shots[number],gf:number}){
  const {camera}=useThree(),e=ez(EZ.inout,gf,s.start,s.end-s.start-1);  // one move over the WHOLE shot, whatever the captions do
  const L=(a:number[],b:number[])=>a.map((v,i)=>v+(b[i]-v)*e);
  let p=L(s.camera.from.pos,s.camera.to.pos),t=L(s.camera.from.target,s.camera.to.target);
  const yS=sliderY(gf),dy=(yS*.8-t[1])*s.camera.follow;t=[t[0],t[1]+dy,t[2]];p=[p[0],p[1]+dy,p[2]];
  for(const ev of script.events.filter(x=>x.shot===s.id&&x.kind==='pushin')){  // push-in / pull-out of the same camera onto a detail
    const w=pushW(gf,ev.at);if(w<=0)continue;
    const tp:V3=ev.target==='tab'?[0,yS-.5,.15]:ev.target==='teeth'?[0,yS-1,0]:[0,yS,0],close=tp.map((v,i)=>v+(p[i]-v)*.3);
    p=p.map((v,i)=>v+(close[i]-v)*w);t=t.map((v,i)=>v+(tp[i]-v)*w);
  }
  camera.position.set(p[0],p[1],p[2]);(camera as THREE.PerspectiveCamera).fov=s.camera.fov;(camera as THREE.PerspectiveCamera).updateProjectionMatrix();
  camera.lookAt(t[0],t[1],t[2]);camera.updateMatrixWorld();
  return null;
}

// ---- a part that is introduced flies in on an arc, rotates and settles with a small bounce; it never pops in -------------------------
type Arr={vis:boolean,pos:V3,rot:number};
const arrive=(gf:number,at:number|null,from:V3,rot0:number):Arr=>{
  if(at===null)return {vis:true,pos:[0,0,0],rot:0};
  if(gf<at)return {vis:false,pos:[0,0,0],rot:0};
  const s=spring({frame:gf-at,fps:FPS,config:{damping:9,stiffness:110,mass:.8}}),a=clip(s),lift=Math.sin(Math.PI*a)*1.1;
  return {vis:true,pos:[from[0]*(1-s),from[1]*(1-s)+lift,from[2]*(1-s)],rot:rot0*(1-s)};
};

// ---- slider: Y-shaped, wide end up; the top plate is removed in the cutaway so the wedge and the teeth path show ---------------------
const plateGeo=(()=>{const sh=new THREE.Shape();sh.moveTo(-.75,.5);sh.lineTo(.75,.5);sh.lineTo(.28,-.5);sh.lineTo(-.28,-.5);sh.closePath();
  const g=new THREE.ExtrudeGeometry(sh,{depth:.05,bevelEnabled:false});g.translate(0,0,-.025);return g;})();
const wedgeGeo=(()=>{const sh=new THREE.Shape();sh.moveTo(0,.32);sh.lineTo(-.14,-.05);sh.lineTo(.14,-.05);sh.closePath();
  const g=new THREE.ExtrudeGeometry(sh,{depth:.16,bevelEnabled:false});g.translate(0,0,-.08);return g;})();
const edge=(x0:number,y0:number,x1:number,y1:number)=>({pos:[(x0+x1)/2,(y0+y1)/2,0] as V3,len:Math.hypot(x1-x0,y1-y0),rot:Math.atan2(y1-y0,x1-x0)});
function Slider({cut}:{cut:boolean}){
  return <group>
    <mesh geometry={plateGeo} position-z={-.14} castShadow><meshStandardMaterial color={K.steelMid} flatShading/></mesh>
    {!cut&&<mesh geometry={plateGeo} position-z={.14} castShadow><meshStandardMaterial color={K.steelMid} flatShading/></mesh>}
    {[edge(-.75,.5,-.28,-.5),edge(.75,.5,.28,-.5)].map((e,i)=><Box key={i} size={[e.len,.07,.3]} pos={e.pos} rot={e.rot} color={K.steel}/>)}
    <mesh geometry={wedgeGeo} position={[0,.05,0]} castShadow><meshStandardMaterial color={K.steelDark} flatShading/></mesh>
  </group>;
}

// ---- the zipper on a jacket ---------------------------------------------------------------------------------------------------
function Zip({gf,env,cut,T,evs}:{gf:number,env:boolean,cut:boolean,T:Record<string,number>|null,evs:Ev[]}){
  const tt=(k:string)=>T?T[k]:null,slA=arrive(gf,tt('slider'),[0,4,2.5],.9),yS=slA.vis?sliderY(gf):-9,v=sliderV(gf);
  const tabA=arrive(gf,tt('tab'),[2.5,3,2.5],-1.2),aA=act(evs,gf,'force_arrows',45);
  const N=22,PT=.2,Y0=-2.2,M=20,SEG=.26,seg=Array.from({length:M},(_,j)=>-2.6+SEG*(j+.5));
  const tabAng=-(v/.157)*.35+.05*Math.sin(gf*.11);
  const map:Record<string,Glow[]>={tape:[{pos:[-.95,0,0],size:[.9,5.4,.3]},{pos:[.95,0,0],size:[.9,5.4,.3]}],teeth:[{pos:[0,(yS-2.5)/2,0],size:[.8,Math.max(.5,yS+2.5),.4]}],
    slider:[{pos:[0,yS,.05],size:[1.7,1.3,.7]}],tab:[{pos:[0,yS-.45,.2],size:[.6,1.1,.3]}],stop:[{pos:[0,2.5,0],size:[1.1,.5,.4]},{pos:[0,-2.5,0],size:[1.1,.5,.4]}]};
  return <>
    {env&&Array.from({length:19}).map((_,i)=><Box key={i} size={[.4,12,.05]} pos={[(i-9)*1.1,0,-1.8]} color={K.stripe}/>)}
    {[-1,1].map(side=>{
      const aT=arrive(gf,tt('tape'),[side*4.5,0,2.5],side*.5);
      return <React.Fragment key={side}>
        {env&&seg.map((y,j)=>{const x=side*(Math.abs(toothX(y,yS,side))+.38+.25+1.3);
          return <Box key={'f'+j} size={[2.6,SEG,.08]} pos={[x,y,-.06]} color={(j%2)?K.denim:K.denimDark}/>;})}
        {aT.vis&&<group position={aT.pos} rotation-z={aT.rot}>
          {seg.map((y,j)=><Box key={'t'+j} size={[.5,SEG,.05]} pos={[side*(Math.abs(toothX(y,yS,side))+.38),y,0]} color={K.tape}/>)}
          {env&&seg.map((y,j)=><Box key={'s'+j} size={[.05,.1,.02]} pos={[side*(Math.abs(toothX(y,yS,side))+.38+.23),y,.04]} color={K.stitch}/>)}
        </group>}
      </React.Fragment>;})}
    {Array.from({length:N*2}).map((_,k)=>{
      const side=k%2?1:-1,i=k>>1,y=Y0+i*PT+(side>0?PT/2:0),a=arrive(gf,T?T.teeth+k*3:null,[side*4,y+1.5,2.5],side*1.2);
      if(!a.vis)return null;
      return <group key={k} position={[toothX(y,yS,side)+a.pos[0],y+a.pos[1],a.pos[2]]} rotation-z={a.rot}>
        <Box size={[.26,.15,.14]} pos={[0,0,0]} color={side<0?K.toothL:K.toothR}/>
        <mesh position={[-side*.1,0,0]} castShadow><icosahedronGeometry args={[.075,0]}/><meshStandardMaterial color={side<0?K.toothL:K.toothR} flatShading/></mesh>
      </group>;})}
    {[-1,1].map(side=>{const a=arrive(gf,tt('stop'),[side*3,3,2.5],side*1.5);
      return a.vis?<group key={side} position={[a.pos[0]+side*.2,2.5+a.pos[1],a.pos[2]]} rotation-z={a.rot}><Box size={[.3,.22,.18]} pos={[0,0,0]} color={K.steelDark}/></group>:null;})}
    {(()=>{const a=arrive(gf,tt('stop'),[0,-3,2.5],-1.5);return a.vis?<group position={[a.pos[0],-2.5+a.pos[1],a.pos[2]]} rotation-z={a.rot}>
      <Box size={[.75,.3,.2]} pos={[0,0,0]} color={K.steelDark}/><Box size={[.12,.3,.26]} pos={[.28,0,0]} color={K.steel}/></group>:null;})()}
    {slA.vis&&<group position={[slA.pos[0],yS+slA.pos[1],slA.pos[2]]} rotation-z={slA.rot}>
      <Slider cut={cut}/>
      {tabA.vis&&<group position={[tabA.pos[0],.52+tabA.pos[1],.17+tabA.pos[2]]} rotation-z={tabA.rot+tabAng}>
        <mesh rotation-x={Math.PI/2}><torusGeometry args={[.08,.03,6,8]}/><meshStandardMaterial color={K.steel} flatShading/></mesh>
        <Box size={[.36,.85,.06]} pos={[0,-.5,.03]} color={K.steelMid}/><Box size={[.2,.12,.07]} pos={[0,-.85,.03]} color={K.steelDark}/>
      </group>}
    </group>}
    {env&&<>
      <mesh position={[0,2.95,-.1]} castShadow><cylinderGeometry args={[.06,.06,.7,6]}/><meshStandardMaterial color={K.hanger} flatShading/></mesh>
      <mesh position={[0,3.4,-.1]} rotation-x={Math.PI/2} castShadow><torusGeometry args={[.3,.05,6,10,Math.PI*1.4]}/><meshStandardMaterial color={K.hanger} flatShading/></mesh>
      <mesh position={[-2.3,-1.0,.0]} rotation-x={Math.PI/2}><cylinderGeometry args={[.2,.2,.06,8]}/><meshStandardMaterial color={K.steel} flatShading/></mesh>
      <Box size={[1.3,.4,.1]} pos={[2.2,-.6,.0]} color={K.denimDark}/>
    </>}
    {aA>0&&<>
      <Arrow from={[v>=0?-1.3:-.4,yS+.3,.35]} dir={[v>=0?1:-1,0,0]} len={.7} s={aA}/>
      <Arrow from={[v>=0?1.3:.4,yS+.3,.35]} dir={[v>=0?-1:1,0,0]} len={.7} s={aA}/></>}
    <Glows evs={evs} gf={gf} map={map}/>
  </>;
}
function Scene({i,gf}:{i:number,gf:number}){
  const s=script.shots[i],evs=shotEvents(s.id),asm=s.sustain==='assembly';
  let T:Record<string,number>|null=null;
  if(asm){T={};['tape','teeth','slider','tab','stop'].forEach((p,k)=>{const e=script.events.find(x=>x.shot===s.id&&x.kind==='attach'&&x.target===p);T![p]=e?e.at:s.start+10+k*40;});}
  return <Zip gf={gf} env={s.type!=='insert'} cut={s.type==='cutaway'} T={T} evs={evs}/>;
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

export function Zipper(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:K.bg}}>
    {script.shots.map((s,i)=><Sequence key={s.id} from={s.start} durationInFrames={s.end-s.start} layout="none"><Shot i={i}/></Sequence>)}
    {script.captions.map(c=><Caption key={c.id} c={c} f={f}/>)}
  </AbsoluteFill>;
}
