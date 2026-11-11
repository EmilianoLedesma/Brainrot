import React from 'react';
import {AbsoluteFill,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import script from './script.json';
import {EZ,FPS,H,W,clip,ez} from '../remotion-explainer/coffee-sci/kit';

// Silent low-poly explainer in ONE continuous world (director v2). Softer look than the first version: rounded boxes, hemisphere light, soft
// shadows, fog, a gentler palette. A small town (street, car, houses, trees) and a sidewalk of road-block exhibits. The camera flies between
// beats and then moves inside each beat (push, pull, orbit, pan, crane) from the angle and height the director chose. Elements move ONLY through
// the director's ACTIONS, each locked to a narration word (script.actions): nothing loops or spins on its own. A beat the director calls a
// "cutaway" opens the block (front half slides away) and shows its interior: rocks, soil grains, fissures, water between them.
// Every animated value is a pure function of useCurrentFrame() (never useFrame).
export const POTHOLE_FRAMES=script.durationFrames;
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const K={sky:'#D3E8F8',grass:'#D9EAC4',grassDark:'#C6DDAB',road:'#7B8798',line:'#F7F8FA',walk:'#E7DFCF',asphalt:'#6B7A8E',asphalt2:'#75849A',base:'#D1CAB9',soil:'#A5806A',wetSoil:'#6F5848',
  frozen:'#C9DAE8',void:'#3A4350',white:'#F7F8FA',gray:'#D3D8E0',mid:'#A4ADB9',dark:'#56606E',water:'#4A97FF',ice:'#D5F4FF',red:'#E5333B',term:'#FFD23F',hl:'#FFFFFF',
  car:'#F5B36E',carTop:'#F8CB9A',roof:'#E59C7C',trunk:'#9A7860',leaf:'#9DD2AE',leafDark:'#84C29A',seal:'#41546A',patch:'#5D6876',cone:'#F28C54',stroke:'#1F2A44'};
type V3=[number,number,number];
const EXH=['layers','cracks','water','traffic','pothole','ice','repair','prevent'];
const TARGETS=['road',...EXH];
const PARTS=['ASFALTO','BASE','SUBRASANTE','GRIETAS','COCODRILO','AGUA','BACHE','HIELO','LENTES','PARCHE','SELLAR','DRENAR'];
const MOVES=['push_in','pull_out','orbit_left','orbit_right','pan_left','pan_right','crane_up','crane_down','drift'];
const ROAD:V3=[0,.05,-8],PX=2,LANE=-6.3;
const POS:Record<string,V3>={road:ROAD,...Object.fromEntries(EXH.map((n,i)=>[n,[(i-3.5)*12,.3,9] as V3]))};
const DIST:Record<string,number>={wide:50,medium:34,close:17};
const GLOW:Record<string,V3>={road:[20,3,9],layers:[9,6,4],cracks:[9,5.4,4],water:[9,9,4],traffic:[9,6.6,4],pothole:[9,5.4,4],ice:[9,5.4,4],repair:[9,6.6,4],prevent:[9,6.4,4]};
const AZ:Record<string,number>={left:-.62,front:0,right:.62},EL:Record<string,number>={low:.2,mid:.38,high:.74};
const wps=script.waypoints,AC=script.actions as {id:string,target:string,name:string,at:number}[];

(function validate(){
  if(wps[0].focus!=='road'||wps[0].dist!=='wide'||wps[0].nature!=='context')throw new Error('the first waypoint must be road/context/wide');
  wps.forEach((w,i)=>{
    if(!TARGETS.includes(w.focus)||!DIST[w.dist])throw new Error(`waypoint ${w.id}: invalid focus or dist`);
    if(!MOVES.includes(w.shot.move)||!AZ.hasOwnProperty(w.shot.angle)||!EL.hasOwnProperty(w.shot.height))throw new Error(`waypoint ${w.id}: incomplete shot`);
    if(i&&w.at-wps[i-1].at<script.flight)throw new Error(`waypoint ${w.id}: closer than one flight (${script.flight} frames) to the previous one`);
    if(i&&JSON.stringify(w.shot)===JSON.stringify(wps[i-1].shot))throw new Error(`waypoint ${w.id}: same camera shot as the previous beat`);
    if(!w.show)throw new Error(`waypoint ${w.id}: needs a description of what is on screen`);
  });
  if(new Set(wps.map(w=>w.shot.move)).size<6)throw new Error('the director must use at least six different camera moves');
  if(wps.filter(w=>w.nature==='cutaway').length<8)throw new Error('the director must use at least eight cutaway beats');
  if(AC.length<18)throw new Error('the director must lock at least 18 actions to the narration');
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
const aim=(w:{focus:string}):V3=>{const p=POS[w.focus];return [p[0],p[1]+(w.focus==='road'?1.2:2.4),p[2]];};
const distOf=(w:{focus:string,dist:string})=>DIST[w.dist]*(w.focus==='road'?1.3:1);

// ---- the camera: each beat has a pose (azimuth, elevation, distance, target) and a MOVE inside the beat; flights blend one pose into the next -----------
type Pose={az:number,el:number,d:number,t:V3};
function pose(w:typeof wps[number],u:number):Pose{
  const e=smooth(clip(u)),T=aim(w);let az=AZ[w.shot.angle],el=EL[w.shot.height],d=distOf(w);
  switch(w.shot.move){
    case 'push_in':d*=1.22-.34*e;break;case 'pull_out':d*=.88+.34*e;break;
    case 'orbit_left':az+=.38-.76*e;break;case 'orbit_right':az+=-.38+.76*e;break;
    case 'pan_left':T[0]+=3.2-6.4*e;break;case 'pan_right':T[0]+=-3.2+6.4*e;break;
    case 'crane_up':el+=-.12+.28*e;break;case 'crane_down':el+=.16-.28*e;break;
    default:az+=.05*Math.sin(e*3);d*=1+.03*Math.sin(e*3);
  }
  return {az,el,d,t:T};
}
function camAt(gf:number){
  let k=0;for(let i=0;i<wps.length;i++)if(wps[i].at<=gf)k=i;
  const cur=wps[k],prev=wps[Math.max(0,k-1)],t=k===0?1:smooth(clip((gf-cur.at)/script.flight));
  const A=pose(prev,1),Bp=pose(cur,(gf-cur.start)/Math.max(1,cur.end-cur.start)),L=(a:number,b:number)=>a+(b-a)*t;
  const az=L(A.az,Bp.az)+.03*Math.sin(gf/170),el=L(A.el,Bp.el),d=Math.exp(L(Math.log(A.d),Math.log(Bp.d))),tg=A.t.map((v,i)=>L(v,Bp.t[i])) as V3;
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
    <hemisphereLight args={['#EEF5FF','#C9DDB0',.55*Math.PI]}/>
    <primitive object={tgt} position={c.target}/>
    <directionalLight target={tgt} position={[c.target[0]+10,c.target[1]+18,c.target[2]+12]} intensity={.72*Math.PI} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048} shadow-radius={5}
      shadow-camera-left={-26} shadow-camera-right={26} shadow-camera-top={26} shadow-camera-bottom={-26} shadow-camera-near={.5} shadow-camera-far={80} shadow-bias={-.0004}/>
  </>;
}

// ---- primitives: rounded boxes (cached geometry), soft materials; icosahedra and cones stay faceted -------------------------------------------------------
const GEO=new Map<string,THREE.BufferGeometry>();
const rbg=(w:number,h:number,d:number,r:number)=>{const k=[w,h,d,r].map(v=>v.toFixed(3)).join();let g=GEO.get(k);
  if(!g){g=new RoundedBoxGeometry(w,h,d,2,Math.max(.001,Math.min(r,w/2-.001,h/2-.001,d/2-.001)));GEO.set(k,g);}return g;};
const B=({s,p,c,r=[0,0,0],e=0,rad=.12}:{s:V3,p:V3,c:string,r?:V3,e?:number,rad?:number})=>
  <mesh geometry={rbg(s[0],s[1],s[2],rad)} position={p} rotation={r} castShadow receiveShadow><meshStandardMaterial color={c} emissive={e?c:'#000000'} emissiveIntensity={e} roughness={.9}/></mesh>;
const Cyl=({r,h,p,c,seg=14,rot=[0,0,0]}:{r:number,h:number,p:V3,c:string,seg?:number,rot?:V3})=>
  <mesh position={p} rotation={rot} castShadow receiveShadow><cylinderGeometry args={[r,r,h,seg]}/><meshStandardMaterial color={c} roughness={.9}/></mesh>;
const Ico=({r,p,c,s=[1,1,1],d=0}:{r:number,p:V3,c:string,s?:V3,d?:number})=><mesh position={p} scale={s} castShadow><icosahedronGeometry args={[r,d]}/><meshStandardMaterial color={c} flatShading roughness={.95}/></mesh>;
const Y=new THREE.Vector3(0,1,0);
function Arrow({from,dir,len,s}:{from:V3,dir:V3,len:number,s:number}){  // thin red arrow: rare, only where the director asked for a direction
  if(s<=.02)return null;
  const d=new THREE.Vector3(...dir).normalize(),A=new THREE.Vector3(...from),L=len*s,end=A.clone().addScaledVector(d,Math.max(L-.3,.001)),tip=A.clone().addScaledVector(d,L),q=new THREE.Quaternion().setFromUnitVectors(Y,d);
  const mid=A.clone().add(end).multiplyScalar(.5),len2=end.clone().sub(A).length();
  return <group>
    <mesh position={mid.toArray()} quaternion={q}><cylinderGeometry args={[.08,.08,Math.max(len2,.001),8]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.4}/></mesh>
    <mesh position={tip.clone().addScaledVector(d,-.2).toArray()} quaternion={q}><coneGeometry args={[.22,.44,8]}/><meshStandardMaterial color={K.red} emissive={K.red} emissiveIntensity={.4}/></mesh>
  </group>;
}
const frac=(x:number)=>x-Math.floor(x);
const Wheel=({x,y,r,c=K.dark}:{x:number,y:number,r:number,c?:string})=>
  <group position={[x,y,0]} rotation-z={-x/r}><Cyl r={r} h={1.4} p={[0,0,0]} c={c} seg={14} rot={[Math.PI/2,0,0]}/><B s={[r*.5,r*.5,1.5]} p={[0,0,0]} c={K.mid}/></group>;

// ---- actions: the director locks a named action to a narration word; an exhibit reads its progress from here and rests when nothing is happening ------
type Ap={on:boolean,p:number,age:number};
function ap(gf:number,t:string,n:string,d:number):Ap{let at=-1e9;for(const a of AC)if(a.target===t&&a.name===n&&a.at<=gf&&a.at>at)at=a.at;const age=gf-at;return {on:at>-1e8,p:clip(age/d),age};}
const pers=(gf:number,t:string,n:string,d:number)=>ap(gf,t,n,d).p;                                   // stays at 1 once finished
const trn=(gf:number,t:string,n:string,d:number)=>{const a=ap(gf,t,n,d);return a.on&&a.age<d?a.p:-1;};   // -1 whenever idle
function sect(gf:number,n:string){let v=0;for(const w of wps)if(w.focus===n&&w.nature==='cutaway')v=Math.max(v,smooth(clip((gf-w.start)/24))*(1-smooth(clip((gf-w.end)/30))));return v;}

// ---- a road block (8 wide, 3 deep, 4.7 tall): soil, base with rocks, asphalt segments that dip under a wheel. In a cutaway the front half slides away and the interior shows ----
type SO={sec:number,wx?:number|null,hole?:boolean,lift?:number,frozen?:number,wet?:number,vd?:number,sepA?:number,sepS?:number,aMix?:number,fiss?:number,pores?:number};
const GRAINS=Array.from({length:22}).map((_,i)=>[-3.6+((i*37)%72)/10,.35+((i*53)%17)/10,.25+((i*7)%3)*.07] as V3);
const ROCKS=Array.from({length:11}).map((_,i)=>[-3.5+i*.7,2.55+((i*29)%7)/9,.4+((i*5)%3)*.06] as V3);
const PORES=Array.from({length:14}).map((_,i)=>[-3.4+((i*41)%68)/10,2.45+((i*19)%11)/10] as [number,number]);
function Slab({sec,wx=null,hole=false,lift=0,frozen=0,wet=0,vd=0,sepA=0,sepS=0,aMix=0,fiss=0,pores=0}:SO){
  const dip=(x:number)=>wx===null?0:-.16*Math.exp(-Math.pow((x-wx)/1.3,2)),soil=mixc(mixc(K.soil,K.wetSoil,wet),K.frozen,frozen),fx=sec*9.5;
  const half=(zc:number,front:boolean)=><group key={front?'f':'b'} position={[front?fx:0,0,0]} visible={!front||sec<.97}>
    <B s={[8,2.2,1.5]} p={[0,1.1+sepS,zc]} c={soil} rad={.1}/><B s={[8,1.6,1.5]} p={[0,3,zc]} c={K.base} rad={.1}/>
    {front&&Array.from({length:9}).map((_,i)=><Ico key={i} r={.26+((i*13)%3)*.06} p={[-3.4+i*.85,2.5+((i*37)%5)*.25,1.5]} c={i%2?K.gray:K.mid} s={[1,.8,.6]}/>)}
    {Array.from({length:8}).map((_,k)=>{const cx=-3.5+k;if(hole&&Math.abs(cx)<1.1)return null;
      return <B key={k} s={[1,.9,1.5]} p={[cx,4.25+lift+sepA+dip(cx),zc]} c={mixc(k%2?K.asphalt:K.asphalt2,'#A6B0BE',aMix*.6)} rad={.1}/>;})}
  </group>;
  return <group>
    {half(-.75,false)}{half(.75,true)}
    {sec>.3&&<group scale={[1,sec,1]} position={[0,0,.02]}>
      {GRAINS.map((g,i)=><B key={'g'+i} s={[g[2],g[2]*.8,.22]} p={[g[0],g[1]+sepS,0]} c={mixc(i%3?soil:K.mid,K.dark,.15)} rad={.06}/>)}
      {ROCKS.map((g,i)=><Ico key={'r'+i} r={g[2]} p={[g[0],g[1],0]} c={i%2?K.gray:K.mid} s={[1,.8,.5]} d={1}/>)}
      {Array.from({length:10}).map((_,i)=><B key={'a'+i} s={[.2,.16,.2]} p={[-3.6+((i*53)%72)/10,4.0+lift+sepA+((i*17)%6)/10,0]} c={K.white} rad={.05}/>)}
      {fiss>0&&[-1.3,.9,2.3].map((x,i)=><B key={'x'+i} s={[.14,.8+2.4*clip(fiss-i*.2),.3]} p={[x,4.7-(.8+2.4*clip(fiss-i*.2))/2,0]} c={K.void} rad={.05}/>)}
      {pores>0&&PORES.slice(0,Math.round(pores*14)).map((q,i)=><B key={'p'+i} s={[.3,.22,.3]} p={[q[0],q[1],.05]} c={K.water} e={.3} rad={.08}/>)}
    </group>}
  </group>;
}
const zs=(sec:number,d=2.6)=>({d:d*(1-.5*sec)-.05*sec,z:-.65*sec*(d/2.6)-.03*sec});   // inner overlays keep to the back half in a cutaway
const wheelAt=(t:number,a=-4.8,b=4.8)=>t<0?null:a+(b-a)*t;

function Layers({gf,sec}:{gf:number,sec:number}){
  const r=trn(gf,'layers','reveal',160),sp=r<0?0:Math.sin(Math.PI*r),wx=wheelAt(trn(gf,'layers','wheel_pass',100)),wear=pers(gf,'layers','wear',90);
  return <group><Slab sec={sec} wx={wx} sepA={1.7*sp} sepS={-.9*sp} aMix={wear}/>{wx!==null&&<Wheel x={wx} y={5.5+1.7*sp} r={.8}/>}</group>;
}
function Cracks({gf,sec}:{gf:number,sec:number}){
  const g=pers(gf,'cracks','crack_grow',170),wx=wheelAt(trn(gf,'cracks','flex',110));
  return <group><Slab sec={sec} wx={wx} fiss={g*1.3}/>{wx!==null&&<Wheel x={wx} y={5.5} r={.8}/>}
    {g>0&&Array.from({length:26}).map((_,i)=>{const len=.9+((i*5)%3)*.25,gi=clip((g*34-i)/8),near=wx===null?0:Math.exp(-Math.pow(((-3.3+(i%9)*.8)-wx)/1.4,2));
      return gi>0?<B key={i} s={[len*gi,.05,.1+.1*near]} p={[-3.3+(i%9)*.8+((i*7)%3)*.12,4.72,(-1.1+Math.floor(i/9)*1.05)-Math.max(0,(-1.1+Math.floor(i/9)*1.05)+.2)*Math.min(1,sec*1.6)]} r={[0,((i*53)%180)*Math.PI/180,0]} c={'#2F3846'} rad={.02}/>:null;})}
  </group>;
}
function Water({gf,sec}:{gf:number,sec:number}){
  const rn=ap(gf,'water','rain',210),cp=rn.on?smooth(clip(rn.age/45))*(1-smooth(clip((rn.age-175)/35))):0,seep=trn(gf,'water','seep',150),pool=pers(gf,'water','pool',170),{d,z}=zs(sec);
  return <group><Slab sec={sec} wet={pool} fiss={1} pores={Math.max(pool,seep<0?0:seep)}/>
    <B s={[.4,1.7,d]} p={[-1,3.9,z]} c={K.void} rad={.05}/>
    {cp>0&&[0,1,2].map(i=><Ico key={i} r={1.1-i*.15} p={[-7+6*cp+i*1.3,8.4+i*.3,0]} c={K.white} s={[1.4,.75,1]} d={1}/>)}
    {rn.on&&rn.age>30&&rn.age<175&&Array.from({length:7}).map((_,i)=>{const u=frac((rn.age-30)/60+i/7);return <B key={i} s={[.3,.3,.3]} p={[-1+(i%3-1)*.7*(u<.5?1:.2),8-u*3.3,((i%2)-.5)*.6]} c={K.water} e={.3} rad={.1}/>;})}
    {seep>=0&&Array.from({length:6}).map((_,i)=>{const p=clip(seep*1.5-i*.12),y=4.7-2.4*p;return p>0&&p<1?<B key={'s'+i} s={[.3,.3,.3]} p={[-1+(i%3-1)*.35*(y<3.9?1.8:0),y,((i%2)-.5)*.4]} c={K.water} e={.4} rad={.1}/>:null;})}
    {pool>0&&<B s={[6,.2+.8*pool,d]} p={[0,2.2+(.2+.8*pool)/2,z]} c={K.water} e={.2} rad={.1}/>}
  </group>;
}
function Squirt({t}:{t:number}){
  return <>{Array.from({length:9}).map((_,j)=>{const dir=j%2?1:-1,s=t*5;
    return <B key={j} s={[.3,.3,.3]} p={[dir*(.6+s*(1.2+j*.15)),4.7+(3*s-4*s*s)*(1+j*.1),(j%3-1)*.6]} c={j%3===0?K.soil:K.water} e={j%3===0?0:.3} rad={.1}/>;})}</>;
}
function Traffic({gf,sec}:{gf:number,sec:number}){
  const pr=trn(gf,'traffic','press',90),pm=trn(gf,'traffic','pump',210),er=pers(gf,'traffic','erode',150),vd=1.2+2.6*er,{d,z}=zs(sec);
  let wx:number|null=null,sq=-1;
  if(pr>=0){wx=-4.2+8.4*pr;sq=pr>.5?(pr-.5)*2:-1;}else if(pm>=0){wx=3.4*Math.sin(2*Math.PI*3*pm);const u=frac(pm*6);sq=u<.6?u/.6:-1;}
  const press=wx===null?0:Math.exp(-Math.pow(wx/1.2,2));
  return <group><Slab sec={sec} wx={wx} vd={vd} wet={.85} pores={.6}/>
    <B s={[vd,.5,d]} p={[0,2.45,z]} c={K.void} rad={.08}/>
    {wx!==null&&<Wheel x={wx} y={5.5-.25*press} r={.8}/>}{sq>=0&&<Squirt t={sq}/>}
  </group>;
}
function PotholeExhibit({gf,sec}:{gf:number,sec:number}){
  const l=pers(gf,'pothole','loosen',70),ej=pers(gf,'pothole','eject',170),w=trn(gf,'pothole','eject',170),{d,z}=zs(sec);
  return <group><Slab sec={sec} hole fiss={1}/><B s={[2,.9,d]} p={[0,4.25,z]} c={K.void} rad={.08}/>
    {Array.from({length:5}).map((_,i)=>{const f=clip((ej*170-i*24)/80),dir=i%2?1:-1,ex=-.8+i*.4,fx=dir*(4.6+.7*i),fz=1.8+(i%3)*.7;
      const px=ex+(fx-ex)*f,py=4.72+.28*l+(4.72-.5)*0+(-4.2*f+Math.sin(Math.PI*f)*3.2),pz=(i%3-1)*.4*(1-f)+fz*f;
      return <B key={i} s={[.7,.45,.7]} p={[px,py<.45?.45:py,pz]} r={[.25*l*(i%2?1:-1)+f*2.4,0,.3*l+f*1.2]} c={K.asphalt}/>;})}
    {w!==null&&<Wheel x={-5+10*w} y={5.5} r={.8}/>}
  </group>;
}
function Ice({gf,sec}:{gf:number,sec:number}){
  const f=pers(gf,'ice','freeze',130),t=pers(gf,'ice','thaw',140),th=.9*f*(1-t),{d,z}=zs(sec);
  return <group>
    <Slab sec={sec} lift={th} frozen={f*(1-.85*t)} fiss={.8}/>
    {th>.01&&<B s={[7.2,th,d*.92]} p={[0,3.8+th/2-.02,z]} c={K.ice} e={.25} rad={.08}/>}
    {t>.3&&<B s={[7,.3*t,d*.92]} p={[0,3.9,z]} c={K.void} rad={.06}/>}
    {t>.5&&<B s={[3,.12,d*.9]} p={[0,2.28,z]} c={K.water} e={.3} rad={.05}/>}
  </group>;
}
function Repair({gf,sec}:{gf:number,sec:number}){
  const tr=pers(gf,'repair','truck_in',100),th=ap(gf,'repair','throw',150),fill=th.on?clip((th.p-.35)/.65):0,roll=trn(gf,'repair','roll',110),tx=-14+7.8*smooth(tr),{d,z}=zs(sec);
  return <group>
    <Slab sec={sec} hole/><B s={[2.4,.9,d]} p={[0,4.25,z]} c={K.void} rad={.08}/>
    {fill>0&&<B s={[2.4,.9*fill+.01,d]} p={[0,3.8+(.9*fill+.01)/2,z]} c={K.patch} rad={.08}/>}
    {tr>0&&<group position={[tx,0,-2.4]}><B s={[3,1.6,1.8]} p={[0,1.3,0]} c={K.white}/><B s={[1.2,1.2,1.8]} p={[-1.5,1.1,0]} c={K.cone}/>
      {[-1,1].map(s=><group key={s} position={[s*1,.55,.9]} rotation-z={-tx/.5}><Cyl r={.5} h={.4} p={[0,0,0]} c={K.dark} rot={[Math.PI/2,0,0]}/></group>)}</group>}
    {tr>.6&&[[-2.4,-1.6],[2.6,-1.6],[2.4,1.9]].map(([x,zz],i)=><mesh key={i} position={[x,5.2*0+.4,zz+1.4]} scale={clip((tr-.6)*3)} castShadow><coneGeometry args={[.35,.8,12]}/><meshStandardMaterial color={K.cone}/></mesh>)}
    {th.on&&th.age<150&&Array.from({length:6}).map((_,i)=>{const u=clip((th.age-50-i*12)/45);return u>0&&u<1?<B key={i} s={[.45,.45,.45]} p={[tx+1.5+(0-tx-1.5)*u,2.8+(5*u-5*u*u)*4,-2+u*2]} c={K.patch} rad={.12}/>:null;})}
    {roll>=0&&<Wheel x={-3+6*roll} y={5.1} r={.7}/>}
  </group>;
}
function Prevent({gf,sec}:{gf:number,sec:number}){
  const s=pers(gf,'prevent','seal',160),dr=trn(gf,'prevent','drain',130),tk=ap(gf,'prevent','thicken',120),{d,z}=zs(sec);
  return <group>
    <Slab sec={sec} fiss={1}/>
    {s>0&&Array.from({length:12}).map((_,i)=>{const px=-3.4+i*.62,done=s>(i/12);
      return <B key={i} s={[.62,.05,.12]} p={[px+.3,4.72,-.4+Math.sin(i*1.3)*.5]} r={[0,Math.sin(i)*.4,0]} c={done?K.seal:'#2F3846'} rad={.02}/>;})}
    {s>0&&s<1&&<B s={[.5,.5,.5]} p={[-3.4+s*7.4,5.1,-.4]} c={K.seal} rad={.14}/>}
    <B s={[1.4,.8,2.6]} p={[4.7,.45,0]} c={K.mid} rad={.12}/>
    {dr>=0&&Array.from({length:5}).map((_,i)=>{const u=clip(dr*1.4-i*.12);return u>0&&u<1?<B key={i} s={[.3,.3,.3]} p={[2.6+u*3.4,3.2-u*2.6,0]} c={K.water} e={.3} rad={.1}/>:null;})}
    {tk.on&&<B s={[8,.7,d*1.15]} p={[0,5.05+(1-smooth(tk.p))*3.2,z*1.15]} c={K.asphalt} rad={.1}/>}
  </group>;
}
const EXHIBIT:Record<string,React.FC<{gf:number,sec:number}>>={layers:Layers,cracks:Cracks,water:Water,traffic:Traffic,pothole:PotholeExhibit,ice:Ice,repair:Repair,prevent:Prevent};
const ARROW:Record<string,{from:V3,dir:V3}>={road:{from:[-3,3,2],dir:[1,0,0]},layers:{from:[-4,7,0],dir:[1,-.5,0]},cracks:{from:[-4,6,1.6],dir:[1,0,0]},water:{from:[1.6,6,0],dir:[0,-1,0]},
  traffic:{from:[.8,6.4,1.8],dir:[1,.4,0]},pothole:{from:[-3,6.5,1],dir:[1,.6,0]},ice:{from:[0,3.6,2],dir:[0,1,0]},repair:{from:[-2.6,7.4,0],dir:[1,-.6,0]},prevent:{from:[-4,7,0],dir:[1,0,0]}};
type Ev={kind:string,at:number,target:string};
const win=(gf:number,at:number,dur:number)=>{const t=gf-at;return t<0||t>dur?0:Math.min(1,t/6)*Math.min(1,(dur-t)/12);};
const act=(gf:number,kind:string,target:string,dur:number)=>Math.max(0,...script.events.filter((e:Ev)=>e.kind===kind&&e.target===target).map((e:Ev)=>win(gf,e.at,dur)));
const firstSeen=(name:string):number=>{
  const w=wps.find(x=>x.focus===name),e=script.events.find((x:Ev)=>x.target===name),a=AC.find(x=>x.target===name);
  return Math.min(w?w.at+10:1e9,e?e.at-20:1e9,a?a.at-20:1e9);
};
const ARRIVE:Record<string,number>=Object.fromEntries(EXH.map(n=>[n,firstSeen(n)]));
function arrive(gf:number,at:number,from:V3){
  if(gf<at)return null;
  const s=spring({frame:gf-at,fps:FPS,config:{damping:9,stiffness:110,mass:.8}}),a=clip(s),lift=Math.sin(Math.PI*a)*3;
  return {pos:[from[0]*(1-s),from[1]*(1-s)+lift,from[2]*(1-s)] as V3,rot:1.1*(1-s)};
}

// ---- the town: a car that appears when the director says so, houses, trees, poles, hills, clouds -------------------------------------------------------
function Car({gf}:{gf:number}){
  const c=trn(gf,'road','car_pass',210);if(c<0)return null;
  const ps=ap(gf,'road','patch_street',50),x=-18+44*c,bump=Math.exp(-Math.pow((x-PX)/4.5,2)),dz=ps.on?0:2.3*bump,slope=ps.on?0:-2.3*2*(x-PX)/20*bump;
  return <group position={[x,.05,LANE-dz]} rotation-y={Math.atan(slope)*.6}>
    <B s={[4,1,2]} p={[0,.95,0]} c={K.car} rad={.3}/><B s={[2.1,.9,1.8]} p={[-.2,1.9,0]} c={K.carTop} rad={.3}/><B s={[1.6,.5,1.9]} p={[-.2,1.95,0]} c={'#6F8FB2'} rad={.15}/>
    <B s={[.2,.35,.5]} p={[2.02,1.05,.6]} c={'#FFF3C4'} e={.4} rad={.08}/><B s={[.2,.35,.5]} p={[2.02,1.05,-.6]} c={'#FFF3C4'} e={.4} rad={.08}/>
    {[[1.2,1],[-1.2,1],[1.2,-1],[-1.2,-1]].map(([wx,wz],i)=><group key={i} position={[wx,.55,wz]} rotation-z={-x/.55}><Cyl r={.55} h={.4} p={[0,0,0]} c={K.dark} rot={[Math.PI/2,0,0]}/><B s={[.3,.3,.45]} p={[0,0,0]} c={K.mid} rad={.1}/></group>)}
  </group>;
}
function House({x,z,c,s=1}:{x:number,z:number,c:string,s?:number}){
  return <group position={[x,0,z]} scale={s}><B s={[6,4,5]} p={[0,2,0]} c={c} rad={.35}/>
    <mesh position={[0,5.1,0]} rotation={[0,Math.PI/4,0]} castShadow><coneGeometry args={[4.6,2.4,4]}/><meshStandardMaterial color={K.roof} roughness={.9}/></mesh>
    <B s={[.9,1.3,.9]} p={[1.6,5.6,-.6]} c={K.mid} rad={.12}/>
    <B s={[1.1,2,.2]} p={[-1.2,1,2.55]} c={K.trunk} rad={.08}/><B s={[1.3,1.1,.2]} p={[1.4,2.4,2.55]} c={'#CFE6F7'} rad={.08}/></group>;
}
const HC=['#F6C3C3','#F8E8BE','#C8E8D6','#DDD5F5','#C8DFF5'];
const Tree=({x,z,s=1}:{x:number,z:number,s?:number})=><group position={[x,0,z]} scale={s}><Cyl r={.3} h={2} p={[0,1,0]} c={K.trunk} seg={8}/>
  <Ico r={1.5} p={[0,3.1,0]} c={K.leafDark} s={[1,1.15,1]} d={1}/><Ico r={1.05} p={[.5,4.2,.2]} c={K.leaf} d={1}/></group>;
const Env=React.memo(function Env(){
  return <>
    <B s={[500,.5,200]} p={[0,-.25,-40]} c={K.grass} rad={.05}/><B s={[500,.5,60]} p={[0,-.24,35]} c={K.grassDark} rad={.05}/>
    <B s={[260,.12,10]} p={[0,.06,-8]} c={K.road} rad={.05}/>
    {Array.from({length:22}).map((_,i)=><B key={i} s={[3,.02,.35]} p={[-62+i*6,.14,-8]} c={K.line} rad={.01}/>)}
    <B s={[260,.25,.5]} p={[0,.12,-13.2]} c={K.walk} rad={.1}/><B s={[260,.25,.5]} p={[0,.12,-2.8]} c={K.walk} rad={.1}/>
    <B s={[260,.3,9]} p={[0,.15,9]} c={K.walk} rad={.12}/><B s={[260,.3,.5]} p={[0,.3,4.4]} c={'#E2DCCD'} rad={.1}/>
    {Array.from({length:13}).map((_,i)=><House key={i} x={-72+i*12} z={-23-(i%2)*3} c={HC[i%5]} s={1+(i%3)*.08}/>)}
    {Array.from({length:10}).map((_,i)=><House key={'b'+i} x={-66+i*14} z={-36} c={HC[(i+2)%5]} s={.9}/>)}
    {Array.from({length:18}).map((_,i)=><Tree key={i} x={-76+i*9+((i*5)%4)} z={-16+((i*7)%3)} s={.9+(i%3)*.15}/>)}
    {Array.from({length:6}).map((_,i)=><group key={'p'+i} position={[-70+i*28,0,-15]}><Cyl r={.18} h={9} p={[0,4.5,0]} c={K.trunk} seg={8}/><B s={[3,.2,.2]} p={[0,8.6,0]} c={K.trunk} rad={.05}/></group>)}
    {[[-40,-58,16,5],[30,-60,22,6],[0,-66,14,4]].map(([x,z,w,h],i)=><Ico key={'h'+i} r={1} p={[x,0,z]} c={K.grassDark} s={[w,h,10]} d={1}/>)}
    <B s={[600,150,.5]} p={[0,60,-90]} c={K.sky} rad={.05}/>
    {[[-50,30],[10,36],[60,28],[-10,24]].map(([x,y],i)=><Ico key={'c'+i} r={3} p={[x,y,-70]} c={K.white} s={[3.2,1,1.2]} d={1}/>)}
  </>;
});
function Street({gf}:{gf:number}){
  const ps=ap(gf,'road','patch_street',60),pt=ps.on?smooth(ps.p):0;
  return <>
    <Env/><Car gf={gf}/>
    {pt<1&&<group>{<B s={[3,.12,2.4]} p={[PX,.14,LANE]} c={K.void} rad={.05}/>}{[0,1,2,3,4].map(i=><B key={i} s={[.5,.12,.4]} p={[PX-1.9+i*.95,.14,LANE+(i%2?1.45:-1.45)]} c={K.asphalt} r={[0,i,0]} rad={.05}/>)}</group>}
    {pt>0&&<><B s={[3.5,.1*pt+.001,2.9]} p={[PX,.11,LANE]} c={'#B8C0CB'} rad={.04}/><B s={[3.2,.16*pt+.001,2.6]} p={[PX,.1+.08*pt,LANE]} c={K.patch} rad={.05}/></>}
  </>;
}
function World({gf}:{gf:number}){
  return <>
    <Street gf={gf}/>
    {EXH.map(n=>{
      const a=arrive(gf,ARRIVE[n],[(POS[n][0]>0?1:-1)*5,9,7]);if(!a)return null;
      const Part=EXHIBIT[n],base=POS[n],g=GLOW[n],gl=act(gf,'highlight',n,40),ar=act(gf,'arrow',n,50);
      return <group key={n} position={[base[0]+a.pos[0],base[1]+a.pos[1],base[2]+a.pos[2]]} rotation-z={a.rot}>
        <Part gf={gf} sec={sect(gf,n)}/>
        {gl>0&&<mesh position={[0,g[1]/2,0]} renderOrder={5}><boxGeometry args={g}/><meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.5} transparent opacity={.32*gl*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>}
        {ar>0&&<Arrow from={ARROW[n].from} dir={ARROW[n].dir} len={2.6} s={ar}/>}
      </group>;
    })}
    {(()=>{const g=act(gf,'highlight','road',40);return g>0?<mesh position={[PX,1.2,LANE]} renderOrder={5}><boxGeometry args={[6,2.4,5]}/><meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.5} transparent opacity={.32*g*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>:null;})()}
    {(()=>{const g=act(gf,'arrow','road',50);return g>0?<group position={[PX,.4,LANE+2.6]}><Arrow from={[-3,2,0]} dir={[1,0,0]} len={3} s={g}/></group>:null;})()}
  </>;
}

// ---- captions: one independent phrase at a time, white bold with a heavy navy stroke, no box ---------------------------------------------------------
const STROKE=Array.from({length:16},(_,k)=>{const a=k*Math.PI/8;return `${(4*Math.cos(a)).toFixed(1)}px ${(4*Math.sin(a)).toFixed(1)}px 0 ${K.stroke}`;}).join(',');
function Caption({c,f}:{c:typeof script.captions[number],f:number}){
  if(f<c.at||f>=c.until)return null;
  const term=c.style==='term',sp=spring({frame:f-c.at,fps:FPS,config:{damping:13,stiffness:170,mass:.7}}),out=ez(EZ.inout,f,c.until-5,5);
  return <div style={{position:'absolute',left:60,right:60,top:term?1660:1500,textAlign:'center',fontFamily:FONT,fontWeight:900,fontSize:term?76:64,lineHeight:1.12,
    color:term?K.term:K.white,textShadow:STROKE,opacity:clip(sp*2)*(1-out),transform:`scale(${.85+.15*sp}) translateY(${(1-sp)*18}px)`}}>{c.text}</div>;
}

export function Pothole(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:K.sky}}>
    <ThreeCanvas width={W} height={H} shadows="percentage" flat camera={{fov:24,position:[0,30,60],near:.5,far:500}}>
      <color attach="background" args={[K.sky]}/><fog attach="fog" args={[K.sky,140,340]}/><Rig gf={f}/><Sun gf={f}/><World gf={f}/>
    </ThreeCanvas>
    {script.captions.map(c=><Caption key={c.id} c={c} f={f}/>)}
  </AbsoluteFill>;
}
