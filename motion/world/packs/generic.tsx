import React from 'react';
import {AbsoluteFill,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import {EZ,FPS,H,W,clip,ez} from '../kit';
import type {Script,Pack} from '../kit';

// The generic renderer of the continuous-world edit: it draws ANY world spec (brainrot/world/spec.py) that the design stage produced, so no scene has to be built by hand.
// The camera, calm-camera rules, stage lifetimes and captions are the engine shared with the curated packs (the low-poly recipe); pieces are presets or compositions of a few
// primitive shapes; actions are effects (appear, move, scale, colour, glow, spin, ray, wear) resolved as pure functions of the frame. Nothing here runs model-written code.
export function makeGeneric(script:Script):Pack{
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const K={sky:'#D6EAF6',plinthSide:'#B89F72',white:'#F8F6F0',dark:'#2B3140',skin:'#EBC3A6',shirt:'#E59C7C',leaf:'#A3CC8F',leafDark:'#88B87E',trunk:'#8F6F55',wall:'#F4C7B8',roof:'#E59C7C',
  animal:'#D9B58A',mark:'#5E4029',bird:'#B9BEC9',wing:'#8A93A3',beak:'#E9A35E',red:'#E5333B',term:'#FFD23F',hl:'#FFFFFF',stroke:'#1F2A44',spark:'#FFF3B0'};
const GROUND:Record<string,string>={grass:'#CFDCA0',sand:'#EBDDB0',snow:'#F2F7FA',stone:'#BDB4A4',wood:'#C9A27A',water:'#A9D6EC',soil:'#B89F72',floor:'#E8E4DA'};
type V3=[number,number,number];
const WORLD=script.world as any;
if(!WORLD||!WORLD.stations)throw new Error('the script carries no world spec');
const ST:any[]=WORLD.stations;
const HERO_ID:string=WORLD.hero;
const STAGES:string[]=ST.filter(s=>s.id!==HERO_ID).map(s=>s.id);
const TARGETS=[HERO_ID,...STAGES];
const MOVES=['hold','push_in','pull_out','orbit_left','orbit_right','pan_left','pan_right'];
const HERO:V3=[0,0,-14];
const POS:Record<string,V3>={[HERO_ID]:HERO,...Object.fromEntries(STAGES.map((n,i)=>[n,[(i-(STAGES.length-1)/2)*10,.5,12] as V3]))};
const DIST:Record<string,number>={wide:112,medium:88,close:62};
const AZ:Record<string,number>={left:-.62,front:0,right:.62},EL:Record<string,number>={low:.14,mid:.3,high:.6};
const GLOW:Record<string,V3>=Object.fromEntries(ST.map(s=>[s.id,(s.id===HERO_ID?[26,7,10]:[18,8,8]) as V3]));
const wps=script.waypoints,AC=script.actions;

(function validate(){
  if(wps[0].focus!==HERO_ID||wps[0].dist!=='wide'||wps[0].nature!=='context')throw new Error('the first waypoint must be hero/context/wide');
  wps.forEach((w,i)=>{
    if(!TARGETS.includes(w.focus)||!DIST[w.dist])throw new Error(`waypoint ${w.id}: invalid focus or dist`);
    if(!MOVES.includes(w.shot.move)||!AZ.hasOwnProperty(w.shot.angle)||!EL.hasOwnProperty(w.shot.height))throw new Error(`waypoint ${w.id}: incomplete shot`);
    if(i&&w.at-wps[i-1].at<script.flight)throw new Error(`waypoint ${w.id}: closer than one flight (${script.flight} frames) to the previous one`);
    if(i&&w.shot.move!=='hold'&&wps[i-1].shot.move!=='hold')throw new Error(`waypoint ${w.id}: two camera moves in a row`);
    if(!w.show)throw new Error(`waypoint ${w.id}: needs a description of what is on screen`);
  });
  script.events.forEach(e=>{if(!TARGETS.includes(e.target))throw new Error(`event ${e.id}: needs a valid target`);});
})();

const smooth=(t:number)=>t*t*(3-2*t);
const mixc=(a:string,b:string,t:number)=>new THREE.Color(a).lerp(new THREE.Color(b),clip(t)).getStyle();
const aim=(w:{focus:string}):V3=>{const p=POS[w.focus];return w.focus===HERO_ID?[p[0],7,p[2]]:[p[0],p[1]+5.6,p[2]];};
const distOf=(w:{focus:string,dist:string})=>DIST[w.dist]*(w.focus===HERO_ID?.66:1);

// ---- calm camera: a pose per beat; most beats hold; flights blend one pose into the next ---------------------------------------------------------------
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
    <hemisphereLight args={['#F4F8FF','#D8DDA6',.62*Math.PI]}/>
    <primitive object={tgt} position={c.target}/>
    <directionalLight target={tgt} position={[c.target[0]+14,c.target[1]+26,c.target[2]+16]} intensity={.72*Math.PI} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048} shadow-radius={5}
      shadow-camera-left={-34} shadow-camera-right={34} shadow-camera-top={34} shadow-camera-bottom={-34} shadow-camera-near={.5} shadow-camera-far={120} shadow-bias={-.0004}/>
  </>;
}

