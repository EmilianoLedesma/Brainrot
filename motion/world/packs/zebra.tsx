import React from 'react';
import {AbsoluteFill,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import {EZ,FPS,H,W,clip,ez} from '../kit';
import type {Script,Pack} from '../kit';

// Scene pack zebra for the continuous-world edit, ported from experiments/. The script arrives as an argument (a pure function of the props), never as a module import.
export function makeZebra(script:Script):Pack{

// Why zebras have stripes: one continuous soft low-poly savanna. The hero is the savanna with a herd; in front of it one round grassy stage per idea.
// Director v3: a calm camera (mostly holds, one pose per beat, angle and height fixed within a station), framing with margin, and actions that never
// overlap (each has a fixed duration; the director may not start one before the previous on the same station ends). The animals are built from smooth
// low-poly primitives (ellipsoids, tapered limbs, cones) with stripes painted per vertex, not from boxes. Every animated value is a pure function of
// useCurrentFrame() (never useFrame); nothing moves unless an action says so.
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const K={sky:'#D6EAF6',grass:'#CFDCA0',grassDark:'#BFD08E',dry:'#E3D49A',plinthTop:'#C7DA98',plinthSide:'#B89F72',rock:'#BDB4A4',rockDark:'#A39A8A',water:'#8CC8F2',trunk:'#8F6F55',leaf:'#A3CC8F',leafDark:'#88B87E',
  white:'#F8F6F0',black:'#2A2F3A',horse:'#B98355',horseMane:'#5E4029',cow:'#30353E',lion:'#E4B36E',mane:'#A5703E',hyena:'#B5A38B',hyenaDark:'#5A4B3F',fly:'#2E3440',wing:'#EAF4FF',eye:'#86D6A8',
  skin:'#E7B79F',hair:'#8E6A52',red:'#E5333B',term:'#FFD23F',hl:'#FFFFFF',sun:'#FFE6A8',therm:'#FF9A5C',glass:'#EEF6FF',trace:'#6FB2FF',stroke:'#1F2A44',paint:'#F8F6F0',brush:'#8A6A52'};
type V3=[number,number,number];
const EXH=['coat','predators','heat','hair','landing','coats','cows'];
const TARGETS=['savanna',...EXH];
const PARTS=['HUELLA','CAMUFLAJE','DEPREDADORES','CALOR','TÁBANOS','CABALLOS','COBERTORES','VACAS','PINTURA','PELO'];
const MOVES=['hold','push_in','pull_out','orbit_left','orbit_right','pan_left','pan_right'];
const HERO:V3=[0,0,-10];
const POS:Record<string,V3>={savanna:HERO,...Object.fromEntries(EXH.map((n,i)=>[n,[(i-3)*20,.5,12] as V3]))};
const WIDE_X:Record<string,number>={coat:1,predators:1.25,heat:1,hair:1,landing:1.25,coats:1.25,cows:1.25};   // plinth stretch along x
const DIST:Record<string,number>={wide:112,medium:88,close:62};   // every stage keeps its subjects inside +-8 units: about 75% of the frame width at medium
const AZ:Record<string,number>={left:-.62,front:0,right:.62},EL:Record<string,number>={low:.2,mid:.34,high:.62};
const GLOW:Record<string,V3>={savanna:[22,7,12],coat:[14,7.5,8],predators:[22,6,9],heat:[18,8,6],hair:[12,5,9],landing:[22,7,8],coats:[26,7.5,8],cows:[22,7,8]};
const wps=script.waypoints,AC=script.actions;

(function validate(){
  if(wps[0].focus!=='savanna'||wps[0].dist!=='wide'||wps[0].nature!=='context')throw new Error('the first waypoint must be savanna/context/wide');
  wps.forEach((w,i)=>{
    if(!TARGETS.includes(w.focus)||!DIST[w.dist])throw new Error(`waypoint ${w.id}: invalid focus or dist`);
    if(!MOVES.includes(w.shot.move)||!AZ.hasOwnProperty(w.shot.angle)||!EL.hasOwnProperty(w.shot.height))throw new Error(`waypoint ${w.id}: incomplete shot`);
    if(i&&w.at-wps[i-1].at<script.flight)throw new Error(`waypoint ${w.id}: closer than one flight (${script.flight} frames) to the previous one`);
    if(i&&w.focus===wps[i-1].focus&&(w.shot.angle!==wps[i-1].shot.angle||w.shot.height!==wps[i-1].shot.height))throw new Error(`waypoint ${w.id}: angle or height changed inside a station`);
    if(i&&w.shot.move!=='hold'&&wps[i-1].shot.move!=='hold')throw new Error(`waypoint ${w.id}: two camera moves in a row`);
    if(!w.show)throw new Error(`waypoint ${w.id}: needs a description of what is on screen`);
  });
  if(wps.filter(w=>w.shot.move!=='hold').length>Math.ceil(wps.length*.4))throw new Error('too many camera moves: the camera must mostly hold');
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
const aim=(w:{focus:string}):V3=>{const p=POS[w.focus];return [p[0],p[1]+(w.focus==='savanna'?2.5:2.8),p[2]];};
const distOf=(w:{focus:string,dist:string})=>DIST[w.dist]*(w.focus==='savanna'?.66:1);

// ---- calm camera: a pose per beat; most beats hold (a tiny drift); flights blend one pose into the next ------------------------------------------------
type Pose={az:number,el:number,d:number,t:V3};
function pose(w:Script['waypoints'][number],u:number):Pose{
  const e=smooth(clip(u)),T=aim(w);let az=AZ[w.shot.angle],el=EL[w.shot.height],d=distOf(w);
  switch(w.shot.move){
    case 'push_in':d*=1.1-.18*e;break;case 'pull_out':d*=.92+.18*e;break;
    case 'orbit_left':az+=.2-.4*e;break;case 'orbit_right':az+=-.2+.4*e;break;
    case 'pan_left':T[0]+=2.4-4.8*e;break;case 'pan_right':T[0]+=-2.4+4.8*e;break;
    default:az+=.02*Math.sin(e*3);
  }
  return {az,el,d,t:T};
}
function camAt(gf:number){
  let k=0;for(let i=0;i<wps.length;i++)if(wps[i].at<=gf)k=i;
  const cur=wps[k],prev=wps[Math.max(0,k-1)],t=k===0?1:smooth(clip((gf-cur.at)/script.flight));
  const A=pose(prev,1),Bp=pose(cur,(gf-cur.start)/Math.max(1,cur.end-cur.start)),L=(a:number,b:number)=>a+(b-a)*t;
  const az=L(A.az,Bp.az),el=L(A.el,Bp.el),d=Math.exp(L(Math.log(A.d),Math.log(Bp.d))),tg=A.t.map((v,i)=>L(v,Bp.t[i])) as V3;
  return {target:tg,pos:[tg[0]+d*Math.sin(az)*Math.cos(el),tg[1]+d*Math.sin(el),tg[2]+d*Math.cos(az)*Math.cos(el)] as V3};
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
    <hemisphereLight args={['#F4F8FF','#D8DDA6',.6*Math.PI]}/>
    <primitive object={tgt} position={c.target}/>
    <directionalLight target={tgt} position={[c.target[0]+14,c.target[1]+26,c.target[2]+16]} intensity={.72*Math.PI} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048} shadow-radius={5}
      shadow-camera-left={-34} shadow-camera-right={34} shadow-camera-top={34} shadow-camera-bottom={-34} shadow-camera-near={.5} shadow-camera-far={120} shadow-bias={-.0004}/>
  </>;
}

// ---- primitives -------------------------------------------------------------------------------------------------------------------------------------
const GEO=new Map<string,THREE.BufferGeometry>();
const rbg=(w:number,h:number,d:number,r:number)=>{const k=[w,h,d,r].map(v=>v.toFixed(3)).join();let g=GEO.get(k);
  if(!g){g=new RoundedBoxGeometry(w,h,d,2,Math.max(.001,Math.min(r,w/2-.001,h/2-.001,d/2-.001)));GEO.set(k,g);}return g;};
const B=({s,p,c,r=[0,0,0],e=0,rad=.12}:{s:V3,p:V3,c:string,r?:V3,e?:number,rad?:number})=>
  <mesh geometry={rbg(s[0],s[1],s[2],rad)} position={p} rotation={r} castShadow receiveShadow><meshStandardMaterial color={c} emissive={e?c:'#000000'} emissiveIntensity={e} roughness={.9}/></mesh>;
const Cyl=({r,r2,h,p,c,seg=14,rot=[0,0,0],o=1}:{r:number,r2?:number,h:number,p:V3,c:string,seg?:number,rot?:V3,o?:number})=>
  <mesh position={p} rotation={rot} castShadow receiveShadow><cylinderGeometry args={[r,r2??r,h,seg]}/><meshStandardMaterial color={c} roughness={.9} transparent={o<1} opacity={o}/></mesh>;
const Ball=({r,p,c,s=[1,1,1],d=2,e=0,o=1,flat=false,rot=[0,0,0]}:{r:number,p:V3,c:string,s?:V3,d?:number,e?:number,o?:number,flat?:boolean,rot?:V3})=>
  <mesh position={p} scale={s} rotation={rot} castShadow={o>=1}><icosahedronGeometry args={[r,d]}/><meshStandardMaterial color={c} flatShading={flat} roughness={.95} emissive={e?c:'#000000'} emissiveIntensity={e} transparent={o<1} opacity={o} depthWrite={o>=1}/></mesh>;
const Cone=({r,h,p,c,rot=[0,0,0],seg=10}:{r:number,h:number,p:V3,c:string,rot?:V3,seg?:number})=><mesh position={p} rotation={rot} castShadow><coneGeometry args={[r,h,seg]}/><meshStandardMaterial color={c} roughness={.9}/></mesh>;
const Y=new THREE.Vector3(0,1,0);
function Arrow({from,dir,len,s}:{from:V3,dir:V3,len:number,s:number}){  // red arrow: rare, only where the director asked for one
  if(s<=.02)return null;
  const d=new THREE.Vector3(...dir).normalize(),A=new THREE.Vector3(...from),L=len*s,end=A.clone().addScaledVector(d,Math.max(L-.3,.001)),tip=A.clone().addScaledVector(d,L),q=new THREE.Quaternion().setFromUnitVectors(Y,d);
  const mid=A.clone().add(end).multiplyScalar(.5),len2=end.clone().sub(A).length();
  return <group><mesh position={mid.toArray()} quaternion={q}><cylinderGeometry args={[.1,.1,Math.max(len2,.001),8]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.4}/></mesh>
    <mesh position={tip.clone().addScaledVector(d,-.25).toArray()} quaternion={q}><coneGeometry args={[.28,.5,8]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.4}/></mesh></group>;
}
const lerp3=(a:V3,b:V3,t:number):V3=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];

// ---- actions: the director locks a named action to a narration word; durations match the table in director.py --------------------------------------
type Ap={on:boolean,p:number,age:number};
function ap(gf:number,t:string,n:string,d:number):Ap{let at=-1e9;for(const a of AC)if(a.target===t&&a.name===n&&a.at<=gf&&a.at>at)at=a.at;const age=gf-at;return {on:at>-1e8,p:clip(age/d),age};}
const pers=(gf:number,t:string,n:string,d:number)=>ap(gf,t,n,d).p;
const trn=(gf:number,t:string,n:string,d:number)=>{const a=ap(gf,t,n,d);return a.on&&a.age<d?a.p:-1;};

// ---- organic animals: smooth low-poly primitives with per-vertex colours (stripes are painted on the vertices) ----------------------------------------------
const VC=new Map<string,THREE.BufferGeometry>();
type Fn=(x:number,y:number,z:number)=>THREE.Color;
function vgeo(key:string,make:()=>THREE.BufferGeometry,fn:Fn,off:V3=[0,0,0]){
  let g=VC.get(key);
  if(!g){g=make();const p=g.attributes.position,c=new Float32Array(p.count*3);
    for(let i=0;i<p.count;i++){const col=fn(p.getX(i)+off[0],p.getY(i)+off[1],p.getZ(i)+off[2]);c[i*3]=col.r;c[i*3+1]=col.g;c[i*3+2]=col.b;}
    g.setAttribute('color',new THREE.BufferAttribute(c,3));VC.set(key,g);}
  return g;
}
const ss=(a:number,b:number,x:number)=>{const t=clip((x-a)/(b-a));return t*t*(3-2*t);};
const WHITE=new THREE.Color(K.white),BLACK=new THREE.Color(K.black);
const mixC=(a:THREE.Color,b:THREE.Color,t:number)=>a.clone().lerp(b,clip(t));
type Look={pat:'none'|'zebra'|'coat'|'paint',base:string,seed?:number,coat?:'black'|'white'|'stripe',mix?:number,paint?:number,fade?:number,trace?:number};
type Dim={rx:number,ry:number,rz:number,legH:number,legR:number,by:number,hip:number,neck:[number,number,number,number,number,number],head:[number,number,number,number,number,number,number],tail:number};
const DIM:Record<string,Dim>={
  zebra:{rx:2,ry:1,rz:.85,legH:2,legR:.17,by:2.4,hip:1.25,neck:[1.7,2.95,3.0,4.0,.56,.36],head:[3.3,4.1,.78,.46,.38,-.5,.5],tail:1.3},
  horse:{rx:2.1,ry:1.05,rz:.88,legH:2.15,legR:.18,by:2.5,hip:1.3,neck:[1.75,3.05,3.1,4.2,.58,.38],head:[3.45,4.3,.85,.48,.4,-.5,.55],tail:1.5},
  cow:{rx:2.1,ry:1.1,rz:1,legH:1.5,legR:.24,by:2.1,hip:1.3,neck:[1.95,2.6,2.85,2.95,.62,.5],head:[3.15,2.85,.7,.52,.46,-.15,.4],tail:1.1},
  lion:{rx:1.9,ry:.95,rz:.85,legH:1.7,legR:.27,by:2.2,hip:1.2,neck:[1.5,2.6,2.3,3.1,.62,.56],head:[2.65,3.1,.6,.55,.5,-.1,.35],tail:1.4},
  hyena:{rx:1.5,ry:.78,rz:.66,legH:1.5,legR:.2,by:1.95,hip:.95,neck:[1.2,2.4,1.9,2.85,.46,.4],head:[2.25,2.9,.58,.42,.38,-.35,.3],tail:.8},
};
function bodyColor(kind:string,look:Look,part:string,x:number,y:number,z:number,D:Dim):THREE.Color{
  const seed=look.seed||0,stripe=(f:number,k=.1)=>ss(-k,k,f);
  const zebra=()=>{
    if(part==='leg'){return y<.28?BLACK:mixC(WHITE,BLACK,stripe(Math.sin(y*8.6+seed)));}
    if(part==='head'){return x>D.head[0]+.4?BLACK:mixC(WHITE,BLACK,stripe(Math.sin((x*1.2+y*.9+seed)*9)));}
    const belly=part==='body'&&y<D.by-D.ry*.62;
    const f=part==='body'?Math.sin((x+.1*(y-D.by)*(y-D.by)+seed*.9)*9.2):Math.sin((x*.9+y*.9+seed*.9)*8);
    const col=belly?WHITE:mixC(WHITE,BLACK,stripe(f,.17));
    return look.trace&&look.trace>0&&!belly&&Math.floor(((x+2.3)/.3))<look.trace*14&&f>0?new THREE.Color(K.trace):col;
  };
  if(look.pat==='zebra')return zebra();
  if(look.pat==='coat'&&part==='body'){
    const c=look.coat==='black'?BLACK:look.coat==='white'?WHITE:zebra(),h=new THREE.Color(look.base);
    return mixC(h,c,look.mix??1);
  }
  if(look.pat==='paint'){
    const base=new THREE.Color(look.base),front=-2.3+4.6*(look.paint??0);
    if(part!=='body'&&part!=='neck')return base;
    const painted=x<front&&Math.sin((x+seed*.4+.4*y)*9)>0.1&&y>D.by-D.ry*.75;
    return painted?mixC(WHITE,base,look.fade??0):base;
  }
  if(kind==='hyena'&&part==='body'&&(Math.sin(x*5+y*3)*Math.sin(z*6+x)>.55))return new THREE.Color(K.hyenaDark);
  return new THREE.Color(part==='head'&&x>D.head[0]+.5&&kind==='hyena'?K.hyenaDark:look.base);
}
const LEG_ORDER:[number,number][]=[[1,1],[-1,-1],[1,-1],[-1,1]];   // diagonal pairs
function Animal({kind,look,walk=null,headDown=0}:{kind:string,look:Look,walk?:number|null,headDown?:number}){
  const D=DIM[kind],lk=JSON.stringify([kind,look.pat,look.base,look.seed||0,look.coat||'',Math.round((look.mix??1)*8),Math.round((look.paint??0)*16),Math.round((look.fade??0)*6),Math.round((look.trace??0)*14)]);
  const body=vgeo('b'+lk,()=>new THREE.SphereGeometry(1,48,32).scale(D.rx,D.ry,D.rz).translate(0,D.by,0),(x,y,z)=>bodyColor(kind,look,'body',x,y,z,D));
  const nb:V3=[D.neck[0],D.neck[1],0],nt:V3=[D.neck[2],D.neck[3],0],len=Math.hypot(nt[0]-nb[0],nt[1]-nb[1]),ang=Math.atan2(nt[0]-nb[0],nt[1]-nb[1]);
  const neck=vgeo('n'+lk,()=>new THREE.CylinderGeometry(D.neck[5],D.neck[4],len,14,6).translate(0,len/2,0).rotateZ(-ang),(x,y,z)=>bodyColor(kind,look,'neck',x+nb[0],y+nb[1],z,D));
  const head=vgeo('h'+lk,()=>new THREE.SphereGeometry(1,22,16).scale(D.head[2],D.head[3],D.head[4]).rotateZ(D.head[5]).translate(D.head[0]-nb[0],D.head[1]-nb[1],0),(x,y,z)=>bodyColor(kind,look,'head',x+nb[0],y+nb[1],z,D));
  const walkA=(i:number)=>walk===null?0:Math.sin(walk*2.2+(i<2?0:Math.PI))*.42*(i%2?-1:1);
  const maneC=kind==='zebra'?K.black:kind==='horse'?K.horseMane:K.mane;
  return <group>
    <mesh geometry={body} castShadow receiveShadow><meshStandardMaterial vertexColors roughness={.9}/></mesh>
    {LEG_ORDER.map(([sx,sz],i)=>{const px=sx*D.hip,pz=sz*D.rz*.55,top:V3=[px,D.legH,pz];
      const lg=vgeo('l'+lk+i,()=>new THREE.CylinderGeometry(D.legR*1.15,D.legR*.78,D.legH,12,8).translate(0,-D.legH/2,0),(x,y,z)=>bodyColor(kind,look,'leg',x+px,y+D.legH,z+pz,D));
      return <group key={i} position={top} rotation-z={walkA(i)}><mesh geometry={lg} castShadow><meshStandardMaterial vertexColors roughness={.9}/></mesh>
        <Cyl r={D.legR*.9} h={.26} p={[0,-D.legH+.12,0]} c={K.black} seg={10}/></group>;})}
    <group position={nb} rotation-z={-headDown*.75}>
      <mesh geometry={neck} castShadow><meshStandardMaterial vertexColors roughness={.9}/></mesh>
      <mesh geometry={head} castShadow><meshStandardMaterial vertexColors roughness={.9}/></mesh>
      {(kind==='zebra'||kind==='horse')&&<Ball r={.34} p={[D.head[0]-nb[0]+.62,D.head[1]-nb[1]-.2,0]} c={kind==='zebra'?K.black:look.base} s={[1.1,.8,.85]}/>}
      {[-1,1].map(s=><Cone key={s} r={kind==='hyena'?.2:.13} h={kind==='hyena'?.45:.5} p={[D.head[0]-nb[0]-.3,D.head[1]-nb[1]+.45,s*D.head[4]*.7]} c={kind==='zebra'?K.black:kind==='lion'?K.mane:kind==='cow'?K.cow:K.horseMane} rot={[s*.25,0,-.15]}/>)}
      {[-1,1].map(s=><Ball key={'e'+s} r={.07} p={[D.head[0]-nb[0]+.25,D.head[1]-nb[1]+.12,s*D.head[4]*.78]} c={K.black} d={1}/>)}
      {(kind==='zebra'||kind==='horse')&&[0,1,2,3,4,5].map(i=>{const f=i/5;return <Cone key={'m'+i} r={.1} h={.42} p={[(nt[0]-nb[0])*f*.9-.12,(nt[1]-nb[1])*f*.95+.45,0]} c={maneC} rot={[0,0,.5]} seg={6}/>;})}
      {kind==='lion'&&<Ball r={.95} p={[D.head[0]-nb[0]-.35,D.head[1]-nb[1]-.1,0]} c={K.mane} s={[.9,1,1.05]} d={1}/>}
    </group>
    <group position={[-D.rx+.1,D.by+.2,0]} rotation-z={.22}><Cyl r={.07} h={D.tail} p={[0,-D.tail/2,0]} c={kind==='zebra'||kind==='horse'?maneC:K.hyena} seg={8}/>
      <Ball r={.22} p={[0,-D.tail,0]} c={kind==='lion'?K.mane:maneC} s={[.8,1.2,.8]} d={1}/></group>
  </group>;
}
// walking legs: the swing is a function of the distance walked, so it only moves while the animal moves
const walkPh=(x:number)=>x*1.7;

// ---- a fly: thorax, abdomen, big eyes, wings, mouthpart. Wings beat only while it flies (`flying`) ---------------------------------------------------
function Fly({p,yaw=0,pitch=0,s=1,flying=true,gf=0,prob=0}:{p:V3,yaw?:number,pitch?:number,s?:number,flying?:boolean,gf?:number,prob?:number}){
  const fl=flying?Math.sin(gf*1.9)*.55:.15;
  return <group position={p} rotation={[0,yaw,pitch]} scale={s}>
    <Ball r={.2} p={[0,0,0]} c={K.fly} d={1}/><Ball r={.18} p={[-.3,-.02,0]} c={'#3B4352'} s={[1.5,.85,.85]} d={1}/>
    <Ball r={.13} p={[.2,.03,0]} c={K.fly} d={1}/>{[-1,1].map(z=><Ball key={z} r={.075} p={[.26,.07,z*.09]} c={K.eye} d={1}/>)}
    {[-1,1].map(z=><mesh key={'w'+z} position={[-.05,.16,z*.16]} rotation={[z*(.7+fl),0,0]} scale={[1,.03,.38]}><sphereGeometry args={[.3,10,8]}/><meshStandardMaterial color={K.wing} transparent opacity={.6} roughness={.5}/></mesh>)}
    <Cone r={.03} h={.2+prob*1.2} p={[.34+prob*.02,-.1-prob*.5,0]} c={K.fly} rot={[0,0,Math.PI*(.85-prob*.15)]} seg={6}/>
  </group>;
}
const flyYaw=(a:V3,b:V3)=>Math.atan2(-(b[2]-a[2]),b[0]-a[0]);
function Trail({pts}:{pts:V3[]}){return <>{pts.map((q,i)=><Ball key={i} r={.1} p={q} c={K.trace} e={.4} d={0}/>)}</>;}

// ---- scenery ------------------------------------------------------------------------------------------------------------------------------------------
function Acacia({x,z,s=1,lean=0}:{x:number,z:number,s?:number,lean?:number}){
  return <group position={[x,0,z]} scale={s} rotation-y={lean}>
    <Cyl r={.55} r2={.9} h={5} p={[0,2.5,0]} c={K.trunk} seg={9}/><Cyl r={.28} r2={.4} h={3.2} p={[-1.2,6.2,0]} c={K.trunk} seg={8} rot={[0,0,.6]}/><Cyl r={.28} r2={.4} h={3} p={[1.3,6,0]} c={K.trunk} seg={8} rot={[0,0,-.7]}/>
    <Ball r={3.6} p={[0,8.3,0]} c={K.leaf} s={[1.35,.34,1.2]} d={2}/><Ball r={2.6} p={[-2.4,7.5,1]} c={K.leafDark} s={[1.2,.3,1.1]} d={2}/><Ball r={2.2} p={[2.8,7.4,-.6]} c={K.leaf} s={[1.2,.3,1]} d={2}/>
  </group>;
}
const Tuft=({x,z,s=1}:{x:number,z:number,s?:number})=><group position={[x,0,z]} scale={s}>{[-.28,0,.28].map((o,i)=><Cone key={i} r={.1} h={1.2+i%2*.4} p={[o,.6,0]} c={i%2?K.grassDark:K.grass} rot={[0,0,o*1.4]} seg={5}/>)}</group>;
const Rock=({x,z,s=1}:{x:number,z:number,s?:number})=><Ball r={s} p={[x,s*.45,z]} c={K.rock} s={[1.25,.75,1]} d={1} flat/>;
const Env=React.memo(function Env(){
  return <>
    <mesh position={[0,-.3,-60]} receiveShadow><boxGeometry args={[700,.6,420]}/><meshStandardMaterial color={K.grass} roughness={1}/></mesh>
    <mesh position={[0,-.28,30]} receiveShadow><boxGeometry args={[700,.6,100]}/><meshStandardMaterial color={K.grassDark} roughness={1}/></mesh>
    <Cyl r={8} h={.2} p={[0,.05,-15]} c={K.water} seg={28}/><Cyl r={9} h={.15} p={[0,.02,-15]} c={K.dry} seg={28}/>
    {[[-2,-12,1.2],[14,-11,1.4],[10,-23,1.1],[0,-21,.9],[-11,-24,1.5],[22,-18,1.1]].map(([x,z,s],i)=><Rock key={i} x={x} z={z} s={s}/>)}
    {[[-38,-40,1,.3],[32,-46,1.1,-.4],[-16,-66,1.2,.8],[14,-84,1.3,.5],[56,-34,.9,.1],[-60,-30,1,-.2]].map(([x,z,s,l],i)=><Acacia key={i} x={x} z={z} s={s} lean={l}/>)}
    {Array.from({length:60}).map((_,i)=><Tuft key={i} x={-70+((i*37)%140)} z={-60+((i*53)%72)} s={.9+(i%3)*.25}/>)}
    {[[-60,-90,40,9],[20,-100,60,12],[75,-85,38,8]].map(([x,z,w,h],i)=><Ball key={i} r={1} p={[x,0,z]} c={K.grassDark} s={[w,h,14]} d={1}/>)}
    <mesh position={[0,60,-170]}><boxGeometry args={[900,200,.5]}/><meshStandardMaterial color={K.sky}/></mesh>
    {[[-70,42],[20,50],[90,38],[-20,34]].map(([x,y],i)=><Ball key={i} r={4} p={[x,y,-150]} c={K.white} s={[3.4,1,1.2]} d={1}/>)}
  </>;
});
function Plinth({n}:{n:string}){const sx=WIDE_X[n]||1;return <group scale={[sx,1,1]}><Cyl r={7.4} h={.7} p={[0,.35,0]} c={K.plinthSide} seg={36}/><Cyl r={7} h={.12} p={[0,.74,0]} c={K.plinthTop} seg={36}/></group>;}

// ---- the hero: the herd on the savanna. fly_strike: a fly dives at a zebra, hits it and bounces off; herd_move: the herd walks on ------------------------
function Savanna({gf}:{gf:number}){
  const mv=ap(gf,'savanna','herd_move',200),walkX=smooth(mv.p)*11,walking=mv.on&&mv.age<200,st=trn(gf,'savanna','fly_strike',150);
  const Z:[V3,number,number,number][]=[[[-6.5,0,-6],0,1,0],[[-2.5,0,-10],0,3,.9],[[1.8,0,-7],Math.PI,5,0],[[5.5,0,-11],0,7,.8]];
  let fp:V3|null=null,fy=0,fpitch=0,bump=0;
  if(st>=0){const hit:V3=[Z[0][0][0]+walkX+.4,2.75,Z[0][0][2]+.9],start:V3=[hit[0]-15,hit[1]+7,hit[2]+7],away:V3=[hit[0]-8,hit[1]+7.5,hit[2]+9];
    if(st<.5){const t=st/.5;fp=lerp3(start,hit,t*t);fy=flyYaw(start,hit);fpitch=-.5;}
    else if(st<.58){fp=[hit[0]+Math.sin(st*120)*.05,hit[1],hit[2]];fy=flyYaw(start,hit);bump=1;}
    else{const t=smooth((st-.58)/.42);fp=lerp3(hit,away,t);fy=flyYaw(hit,away)+Math.PI;fpitch=.3;}}
  return <group>
    {Z.map(([p,yaw,seed,hd],i)=>{const wk=i===0||i===1||i===3?walkX:0;const px=p[0]+wk;
      return <group key={i} position={[px,0,p[2]]} rotation-y={yaw}><Animal kind="zebra" look={{pat:'zebra',base:K.white,seed}} walk={walking?walkPh(px):null} headDown={hd}/></group>;})}
    {fp&&<Fly p={fp} yaw={fy} pitch={fpitch} s={2.8} gf={gf} flying={bump===0}/>}
  </group>;
}

// ---- coat: pair_in brings a second zebra with a different pattern; pattern_trace lights the first one's stripes one by one ---------------------------------
function CoatEx({gf}:{gf:number}){
  const pi=ap(gf,'coat','pair_in',120),e=smooth(pi.p),bx=pi.on?10-6.6*e:99,walking=pi.on&&pi.age<120,tr=ap(gf,'coat','pattern_trace',110);
  return <group><Plinth n="coat"/>
    <group position={[-3.2,.8,0]}><Animal kind="zebra" look={{pat:'zebra',base:K.white,seed:2,trace:tr.on?tr.p:0}}/></group>
    {pi.on&&<group position={[bx,.8,0]} rotation-y={Math.PI}><Animal kind="zebra" look={{pat:'zebra',base:K.white,seed:6}} walk={walking?walkPh(bx):null}/></group>}
  </group>;
}

// ---- predators: lion_stalk (a lion creeps toward the herd), haze (the stripes disappear from afar) -----------------------------------------------------
function Predators({gf}:{gf:number}){
  const ls=ap(gf,'predators','lion_stalk',220),lx=-9+5.5*smooth(ls.p),walking=ls.on&&ls.age<220,hz=trn(gf,'predators','haze',100),ha=hz<0?0:Math.sin(Math.PI*hz);
  return <group><Plinth n="predators"/>
    <group position={[ls.on?lx:-9,.8,2]} scale={.85}><Animal kind="lion" look={{pat:'none',base:K.lion}} walk={walking?walkPh(lx):null} headDown={ls.on?.25*ls.p:0}/></group>
    <group position={[-7.5,.8,-3.5]} scale={.85}><Animal kind="hyena" look={{pat:'none',base:K.hyena}}/></group>
    <group position={[5.6,.8,-1]} rotation-y={Math.PI} scale={.8}><Animal kind="zebra" look={{pat:'zebra',base:K.white,seed:3}} headDown={.8}/></group>
    <group position={[2.5,.8,3]} scale={.8}><Animal kind="zebra" look={{pat:'zebra',base:K.white,seed:8}}/></group>
    {ha>0&&<Ball r={5} p={[.2,3,0]} c={'#E6EBF0'} s={[.5,.75,1.1]} d={2} o={.68*ha}/>}
  </group>;
}

// ---- heat: three barrels dressed in hides, three thermometers; sun_up, temps_read -----------------------------------------------------------------------
const HIDE=['horse','zebra','cow'];
function Barrel({kind,x}:{kind:string,x:number}){
  const g=vgeo('barrel'+kind,()=>new THREE.CylinderGeometry(1.5,1.5,2.8,28,8).translate(0,1.4,0),(px,py,pz)=>kind==='zebra'?mixC(WHITE,BLACK,ss(-.12,.12,Math.sin(Math.atan2(pz,px)*9))):new THREE.Color(kind==='horse'?K.horse:K.cow));
  return <group position={[x,.8,0]}><mesh geometry={g} castShadow><meshStandardMaterial vertexColors roughness={.9}/></mesh><Cyl r={1.45} h={.14} p={[0,2.82,0]} c={'#B9C4CE'} seg={28}/></group>;
}
function Heat({gf}:{gf:number}){
  const su=pers(gf,'heat','sun_up',130),tr=pers(gf,'heat','temps_read',120),sy=7+7*smooth(su),sOn=ap(gf,'heat','sun_up',130).on;
  return <group><Plinth n="heat"/>
    {HIDE.map((k,i)=><Barrel key={k} kind={k} x={(i-1)*5.5}/>)}
    {HIDE.map((k,i)=><group key={'t'+k} position={[(i-1)*5.5,.8,-3.4]}><B s={[.7,4.4,.5]} p={[0,2.2,0]} c={K.glass} rad={.2}/><B s={[.34,3.6*tr+.05,.36]} p={[0,.5+(3.6*tr+.05)/2,.05]} c={K.therm} e={.25} rad={.1}/></group>)}
    {sOn&&<group position={[0,sy,-4]}><Ball r={2} p={[0,0,0]} c={K.sun} e={.6} d={2}/><Ball r={3.1} p={[0,0,0]} c={K.sun} e={.3} d={1} o={.22}/></group>}
  </group>;
}

// ---- hair (cutaway): magnified skin, short hair, a fly whose mouthpart is longer than the hair; fly_land, bite ---------------------------------------------
const HAIRS=Array.from({length:150}).map((_,i)=>[-4.8+((i*37)%96)/10,-3.2+((i*53)%64)/10,.45+((i*7)%4)*.06] as V3);
function Hair({gf}:{gf:number}){
  const fl=ap(gf,'hair','fly_land',120),bt=ap(gf,'hair','bite',120),land=smooth(fl.p),prob=bt.on?smooth(bt.p):0;
  const start:V3=[-11,9,-1],rest:V3=[.4,2.7,0],fp:V3=fl.on?lerp3(start,rest,land):[99,99,99];
  return <group><Plinth n="hair"/>
    <B s={[11,.8,8]} p={[0,1.1,0]} c={K.skin} rad={.4}/>
    {HAIRS.map((h,i)=><Cone key={i} r={.07} h={h[2]} p={[h[0],1.5+h[2]/2,h[1]]} c={K.hair} rot={[0,0,((i*13)%7-3)*.05]} seg={5}/>)}
    {fl.on&&<Fly p={fp} yaw={0} pitch={0} s={3.4} gf={gf} flying={fl.p<.95&&!bt.on} prob={prob}/>}
    {prob>0&&<B s={[.5,.12,.5]} p={[2.2,1.52,0]} c={'#D98F8F'} rad={.06}/>}
  </group>;
}

// ---- landing (cutaway): a horse and a zebra, two flies; approach, horse_land (decelerates, lands), zebra_bump (no braking, bounces off), ring (2 m) -------------
const HX=-5.8,ZX=5.8;
function Landing({gf}:{gf:number}){
  const ap1=ap(gf,'landing','approach',140),hl=ap(gf,'landing','horse_land',130),zb=ap(gf,'landing','zebra_bump',120),rg=ap(gf,'landing','ring',100);
  const hitH:V3=[HX+.4,2.9,.95],hitZ:V3=[ZX-.4,2.75,.95],sH:V3=[HX-9,8,5],sZ:V3=[ZX+9,8,5],midH:V3=lerp3(sH,hitH,.7),midZ:V3=lerp3(sZ,hitZ,.7);
  let hp:V3|null=null,zp:V3|null=null,hFly=true,zFly=true,probe=0;const trailH:V3[]=[],trailZ:V3[]=[];
  if(ap1.on){const t=smooth(ap1.p);hp=lerp3(sH,midH,t);zp=lerp3(sZ,midZ,t);}
  if(hl.on){const t=1-Math.pow(1-hl.p,2.4);hp=lerp3(midH,hitH,t);hFly=hl.p<.97;probe=hl.p>.8?smooth((hl.p-.8)/.2):0;}
  if(zb.on){zp=zb.p<.5?lerp3(midZ,hitZ,zb.p/.5):zb.p<.6?hitZ:lerp3(hitZ,[ZX+9,hitZ[1]+6,hitZ[2]+5],smooth((zb.p-.6)/.4));zFly=!(zb.p>=.5&&zb.p<.6);}
  if(hl.on&&hl.age<130)for(let i=1;i<=8;i++){const u=i/8,t=1-Math.pow(1-u,2.4);if(u<=hl.p+.001)trailH.push(lerp3(midH,hitH,t));}
  if(zb.on&&zb.age<120)for(let i=1;i<=8;i++){const u=i/8;if(u*.5<=zb.p)trailZ.push(lerp3(midZ,hitZ,u));}
  const ring=rg.on?smooth(rg.p):0;
  return <group><Plinth n="landing"/>
    <group position={[HX,.8,0]}><Animal kind="horse" look={{pat:'none',base:K.horse}}/></group>
    <group position={[ZX,.8,0]} rotation-y={Math.PI}><Animal kind="zebra" look={{pat:'zebra',base:K.white,seed:4}}/></group>
    {hp&&<Fly p={hp} yaw={flyYaw(sH,hitH)} s={1.7} gf={gf} flying={hFly} prob={probe}/>}{zp&&<Fly p={zp} yaw={flyYaw(sZ,hitZ)} s={1.7} gf={gf} flying={zFly}/>}
    <Trail pts={trailH}/><Trail pts={trailZ}/>
    {ring>0&&<mesh position={[ZX,.85,0]} rotation={[-Math.PI/2,0,0]} scale={ring}><torusGeometry args={[6,.1,8,64]}/><meshStandardMaterial color={'#FFFFFF'} emissive={'#FFFFFF'} emissiveIntensity={.5} transparent opacity={.8}/></mesh>}
  </group>;
}

// ---- coats: three horses dressed in black, white and striped coats; coats_on, flies_test (they land on plain, veer from stripes), head_test ------------------
const COATS:('black'|'white'|'stripe')[]=['black','white','stripe'];
function Coats({gf}:{gf:number}){
  const on=ap(gf,'coats','coats_on',120),mix=on.on?smooth(on.p):0,ft=ap(gf,'coats','flies_test',160),ht=ap(gf,'coats','head_test',110);
  const hx=[-6.4,0,6.4];
  const flies:{p:V3,yaw:number,fly:boolean}[]=[];
  if(ft.on&&ft.age<160){
    [[0,-.5],[0,.7],[1,-.5],[1,.7]].forEach(([h,o],i)=>{const hit:V3=[hx[h]+o*1.3,3.1,.85],s:V3=[hx[h]-7,9,6],t=clip(ft.p*1.6-i*.05),stay=ft.p>.88?smooth((ft.p-.88)/.12):0;
      const p=t<1?lerp3(s,hit,t):lerp3(hit,[hit[0]+4,hit[1]+7,hit[2]+5],stay);flies.push({p,yaw:flyYaw(s,hit),fly:t<1||stay>0});});
    [0,1].forEach(i=>{const h2=hx[2],hit:V3=[h2+.3-i*.7,3.1,.85],s:V3=[h2-7,9,6],t=clip(ft.p*1.5-.1*i),near:V3=[hit[0]-.5,hit[1]+1.6,hit[2]+2.5],aw=t<.6?lerp3(s,near,smooth(t/.6)):lerp3(near,[h2+8,10,7],smooth((t-.6)/.4));flies.push({p:aw,yaw:flyYaw(s,hit),fly:true});});
  }
  if(ht.on&&ht.age<110)[0,1].forEach(i=>{const hh:V3=[hx[2]+2.8+i*.4,4.3+i*.18,.15],s:V3=[hx[2]+11,10,6],t=clip(ht.p*1.5-.12*i),stay=ht.p>.88?smooth((ht.p-.88)/.12):0;
    flies.push({p:t<1?lerp3(s,hh,smooth(t)):lerp3(hh,[hh[0]+4,hh[1]+7,hh[2]+4],stay),yaw:flyYaw(s,hh),fly:t<1||stay>0});});
  return <group><Plinth n="coats"/>
    {hx.map((x,i)=><group key={i} position={[x,.8,0]} scale={.8}><Animal kind="horse" look={{pat:'coat',base:K.horse,coat:COATS[i],mix:mix,seed:5}}/></group>)}
    {flies.map((f,i)=><Fly key={i} p={f.p} yaw={f.yaw} s={1.6} gf={gf} flying={f.fly}/>)}
  </group>;
}

// ---- cows: paint (a brush paints stripes), swarm (about half as many flies on the striped cow), fade (the paint fades) -------------------------------------
function Cows({gf}:{gf:number}){
  const pt=ap(gf,'cows','paint',140),sw=ap(gf,'cows','swarm',170),fd=ap(gf,'cows','fade',130),pa=pt.on?pt.p:0,fade=fd.on?smooth(fd.p):0;
  const brush:V3=[5.8+(-2.3+4.6*pa),4.1,1.4];
  const flies:{p:V3,yaw:number,fly:boolean}[]=[];
  if(sw.on&&sw.age<170){
    const sit=(cx:number,k:number,n:number)=>Array.from({length:n}).map((_,i)=>{const hit:V3=[cx-1.8+i*(3.6/Math.max(1,n-1)),3.1+(i%2)*.7,1.0+(i%3)*.05],s:V3=[cx+(k?14:-14),9+i,5+i],t=clip(sw.p*1.7-i*.07),leave=sw.p>.9?smooth((sw.p-.9)/.1):0;
      return {p:t<1?lerp3(s,hit,smooth(t)):lerp3(hit,[hit[0]+(k?6:-6),hit[1]+7,hit[2]+4],leave),yaw:flyYaw(s,hit),fly:t<1||leave>0};});
    flies.push(...sit(-5.8,0,6),...sit(5.8,1,3));
  }
  return <group><Plinth n="cows"/>
    <group position={[-5.8,.8,0]}><Animal kind="cow" look={{pat:'none',base:K.cow}}/></group>
    <group position={[5.8,.8,0]}><Animal kind="cow" look={{pat:'paint',base:K.cow,seed:3,paint:pa,fade}}/></group>
    {pt.on&&pt.age<140&&<group position={brush}><Cyl r={.1} h={2} p={[0,.9,0]} c={K.brush} seg={8} rot={[0,0,.5]}/><B s={[.9,.5,.3]} p={[-.5,-.1,0]} c={K.paint} rad={.1}/></group>}
    {flies.map((f,i)=><Fly key={i} p={f.p} yaw={f.yaw} s={1.6} gf={gf} flying={f.fly}/>)}
  </group>;
}
const EXHIBIT:Record<string,React.FC<{gf:number}>>={coat:CoatEx,predators:Predators,heat:Heat,hair:Hair,landing:Landing,coats:Coats,cows:Cows};
const ARROW:Record<string,{from:V3,dir:V3}>={savanna:{from:[-12,6,-2],dir:[1,-.3,0]},coat:{from:[-8,8,0],dir:[1,0,0]},predators:{from:[-6,7,0],dir:[1,0,0]},heat:{from:[-7,8,0],dir:[1,0,0]},hair:{from:[-4,6,0],dir:[1,-.6,0]},
  landing:{from:[-4,8,0],dir:[1,0,0]},coats:{from:[-5,8,0],dir:[1,0,0]},cows:{from:[-4,8,0],dir:[1,0,0]}};
type Ev={kind:string,at:number,target:string};
const win=(gf:number,at:number,dur:number)=>{const t=gf-at;return t<0||t>dur?0:Math.min(1,t/6)*Math.min(1,(dur-t)/12);};
const act=(gf:number,kind:string,target:string,dur:number)=>Math.max(0,...script.events.filter((e:Ev)=>e.kind===kind&&e.target===target).map((e:Ev)=>win(gf,e.at,dur)));
const firstSeen=(name:string):number=>{
  const w=wps.find(x=>x.focus===name),e=script.events.find((x:Ev)=>x.target===name),a=AC.find(x=>x.target===name);
  return Math.min(w?w.at+10:1e9,e?e.at-20:1e9,a?a.at-20:1e9);
};
// A stage is on the set only while the story is on it: from the start of its beat(s) until 30 frames after they end (merged when the camera comes right back);
// otherwise earlier stages would pile up in front of the savanna and hide it. Its state (what an action already did) is kept for the next visit.
const INTERVALS:Record<string,[number,number][]>=Object.fromEntries(EXH.map(n=>{
  const iv:[number,number][]=[];
  wps.forEach(w=>{if(w.focus!==n)return;const last=iv[iv.length-1];if(last&&w.at-last[1]<120)last[1]=w.end;else iv.push([w.at,w.end]);});
  return [n,iv];
}));
const ARRIVE:Record<string,number>=Object.fromEntries(EXH.map(n=>[n,firstSeen(n)]));
function arrive(gf:number,at:number,from:V3){
  if(gf<at)return null;
  const s=spring({frame:gf-at,fps:FPS,config:{damping:12,stiffness:90,mass:.9}}),a=clip(s),lift=Math.sin(Math.PI*a)*3;
  return {pos:[from[0]*(1-s),from[1]*(1-s)+lift,from[2]*(1-s)] as V3};
}
function World({gf}:{gf:number}){
  return <>
    <Env/><Savanna gf={gf}/>
    {EXH.map(n=>{
      const iv=INTERVALS[n].find(([s,e])=>gf>=s&&gf<=e+30);if(!iv)return null;
      const a=arrive(gf,iv[0],[0,10,8]);if(!a)return null;
      const out=1-smooth(clip((gf-iv[1])/30)),Part=EXHIBIT[n],base=POS[n],g=GLOW[n],gl=act(gf,'highlight',n,40),ar=act(gf,'arrow',n,50);
      return <group key={n} position={[base[0]+a.pos[0],base[1]+a.pos[1],base[2]+a.pos[2]]} scale={Math.max(.001,out)}>
        <Part gf={gf}/>
        {gl>0&&<mesh position={[0,g[1]/2+.8,0]} scale={[g[0]/2,g[1]/2,g[2]/2]} renderOrder={5}><sphereGeometry args={[1,24,16]}/><meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.5} transparent opacity={.22*gl*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>}
        {ar>0&&<Arrow from={ARROW[n].from} dir={ARROW[n].dir} len={3} s={ar}/>}
      </group>;
    })}
    {(()=>{const g=act(gf,'highlight','savanna',40),q=GLOW.savanna;return g>0?<mesh position={[HERO[0],q[1]/2+.5,HERO[2]]} scale={[q[0]/2,q[1]/2,q[2]/2]} renderOrder={5}><sphereGeometry args={[1,24,16]}/><meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.5} transparent opacity={.2*g*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>:null;})()}
    {(()=>{const g=act(gf,'arrow','savanna',50);return g>0?<group position={[HERO[0],HERO[1],HERO[2]]}><Arrow from={ARROW.savanna.from} dir={ARROW.savanna.dir} len={3.5} s={g}/></group>:null;})()}
  </>;
}

// ---- captions: one independent phrase at a time, white bold with a heavy navy stroke, no box --------------------------------------------------------------
const STROKE=Array.from({length:16},(_,k)=>{const a=k*Math.PI/8;return `${(4*Math.cos(a)).toFixed(1)}px ${(4*Math.sin(a)).toFixed(1)}px 0 ${K.stroke}`;}).join(',');
function Caption({c,f}:{c:Script['captions'][number],f:number}){
  if(f<c.at||f>=c.until)return null;
  const term=c.style==='term',sp=spring({frame:f-c.at,fps:FPS,config:{damping:13,stiffness:170,mass:.7}}),out=ez(EZ.inout,f,c.until-5,5);
  return <div style={{position:'absolute',left:60,right:60,top:term?1660:1500,textAlign:'center',fontFamily:FONT,fontWeight:900,fontSize:term?76:64,lineHeight:1.12,
    color:term?K.term:K.white,textShadow:STROKE,opacity:clip(sp*2)*(1-out),transform:`scale(${.85+.15*sp}) translateY(${(1-sp)*18}px)`}}>{c.text}</div>;
}

function Zebra(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:K.sky}}>
    <ThreeCanvas width={W} height={H} shadows="percentage" flat camera={{fov:24,position:[0,30,60],near:.5,far:700}}>
      <color attach="background" args={[K.sky]}/><fog attach="fog" args={[K.sky,230,520]}/><Rig gf={f}/><Sun gf={f}/><World gf={f}/>
    </ThreeCanvas>
    {script.captions.map(c=><Caption key={c.id} c={c} f={f}/>)}
  </AbsoluteFill>;
}
  return Zebra;
}