// ---- primitives -----------------------------------------------------------------------------------------------------------------------------------
const GEO=new Map<string,THREE.BufferGeometry>();
const rbg=(w:number,h:number,d:number,r:number)=>{const k=[w,h,d,r].map(v=>v.toFixed(3)).join();let g=GEO.get(k);
  if(!g){g=new RoundedBoxGeometry(w,h,d,2,Math.max(.001,Math.min(r,w/2-.001,h/2-.001,d/2-.001)));GEO.set(k,g);}return g;};
const B=({s,p,c,r=[0,0,0],e=0,rad=.12,o=1}:{s:V3,p:V3,c:string,r?:V3,e?:number,rad?:number,o?:number})=>
  <mesh geometry={rbg(s[0],s[1],s[2],rad)} position={p} rotation={r} castShadow={o>=1} receiveShadow><meshStandardMaterial color={c} emissive={e?c:'#000000'} emissiveIntensity={e} roughness={.9} transparent={o<1} opacity={o}/></mesh>;
const Cyl=({r,r2,h,p,c,seg=14,rot=[0,0,0],e=0,o=1}:{r:number,r2?:number,h:number,p:V3,c:string,seg?:number,rot?:V3,e?:number,o?:number})=>
  <mesh position={p} rotation={rot} castShadow={o>=1} receiveShadow><cylinderGeometry args={[r,r2??r,h,seg]}/><meshStandardMaterial color={c} roughness={.9} emissive={e?c:'#000000'} emissiveIntensity={e} transparent={o<1} opacity={o}/></mesh>;
const Ball=({r,p,c,s=[1,1,1],d=2,e=0,o=1,rot=[0,0,0],flat=false}:{r:number,p:V3,c:string,s?:V3,d?:number,e?:number,o?:number,rot?:V3,flat?:boolean})=>
  <mesh position={p} scale={s} rotation={rot} castShadow={o>=1}><icosahedronGeometry args={[r,d]}/><meshStandardMaterial color={c} flatShading={flat} roughness={.95} emissive={e?c:'#000000'} emissiveIntensity={e} transparent={o<1} opacity={o} depthWrite={o>=1}/></mesh>;
const Cone=({r,h,p,c,rot=[0,0,0],seg=10}:{r:number,h:number,p:V3,c:string,rot?:V3,seg?:number})=><mesh position={p} rotation={rot} castShadow><coneGeometry args={[r,h,seg]}/><meshStandardMaterial color={c} roughness={.9}/></mesh>;
const Y=new THREE.Vector3(0,1,0);
function Arrow({from,dir,len,s}:{from:V3,dir:V3,len:number,s:number}){
  if(s<=.02)return null;
  const d=new THREE.Vector3(...dir).normalize(),A=new THREE.Vector3(...from),L=len*s,end=A.clone().addScaledVector(d,Math.max(L-.3,.001)),tip=A.clone().addScaledVector(d,L),q=new THREE.Quaternion().setFromUnitVectors(Y,d);
  const mid=A.clone().add(end).multiplyScalar(.5),len2=end.clone().sub(A).length();
  return <group><mesh position={mid.toArray()} quaternion={q}><cylinderGeometry args={[.1,.1,Math.max(len2,.001),8]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.4}/></mesh>
    <mesh position={tip.clone().addScaledVector(d,-.25).toArray()} quaternion={q}><coneGeometry args={[.28,.5,8]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.4}/></mesh></group>;
}
const lerp3=(a:V3,b:V3,t:number):V3=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
const frac=(x:number)=>x-Math.floor(x);


// ---- small parts -------------------------------------------------------------------------------------------------------------------------------------------
const Plinth=({top}:{top:string})=><group><Cyl r={9.4} h={.7} p={[0,.35,0]} c={K.plinthSide} seg={40}/><Cyl r={9} h={.12} p={[0,.74,0]} c={top} seg={40}/></group>;
const Shades=({p,c=K.dark,s=1}:{p:V3,c?:string,s?:number}):React.ReactElement=><group position={p} scale={s}>
  {[-.42,.42].map(x=><mesh key={x} position={[x,0,0]} rotation={[Math.PI/2,0,0]}><cylinderGeometry args={[.34,.34,.1,18]}/><meshStandardMaterial color={c} roughness={.5}/></mesh>)}
  <B s={[.3,.07,.07]} p={[0,.08,0]} c={K.dark} rad={.03}/><B s={[1.7,.06,.06]} p={[0,.1,-.05]} c={K.dark} rad={.03}/></group>;
const Ray=({a,b,r,c,o=.9}:{a:V3,b:V3,r:number,c:string,o?:number}):React.ReactElement|null=>{
  const A=new THREE.Vector3(...a),d=new THREE.Vector3(...b).sub(A),len=d.length();if(len<.05)return null;
  const q=new THREE.Quaternion().setFromUnitVectors(Y,d.clone().normalize());
  return <mesh position={A.clone().addScaledVector(d,.5).toArray()} quaternion={q}><cylinderGeometry args={[r,r,len,8]}/><meshStandardMaterial color={c} emissive={c} emissiveIntensity={.8} transparent opacity={o} depthWrite={false}/></mesh>;
};

// ---- presets ------------------------------------------------------------------------------------------------------------------------------------------------
function PPerson({c,c2,wear,wc}:{c:string,c2:string,wear:number,wc:string}){
  return <group>
    <mesh position={[0,.85,0]} castShadow><capsuleGeometry args={[.38,.75,6,12]}/><meshStandardMaterial color={c} roughness={.9}/></mesh>
    <Ball r={.36} p={[0,1.62,0]} c={c2} d={2}/>
    {wear<.6&&[-.13,.13].map(x=><Ball key={x} r={.045} p={[x,1.64,.33]} c={K.dark} d={1}/>)}
    {wear>0&&<Shades p={[0,1.64+(1-wear)*.6,.36]} c={wc} s={.45}/>}
  </group>;
}
const PTree=({c,c2}:{c:string,c2:string})=><group><Cyl r={.3} h={2} p={[0,1,0]} c={c2} seg={8}/><Ball r={1.5} p={[0,3.1,0]} c={c} s={[1,1.15,1]} d={1}/><Ball r={1.05} p={[.5,4.2,.2]} c={c} d={1}/></group>;
const PHouse=({c,c2}:{c:string,c2:string})=><group><B s={[6,4,5]} p={[0,2,0]} c={c} rad={.35}/><mesh position={[0,5.1,0]} rotation={[0,Math.PI/4,0]} castShadow><coneGeometry args={[4.6,2.4,4]}/><meshStandardMaterial color={c2} roughness={.9}/></mesh></group>;
const PAnimal=({c,c2}:{c:string,c2:string})=><group>
  <Ball r={1} p={[0,1.5,0]} c={c} s={[1.5,.9,.8]} d={2}/><Ball r={.6} p={[1.6,2,0]} c={c} s={[1,.9,.8]} d={2}/>
  {[-.3,.3].map(z=><Cone key={z} r={.2} h={.45} p={[1.55,2.65,z]} c={c}/>)}
  {[[-.9,.45],[-.9,-.45],[.8,.45],[.8,-.45]].map(([x,z],i)=><Cyl key={i} r={.14} r2={.1} h={1.1} p={[x,.55,z]} c={c} seg={8}/>)}
  <Cyl r={.06} h={.9} p={[-1.6,1.7,0]} c={c} rot={[0,0,.9]} seg={6}/>
  {[-.6,0,.6].map(x=><Ball key={x} r={.5} p={[x,1.55,0]} c={c2} s={[.18,.7,.88]} d={1}/>)}
</group>;
const PBird=({c,c2}:{c:string,c2:string})=><group>
  <Ball r={1} p={[0,1.05,0]} c={c} s={[1,.88,.78]} d={2}/><Ball r={.56} p={[.98,1.83,0]} c={c} s={[1,.95,.9]} d={2}/>
  <Cone r={.17} h={.5} p={[1.7,1.75,0]} c={K.beak} rot={[0,0,-Math.PI/2]}/>
  {[-1,1].map(sd=><Ball key={sd} r={1} p={[0,1.2,sd*.75]} c={c2} s={[.9,.12,.5]} d={1}/>)}
  <Ball r={.8} p={[-1.25,1.05,0]} c={c2} s={[1,.1,.3]} d={1}/>
</group>;

// ---- a piece: presets or primitive parts; its state is a pure function of the frame ----------------------------------------------------------------
const FX=new Map<string,{t0:number,dur:number,e:any}[]>();
ST.forEach(st=>{
  const seen=new Set<string>(),list:{t0:number,dur:number,e:any}[]=[];
  AC.filter(a=>a.target===st.id).sort((a,b)=>a.at-b.at).forEach(a=>{
    if(seen.has(a.name))return;seen.add(a.name);
    const def=st.actions.find((x:any)=>x.name===a.name);if(!def)return;
    def.effects.forEach((e:any)=>list.push({t0:a.at+e.start*def.frames,dur:Math.max(1,(e.end-e.start)*def.frames),e}));
  });
  list.sort((x,y)=>x.t0-y.t0);FX.set(st.id,list);
});
type PS={vis:number,off:V3,sc:V3,col:string,colT:number,glow:number,spin:number,wear:number,wearCol:string};
function pstate(gf:number,stId:string,pc:any):PS{
  const s:PS={vis:pc.hidden?0:1,off:[0,0,0],sc:[1,1,1],col:'',colT:0,glow:0,spin:0,wear:0,wearCol:K.dark};let acc:V3=[0,0,0];
  for(const {t0,dur,e} of FX.get(stId)||[]){
    if(e.piece!==pc.id||gf<t0)continue;
    const p=smooth(clip((gf-t0)/dur));
    if(e.type==='appear')s.vis=p;else if(e.type==='disappear')s.vis=1-p;
    else if(e.type==='move'){if(p>=1){acc=[acc[0]+e.vec[0],acc[1]+e.vec[1],acc[2]+e.vec[2]];s.off=acc;}else s.off=[acc[0]+e.vec[0]*p,acc[1]+e.vec[1]*p,acc[2]+e.vec[2]*p];}
    else if(e.type==='scale')s.sc=[1+(e.vec[0]-1)*p,1+(e.vec[1]-1)*p,1+(e.vec[2]-1)*p];
    else if(e.type==='color'){s.col=e.color;s.colT=p;}
    else if(e.type==='glow')s.glow=Math.sin(Math.PI*clip((gf-t0)/dur))*e.amount;
    else if(e.type==='spin')s.spin=e.amount*p*Math.PI*2;
    else if(e.type==='wear'){s.wear=p;s.wearCol=e.color;}
  }
  return s;
}
function PartView({p,s}:{p:any,s:PS}){
  const c=s.col?mixc(p.color,s.col,s.colT):p.color,e=Math.max(p.glow||0,s.glow*.6),o=p.opacity??1,sz=p.size as V3,rot=(p.rot||[0,0,0]) as V3,pos=p.pos as V3;
  switch(p.shape){
    case 'box':return <B s={sz} p={pos} c={c} r={rot} e={e} rad={.12} o={o}/>;
    case 'ball':return <Ball r={1} p={pos} c={c} s={sz} d={2} e={e} o={o} rot={rot}/>;
    case 'cone':return <Cone r={sz[0]} h={sz[1]} p={pos} c={c} rot={rot}/>;
    default:return <Cyl r={sz[0]} h={sz[1]} p={pos} c={c} rot={rot} e={e} o={o} seg={24}/>;
  }
}
function PieceView({stId,pc,gf}:{stId:string,pc:any,gf:number}){
  const s=pstate(gf,stId,pc);if(s.vis<=.01)return null;
  const c1=s.col?mixc(pc.color||'#cccccc',s.col,s.colT):pc.color,c2=pc.color2;
  const k=(pc.scale||1)*s.vis,pos:V3=[pc.pos[0]+s.off[0],pc.pos[1]+s.off[1],pc.pos[2]+s.off[2]];
  return <group position={pos} rotation-y={(pc.rot_y||0)+s.spin} scale={[k*s.sc[0],k*s.sc[1],k*s.sc[2]]}>
    {pc.preset==='person'?<PPerson c={c1||K.shirt} c2={c2||K.skin} wear={s.wear} wc={s.wearCol}/>
      :pc.preset==='tree'?<PTree c={c1||K.leaf} c2={c2||K.trunk}/>
      :pc.preset==='house'?<PHouse c={c1||K.wall} c2={c2||K.roof}/>
      :pc.preset==='animal'?<PAnimal c={c1||K.animal} c2={c2||K.mark}/>
      :pc.preset==='bird'?<PBird c={c1||K.bird} c2={c2||K.wing}/>
      :(pc.parts||[]).map((p:any,i:number)=><PartView key={i} p={p} s={s}/>)}
  </group>;
}
function Rays({stId,gf}:{stId:string,gf:number}){
  return <>{(FX.get(stId)||[]).filter(x=>x.e.type==='ray'&&gf>=x.t0).map((x,i)=>{
    const p=smooth(clip((gf-x.t0)/x.dur)),a=x.e.vec as V3,b=x.e.vec2 as V3;
    return <Ray key={i} a={a} b={lerp3(a,b,p)} r={x.e.amount} c={x.e.color}/>;
  })}</>;
}
function Station({st,gf,hero}:{st:any,gf:number,hero:boolean}){
  return <group>{!hero&&<Plinth top={GROUND[st.ground]||GROUND.floor}/>}
    <group position={[0,hero?0:.8,0]}>{st.pieces.map((pc:any)=><PieceView key={pc.id} stId={st.id} pc={pc} gf={gf}/>)}<Rays stId={st.id} gf={gf}/></group></group>;
}

// ---- the world: ground, sky, hero and the stages that enter with their beats ------------------------------------------------------------------------------
const HERO_GROUND=GROUND[ST.find(s=>s.id===HERO_ID)?.ground]||GROUND.grass;
const Env=React.memo(function Env(){
  return <>
    <mesh position={[0,-.3,-60]} receiveShadow><boxGeometry args={[700,.6,420]}/><meshStandardMaterial color={HERO_GROUND} roughness={1}/></mesh>
    <mesh position={[0,-.28,30]} receiveShadow><boxGeometry args={[700,.6,100]}/><meshStandardMaterial color={mixc(HERO_GROUND,'#FFFFFF',.15)} roughness={1}/></mesh>
    {[[-60,-90,40,9],[20,-100,60,12],[75,-85,38,8]].map(([x,z,w,h],i)=><Ball key={i} r={1} p={[x,0,z]} c={mixc(HERO_GROUND,'#000000',.06)} s={[w,h,14]} d={1}/>)}
    <mesh position={[0,60,-170]}><boxGeometry args={[900,200,.5]}/><meshStandardMaterial color={K.sky}/></mesh>
    {[[-70,42],[20,50],[90,38],[-20,34]].map(([x,y],i)=><Ball key={i} r={4} p={[x,y,-150]} c={K.white} s={[3.4,1,1.2]} d={1}/>)}
  </>;
});
type Ev2={kind:string,at:number,target:string};
const win=(gf:number,at:number,dur:number)=>{const t=gf-at;return t<0||t>dur?0:Math.min(1,t/6)*Math.min(1,(dur-t)/12);};
const act=(gf:number,kind:string,target:string,dur:number)=>Math.max(0,...script.events.filter((e:Ev2)=>e.kind===kind&&e.target===target).map((e:Ev2)=>win(gf,e.at,dur)));
const INTERVALS:Record<string,[number,number][]>=Object.fromEntries(TARGETS.map(n=>{
  const iv:[number,number][]=[];
  wps.forEach(w=>{if(w.focus!==n)return;const last=iv[iv.length-1];if(last&&w.at-last[1]<120)last[1]=w.end;else iv.push([w.at,w.end]);});
  return [n,iv];
}));
function arrive(gf:number,at:number,from:V3){
  if(gf<at)return null;
  const s=spring({frame:gf-at,fps:FPS,config:{damping:12,stiffness:90,mass:.9}}),a=clip(s),lift=Math.sin(Math.PI*a)*3;
  return {pos:[from[0]*(1-s),from[1]*(1-s)+lift,from[2]*(1-s)] as V3};
}
const Glow=({q,y,o,gf}:{q:V3,y:number,o:number,gf:number})=><mesh position={[0,y,0]} scale={[q[0]/2,q[1]/2,q[2]/2]} renderOrder={5}><sphereGeometry args={[1,24,16]}/><meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.5} transparent opacity={.2*o*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>;
function World({gf}:{gf:number}){
  const hero=ST.find(s=>s.id===HERO_ID);
  return <>
    <Env/><group position={HERO}><Station st={hero} gf={gf} hero/></group>
    {STAGES.map(n=>{
      const iv=INTERVALS[n].find(([s,e])=>gf>=s&&gf<=e+30);if(!iv)return null;
      const a=arrive(gf,iv[0],[0,10,8]);if(!a)return null;
      const out=1-smooth(clip((gf-iv[1])/30)),base=POS[n],g=GLOW[n],gl=act(gf,'highlight',n,40),ar=act(gf,'arrow',n,50);
      return <group key={n} position={[base[0]+a.pos[0],base[1]+a.pos[1],base[2]+a.pos[2]]} scale={Math.max(.001,out)}>
        <Station st={ST.find(s=>s.id===n)} gf={gf} hero={false}/>
        {gl>0&&<Glow q={g} y={g[1]/2+.8} o={gl} gf={gf}/>}
        {ar>0&&<Arrow from={[-6,6,0]} dir={[1,0,0]} len={3} s={ar}/>}
      </group>;
    })}
    {(()=>{const g=act(gf,'highlight',HERO_ID,40);return g>0?<group position={[HERO[0],HERO[1]+7,HERO[2]]}><Glow q={GLOW[HERO_ID]} y={0} o={g} gf={gf}/></group>:null;})()}
    {(()=>{const g=act(gf,'arrow',HERO_ID,50);return g>0?<group position={[HERO[0],HERO[1],HERO[2]]}><Arrow from={[-8,6,0]} dir={[1,0,0]} len={4} s={g}/></group>:null;})()}
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

function Generic(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:K.sky}}>
    <ThreeCanvas width={W} height={H} shadows="percentage" flat camera={{fov:24,position:[0,30,60],near:.5,far:900}}>
      <color attach="background" args={[K.sky]}/><fog attach="fog" args={[K.sky,230,620]}/><Rig gf={f}/><Sun gf={f}/><World gf={f}/>
    </ThreeCanvas>
    {script.captions.map(c=><Caption key={c.id} c={c} f={f}/>)}
  </AbsoluteFill>;
}
  return Generic;
}
