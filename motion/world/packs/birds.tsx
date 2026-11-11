import React from 'react';
import {AbsoluteFill,spring,useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import {EZ,FPS,H,W,clip,ez} from '../kit';
import type {Script,Pack} from '../kit';

// Scene pack birds for the continuous-world edit, ported from experiments/. The script arrives as an argument (a pure function of the props), never as a module import.
export function makeBirds(script:Script):Pack{

// Why birds can perch on power lines: one continuous soft low-poly countryside (director v4, subject-first). The director identifies the SUBJECT of the film
// (script.subject: the small bird or the eagle); the renderer gives it the most detailed model (body, head, eyes with highlights, beak, layered wings and
// tail feathers, legs and toes that close around the wire), its own poses driven by the subject actions locked to narration words (script.subjectActions),
// and the only saturated warm colour in the frame. It appears on every stage. Everything else is calm: the camera mostly holds, stations enter and leave
// with their beats, actions never overlap, nothing moves unless an action says so. Every animated value is a pure function of useCurrentFrame().
const FONT='Inter, "Segoe UI", Arial, sans-serif';
const K={sky:'#D6EAF6',grass:'#CFDCA0',grassDark:'#BFD08E',road:'#8D96A3',line:'#F4F6F8',plinthTop:'#C7DA98',plinthSide:'#B89F72',wood:'#A08066',woodDark:'#8A6B52',wire:'#7F8996',insul:'#E4EEF4',
  violet:'#B48CFF',teal:'#5FD3C8',pulse:'#EAF6FF',spark:'#FFF3B0',leaf:'#A3CC8F',leafDark:'#88B87E',white:'#F8F6F0',hat:'#F6B042',cover:'#8CB6D9',skin:'#EBC3A6',suit:'#5E7BA6',
  red:'#E5333B',term:'#FFD23F',hl:'#FFFFFF',stroke:'#1F2A44',house:'#F4C7B8',roof:'#E59C7C',truck:'#E9EEF2'};
type V3=[number,number,number];
const STAGES=['difference','feet','path','circuit','bridge','spacing','pole','fixes','lineman'];
const TARGETS=['line',...STAGES];
const PARTS=['VOLTAJE','DIFERENCIA','CIRCUITO','RESISTENCIA','ENVERGADURA','AISLANTE','PERCHA','POTENCIAL'];
const MOVES=['hold','push_in','pull_out','orbit_left','orbit_right','pan_left','pan_right'];
const SUBJ=script.subject as string;                       // 'bird' | 'eagle'
const HERO:V3=[0,0,-14];
const POS:Record<string,V3>={line:HERO,...Object.fromEntries(STAGES.map((n,i)=>[n,[(i-4)*10,.5,12] as V3]))};
const DIST:Record<string,number>={wide:112,medium:88,close:62};
const AZ:Record<string,number>={left:-.62,front:0,right:.62},EL:Record<string,number>={low:.14,mid:.3,high:.6};
const GLOW:Record<string,V3>={line:[24,6,10],difference:[18,9,6],feet:[16,6,6],path:[16,6,6],circuit:[16,10,6],bridge:[18,9,6],spacing:[18,10,6],pole:[18,10,6],fixes:[18,10,6],lineman:[18,10,6]};
const wps=script.waypoints,AC=script.actions,SA=script.subjectActions;

(function validate(){
  if(SUBJ!=='bird'&&SUBJ!=='eagle')throw new Error('the director must identify the subject: bird or eagle');
  if(wps[0].focus!=='line'||wps[0].dist!=='wide'||wps[0].nature!=='context')throw new Error('the first waypoint must be line/context/wide');
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
const aim=(w:{focus:string}):V3=>{const p=POS[w.focus];return w.focus==='line'?[p[0],7,p[2]]:[p[0],p[1]+5.6,p[2]];};
const distOf=(w:{focus:string,dist:string})=>DIST[w.dist]*(w.focus==='line'?.66:1);

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

// ---- actions: station actions and the subject's own actions are locked to narration words ----------------------------------------------------------------
type Ap={on:boolean,p:number,age:number};
function ap(gf:number,t:string,n:string,d:number):Ap{let at=-1e9;for(const a of AC)if(a.target===t&&a.name===n&&a.at<=gf&&a.at>at)at=a.at;const age=gf-at;return {on:at>-1e8,p:clip(age/d),age};}
const trn=(gf:number,t:string,n:string,d:number)=>{const a=ap(gf,t,n,d);return a.on&&a.age<d?a.p:-1;};
const SDUR:Record<string,number>={look_around:70,tilt:45,grip:60,fluff:60,hop:60,land:100,take_off:90};
function sap(gf:number,name:string):Ap{let at=-1e9;for(const a of SA)if(a.name===name&&a.at<=gf&&a.at>at)at=a.at;const age=gf-at;return {on:at>-1e8&&age<SDUR[name],p:clip(age/SDUR[name]),age};}

// ---- the wire world --------------------------------------------------------------------------------------------------------------------------------------
const wireY=(x:number,y0:number,sag:number,L:number)=>y0-sag*(1-(x/L)*(x/L));
const top=(x:number,y0:number,sag=.5,L=8.5)=>wireY(x,y0,sag,L)+.14;
function Seg({a,b,r,c,e=0}:{a:V3,b:V3,r:number,c:string,e?:number}){
  const A=new THREE.Vector3(...a),d=new THREE.Vector3(...b).sub(A),len=d.length(),q=new THREE.Quaternion().setFromUnitVectors(Y,d.clone().normalize());
  return <mesh position={A.clone().addScaledVector(d,.5).toArray()} quaternion={q} castShadow><cylinderGeometry args={[r,r,len+.02,8]}/><meshStandardMaterial color={c} roughness={.7} emissive={e?c:'#000000'} emissiveIntensity={e}/></mesh>;
}
function Wire({y0,sag=.5,z=0,c=K.wire,x0=-8.5,x1=8.5,r=.12,e=0,dy=0}:{y0:number,sag?:number,z?:number,c?:string,x0?:number,x1?:number,r?:number,e?:number,dy?:number}){
  const n=16,L=(x1-x0)/2,mid=(x0+x1)/2,pts:V3[]=Array.from({length:n+1}).map((_,i)=>{const x=x0+(x1-x0)*i/n;return [x,wireY(x-mid,y0,sag,L)+dy*Math.sin(Math.PI*i/n),z] as V3;});
  return <group>{pts.slice(1).map((p,i)=><Seg key={i} a={pts[i]} b={p} r={r} c={c} e={e}/>)}</group>;
}
const Pulse=({p,s=1}:{p:V3,s?:number})=><Ball r={.26*s} p={p} c={K.pulse} e={.9} d={1}/>;
function RunPulses({y0,sag=.5,z=0,x0=-8.5,x1=8.5,p,n=6,rep=2}:{y0:number,sag?:number,z?:number,x0?:number,x1?:number,p:number,n?:number,rep?:number}){
  const L=(x1-x0)/2,mid=(x0+x1)/2;
  return <>{Array.from({length:n}).map((_,i)=>{const x=x0+(x1-x0)*frac(p*rep+i/n);return <Pulse key={i} p={[x,wireY(x-mid,y0,sag,L)+.02,z]}/>;})}</>;
}
function Pole({x,z=0,h=12,arm=true,w=7}:{x:number,z?:number,h?:number,arm?:boolean,w?:number}){
  return <group position={[x,0,z]}><Cyl r={.45} r2={.62} h={h} p={[0,h/2,0]} c={K.wood} seg={10}/>
    {arm&&<><B s={[w,.5,.5]} p={[0,h-.6,0]} c={K.woodDark} rad={.15}/><B s={[.4,2.4,.4]} p={[-1.4,h-1.7,0]} c={K.woodDark} rad={.12} r={[0,0,.6]}/><B s={[.4,2.4,.4]} p={[1.4,h-1.7,0]} c={K.woodDark} rad={.12} r={[0,0,-.6]}/></>}</group>;
}
const Insul=({p,cover=0}:{p:V3,cover?:number}):React.ReactElement=><group position={p}><Cyl r={.28} h={.5} p={[0,.25,0]} c={K.insul} seg={10}/><Cyl r={.46} h={.14} p={[0,.6,0]} c={K.insul} seg={12}/><Cyl r={.36} h={.14} p={[0,.9,0]} c={K.insul} seg={12}/>
  {cover>0&&<Ball r={.95} p={[0,.65+(1-cover)*1.6,0]} c={K.cover} s={[1,.9,1]} d={2} o={.86}/>}</group>;
const Plinth=()=><group><Cyl r={9.4} h={.7} p={[0,.35,0]} c={'#B89F72'} seg={40}/><Cyl r={9} h={.12} p={[0,.74,0]} c={K.plinthTop} seg={40}/></group>;
const Rings=({p,c,s}:{p:V3,c:string,s:number})=><mesh position={p} rotation={[-Math.PI/2,0,0]} scale={s}><torusGeometry args={[.7,.07,8,32]}/><meshStandardMaterial color={c} emissive={c} emissiveIntensity={.8}/></mesh>;

// ---- the animals: a detailed bird (and an eagle from the same builder). Smooth primitives with vertex colours ------------------------------------------
const VC=new Map<string,THREE.BufferGeometry>();
type Fn=(x:number,y:number,z:number)=>THREE.Color;
function vgeo(key:string,make:()=>THREE.BufferGeometry,fn:Fn){
  let g=VC.get(key);
  if(!g){g=make();const p=g.attributes.position,c=new Float32Array(p.count*3);
    for(let i=0;i<p.count;i++){const col=fn(p.getX(i),p.getY(i),p.getZ(i));c[i*3]=col.r;c[i*3+1]=col.g;c[i*3+2]=col.b;}
    g.setAttribute('color',new THREE.BufferAttribute(c,3));VC.set(key,g);}
  return g;
}
const ss=(a:number,b:number,x:number)=>{const t=clip((x-a)/(b-a));return t*t*(3-2*t);};
type Pal={breast:string,belly:string,back:string,head:string,face:string,wing:string,wingTip:string,tail:string,beak:string};
const PAL:Record<string,Pal>={
  bird:{breast:'#F28B6E',belly:'#FFE9D6',back:'#7E8798',head:'#6F7A8C',face:'#9AA6B8',wing:'#6A7487',wingTip:'#4F596B',tail:'#59627A',beak:'#E9A35E'},
  eagle:{breast:'#7A5A44',belly:'#8B6B52',back:'#6B4E3A',head:'#F4F0E6',face:'#F4F0E6',wing:'#5A4030',wingTip:'#3C2A20',tail:'#F4F0E6',beak:'#E6C25A'},
  muted:{breast:'#B9BEC9',belly:'#EDEDEF',back:'#8A93A3',head:'#7C8596',face:'#A6AFBF',wing:'#737C8D',wingTip:'#575F70',tail:'#5E6677',beak:'#CDAA82'}};
type BP={yaw?:number,headYaw?:number,headRoll?:number,wingOpen?:number,puff?:number,crouch?:number,grip?:number,alert?:boolean};
type Kind='bird'|'eagle'|'muted';
function Bird({kind,s=1.8,p={}}:{kind:Kind,s?:number,p?:BP}){
  const pal=PAL[kind],big=kind==='eagle',puff=p.puff||0,cr=(p.crouch||0)*.22,wo=p.wingOpen||0,gr=p.grip||0,col=(c:string)=>new THREE.Color(c);
  const body=vgeo('bb'+kind,()=>new THREE.SphereGeometry(1,40,28).scale(1,.88,.78).translate(0,1.05,0),(x,y)=>col(pal.back).lerp(col(pal.breast),ss(-.05,.55,x)*ss(1.5,1.0,y)).lerp(col(pal.belly),ss(.8,.42,y)*.9));
  const head=vgeo('bh'+kind,()=>new THREE.SphereGeometry(.56,28,20).scale(1,.95,.9),(x,y)=>col(pal.head).lerp(col(pal.face),ss(0,.4,x)).lerp(col(pal.belly),big?0:ss(-.05,-.4,y)*.85));
  const wing=vgeo('bw'+kind,()=>new THREE.SphereGeometry(1,22,14).scale(.95,.12,.5).translate(-.1,0,.45),(x)=>col(pal.wing).lerp(col(pal.wingTip),ss(.2,.9,-x)));
  const feather=vgeo('bf'+kind,()=>new THREE.SphereGeometry(1,14,10).scale(.7,.05,.13),()=>col(pal.wingTip));
  const tailG=vgeo('bt'+kind,()=>new THREE.SphereGeometry(1,16,10).scale(.8,.05,.2),()=>col(pal.tail));
  const bs=1+.16*puff;
  return <group scale={s*(big?1.35:1)} rotation-y={p.yaw||0}>
    <group position={[0,-cr,0]}>
      <mesh geometry={body} scale={[bs,bs,bs]} castShadow><meshStandardMaterial vertexColors roughness={.9}/></mesh>
      {[-1,1].map(sd=><group key={sd} position={[.08,1.38,sd*.74*bs]} rotation={[sd*(wo*1.15+.04),sd*wo*.25,-.08]}>
        <mesh geometry={wing} scale={[1,1,sd]} castShadow><meshStandardMaterial vertexColors roughness={.9}/></mesh>
        {[0,1,2,3].map(i=><mesh key={i} geometry={feather} position={[-.75-i*.12,0,sd*(.55+i*.22+wo*.5)]} rotation={[0,sd*(.1+i*.08),0]} castShadow><meshStandardMaterial vertexColors roughness={.9}/></mesh>)}</group>)}
      {[-.28,0,.28].map((a,i)=><mesh key={i} geometry={tailG} position={[-1.25,1.05,0]} rotation={[0,a,.22]} castShadow><meshStandardMaterial vertexColors roughness={.9}/></mesh>)}
      <group position={[.78,1.55,0]} rotation={[p.headRoll||0,p.headYaw||0,0]}>
        <mesh geometry={head} position={[.2,.28,0]} castShadow><meshStandardMaterial vertexColors roughness={.9}/></mesh>
        {[-1,1].map(sd=><group key={sd}><Ball r={.1} p={[.62,.38,sd*.43]} c={'#1B2230'} d={1}/><Ball r={.035} p={[.68,.44,sd*.5]} c={'#FFFFFF'} d={0} e={.5}/></group>)}
        <Cone r={.17} h={big?.7:.5} p={[.95,.2,0]} c={pal.beak} rot={[0,0,-Math.PI/2]} seg={10}/><Cone r={.11} h={big?.5:.34} p={[.88,.1,0]} c={pal.beak} rot={[0,0,-Math.PI/2-.05]} seg={8}/>
      </group>
    </group>
    {[-1,1].map(sd=><group key={'l'+sd} position={[.05,0,sd*.3]}>
      <Cyl r={.05} h={1.1-cr} p={[0,.55-cr/2,0]} c={'#8B6A55'} seg={8}/>
      {[0,1,2].map(i=><Cyl key={i} r={.035} h={.34} p={[.17,.03,(i-1)*.1]} c={'#8B6A55'} seg={6} rot={[0,0,Math.PI/2-gr*.9]}/>)}
      <Cyl r={.035} h={.26} p={[-.12,.03,0]} c={'#8B6A55'} seg={6} rot={[0,0,Math.PI/2+gr*.9]}/></group>)}
  </group>;
}

// ---- the subject: poses from its own actions, locked to narration words; it flies in and out only when the narration says so ------------------------------
function subjectPose(gf:number,iv:[number,number]):{vis:boolean,pos:V3,pose:BP,tilt:number}{
  const land=SA.find(a=>a.name==='land'&&a.at>=iv[0]&&a.at<=iv[1]),take=SA.find(a=>a.name==='take_off'&&a.at>=iv[0]&&a.at<=iv[1]);
  const lk=sap(gf,'look_around'),tl=sap(gf,'tilt'),gp=sap(gf,'grip'),fl=sap(gf,'fluff'),hp=sap(gf,'hop');
  const pose:BP={headYaw:lk.on?.75*Math.sin(lk.p*Math.PI*2):0,headRoll:tl.on?.55*Math.sin(Math.PI*tl.p):0,grip:gp.on?Math.sin(Math.PI*gp.p):0,crouch:gp.on?.6*Math.sin(Math.PI*gp.p):0,puff:fl.on?Math.sin(Math.PI*fl.p):0};
  let pos:V3=[0,hp.on?1.1*Math.sin(Math.PI*hp.p):0,0],vis=true,tilt=0;
  if(land){const a=gf-land.at;if(a<0)vis=false;else if(a<SDUR.land){const t=smooth(a/SDUR.land);pos=lerp3([-13,8,0],[0,0,0],t);pos[1]+=Math.sin(Math.PI*t)*2.2;pose.wingOpen=t<.85?.55+.45*Math.sin(a*.95):.1;tilt=-.25*(1-t);}}
  if(take){const a=gf-take.at;if(a>=SDUR.take_off)vis=false;else if(a>=0){const t=smooth(a/SDUR.take_off);pos=lerp3([0,0,0],[14,9,0],t);pose.wingOpen=.55+.45*Math.sin(a*.95);tilt=.3*t;}}
  return {vis,pos,pose,tilt};
}
function Subject({gf,iv,at,s=1.8,yaw=0}:{gf:number,iv:[number,number],at:V3,s?:number,yaw?:number}){
  const q=subjectPose(gf,iv);if(!q.vis)return null;
  return <group position={[at[0]+q.pos[0],at[1]+q.pos[1],at[2]+q.pos[2]]} rotation-z={q.tilt}><Bird kind={SUBJ as Kind} s={s} p={{...q.pose,yaw}}/></group>;
}
// the big bird of the danger stages: the subject itself when the director chose the eagle (it then also gets the subject's poses)
function BigBird({gf,iv,at,wing=0,yaw=0,extra=0}:{gf:number,iv:[number,number],at:V3,wing?:number,yaw?:number,extra?:number}){
  const q=SUBJ==='eagle'?subjectPose(gf,iv):null;if(q&&!q.vis)return null;
  return <group position={at} rotation-z={extra}><Bird kind="eagle" s={1.8} p={{...(q?q.pose:{}),wingOpen:wing||q?.pose.wingOpen,yaw}}/></group>;
}
const SmallWatcher=({gf,iv,at}:{gf:number,iv:[number,number],at:V3})=>SUBJ==='bird'?<Subject gf={gf} iv={iv} at={at}/>:null;

// ---- stages --------------------------------------------------------------------------------------------------------------------------------------------------
type SP={gf:number,iv:[number,number]};
function Difference({gf,iv}:SP){
  const sl=ap(gf,'difference','show_levels',110),pu=trn(gf,'difference','push',110),ca=sl.on?sl.p:0;
  return <group><Plinth/><Pole x={-8.6}/><Pole x={8.6}/>
    <Wire y0={9} c={mixc(K.wire,K.violet,ca)} e={ca*.35}/><Wire y0={6.2} c={mixc(K.wire,K.teal,ca)} e={ca*.35} z={1.2}/>
    {pu>=0&&Array.from({length:6}).map((_,i)=>{const u=frac(pu*3+i/6);return <Pulse key={i} p={[2+Math.sin(u*Math.PI)*1.4,9-2.8*u,.6*u]}/>;})}
    <Subject gf={gf} iv={iv} at={[-2,top(-2,9),0]}/>
  </group>;
}
function Feet({gf,iv}:SP){
  const eq=ap(gf,'feet','equal',90),np=trn(gf,'feet','no_push',110),e=eq.on?smooth(eq.p):0,y0=4.6;
  return <group><Plinth/><Pole x={-8.6} h={8}/><Pole x={8.6} h={8}/>
    <Wire y0={y0} c={mixc(K.wire,K.violet,e)} e={e*.35} r={.16}/>
    {e>0&&[-.3,.3].map(z=><Rings key={z} p={[.1*3,top(0,y0,.5)+.15,z*3]} c={K.violet} s={e*1.2}/>)}
    {np>=0&&<RunPulses y0={y0} p={np} n={6} rep={1.5}/>}
    <Subject gf={gf} iv={iv} at={[0,top(0,y0),0]} s={3}/>
  </group>;
}
function Path({gf,iv}:SP){
  const cp=ap(gf,'path','compare',110),by=trn(gf,'path','bypass',130),c=cp.on?smooth(cp.p):0,y0=4.6;
  return <group><Plinth/><Pole x={-8.6} h={8}/><Pole x={8.6} h={8}/>
    <Wire y0={y0} r={.16}/>
    {c>0&&<Cyl r={.5} h={4.2} p={[0,y0-.2,0]} c={K.teal} rot={[0,0,Math.PI/2]} o={.28*c} e={.4}/>}
    {c>0&&Array.from({length:9}).map((_,i)=>{const t=i/8,x=-.5+t,y=top(0,y0)+Math.sin(Math.PI*t)*3.4;return <Ball key={i} r={.1} p={[x*1.0+.1,y,0]} c={'#9AA3B2'} d={0} o={.7*c}/>;})}
    {by>=0&&<RunPulses y0={y0} p={by} n={7} rep={1.4}/>}
    <Subject gf={gf} iv={iv} at={[0,top(0,y0),0]} s={2.6}/>
  </group>;
}
const LOOP:V3[]=[[-6,3,0],[-6,10,0],[6,10,0],[6,7.2,0]],LOOP2:V3[]=[[6,5.8,0],[6,3,0],[-6,3,0]];
function Circuit({gf,iv}:SP){
  const op=trn(gf,'circuit','open',110),cl=ap(gf,'circuit','close',110),shut=cl.on?smooth(cl.p):0;
  const pts=[...LOOP,...LOOP2],lens=pts.slice(1).map((p,i)=>Math.hypot(p[0]-pts[i][0],p[1]-pts[i][1])),total=lens.reduce((a,b)=>a+b,0);
  const at=(s:number):V3=>{let t=s;for(let i=0;i<lens.length;i++){if(t<=lens[i]){const u=t/lens[i];return [pts[i][0]+(pts[i+1][0]-pts[i][0])*u,pts[i][1]+(pts[i+1][1]-pts[i][1])*u,0];}t-=lens[i];}return pts[pts.length-1];};
  const before=lens[0]+lens[1]+lens[2];   // up to the gap
  const segs:[V3,V3][]=[[LOOP[0],LOOP[1]],[LOOP[1],LOOP[2]],[LOOP[2],LOOP[3]],[LOOP2[0],LOOP2[1]],[LOOP2[1],LOOP2[2]]];
  return <group><Plinth/>
    {segs.map((s,i)=><Seg key={i} a={s[0]} b={s[1]} r={.16} c={K.wire}/>)}
    <B s={[1.6,1.2,1.2]} p={[0,3,0]} c={'#DCE3EA'} rad={.2}/>
    <Seg a={[6,7.2,0]} b={[6,5.8,0]} r={.16} c={mixc('#B7C0CB',K.teal,shut)} e={shut*.5}/>
    {op>=0&&Array.from({length:6}).map((_,i)=>{const s=frac(op*1.6+i/6)*before;return <Pulse key={i} p={at(s)}/>;})}
    {cl.on&&cl.age<110&&Array.from({length:8}).map((_,i)=>{const s=frac(cl.p*1.8+i/8)*total;return <Pulse key={i} p={at(s)}/>;})}
    <Subject gf={gf} iv={iv} at={[0,top(0,10,0),0]} s={2}/>
  </group>;
}
function Bridge({gf,iv}:SP){
  const ein=ap(gf,'bridge','eagle_in',100),re=ap(gf,'bridge','eagle_reach',90),fl=ap(gf,'bridge','flash',60);
  const reach=re.on?smooth(re.p):0,hit=fl.on?fl.p:0,pos0:V3=[2.2,top(2.2,9),0];
  let at:V3=pos0,wing=reach,extra=0,vis=true;
  if(!ein.on)vis=false;
  else if(ein.age<100){const t=smooth(ein.p);at=lerp3([14,13,0],pos0,t);at[1]+=Math.sin(Math.PI*t)*2;wing=ein.p<.85?.5+.5*Math.sin(ein.age*.95):.1;}
  if(fl.on){if(fl.age>=60&&fl.p>=1)vis=vis&&false;else{const t=smooth(clip((fl.p-.25)/.75));at=lerp3(pos0,[16,14,-3],t);extra=t*3.4;wing=.8;}}
  return <group><Plinth/><Pole x={-8.6}/><Pole x={8.6}/>
    <Wire y0={9}/><Wire y0={6} z={2.3}/>
    {vis&&<BigBird gf={gf} iv={iv} at={at} wing={wing} extra={extra}/>}
    {fl.on&&fl.age<60&&hit<.8&&Array.from({length:8}).map((_,i)=>{const a=i*Math.PI/4,r=2.4*Math.sin(Math.PI*Math.min(1,hit*1.3));return <Ball key={i} r={.34} p={[2.2+Math.cos(a)*r,6+Math.sin(a)*r,2.3]} c={K.spark} e={1} d={1}/>;})}
    {fl.on&&fl.age<60&&hit<.8&&<Ball r={1.1*Math.sin(Math.PI*Math.min(1,hit*1.3))} p={[2.2,6,2.3]} c={K.spark} e={1} d={1}/>}
    <SmallWatcher gf={gf} iv={iv} at={[-5.2,top(-5.2,9),0]}/>
  </group>;
}
function Spacing({gf,iv}:SP){
  const me=ap(gf,'spacing','measure',80),wa=ap(gf,'spacing','wires_apart',100),m=me.on?smooth(me.p):0,apart=wa.on?smooth(wa.p):0,yb=6-3.4*apart;
  return <group><Plinth/><Pole x={-8.6}/><Pole x={8.6}/>
    <Wire y0={9}/><Wire y0={yb} z={2.3}/>
    <BigBird gf={gf} iv={iv} at={[2.2,top(2.2,9),0]} wing={me.on?1:0}/>
    {m>0&&<group position={[-1.2,0,2.3]}><B s={[.25,3.1*m,.25]} p={[0,9.1-1.55*m,0]} c={K.teal} o={.8} e={.4} rad={.08}/><B s={[1.2,.18,.25]} p={[0,9.1,0]} c={K.teal} e={.4} rad={.06}/><B s={[1.2,.18,.25]} p={[0,9.1-3.1*m,0]} c={K.teal} e={.4} rad={.06}/></group>}
    <SmallWatcher gf={gf} iv={iv} at={[-5.2,top(-5.2,9),0]}/>
  </group>;
}
function PoleStage({gf,iv}:SP){
  const lp=ap(gf,'pole','land_pole',100),fk=ap(gf,'pole','flock',150),f=fk.on?fk.p:0,sag=-1.4*smooth(clip(f*1.4))+.5*Math.sin(fk.age*.25)*(f>0&&f<.9?1:0);
  const arm:V3=[-1.3,10.9,0];let at:V3=arm,wing=0;let vis=lp.on;
  if(lp.on&&lp.age<100){const t=smooth(lp.p);at=lerp3([-14,14,0],arm,t);at[1]+=Math.sin(Math.PI*t)*2;wing=lp.p<.85?.5+.5*Math.sin(lp.age*.95):.1;}
  const touch=f>.75?smooth((f-.75)/.25):0;
  return <group><Plinth/><Pole x={0} h={11} w={8}/>
    {[-2.6,0,2.6].map(x=><Insul key={x} p={[x,10.9-.5,0]}/>)}
    {[-2.6,0,2.6].map((x,i)=><group key={x} position={[x,0,0]} rotation-y={Math.PI/2}><Wire y0={11.4} sag={.4} x0={-8} x1={8} dy={i===2?sag:i===1?sag*.5*touch:0} c={mixc(K.wire,K.violet,i===0?.4:0)}/></group>)}
    {vis&&<BigBird gf={gf} iv={iv} at={at} wing={wing}/>}
    {fk.on&&[0,1,2,3,4].map(i=>{const t=smooth(clip(f*2.4-i*.2)),from:V3=[8+i,13,-5+i*2.2],to:V3=[2.6,top(0,11.4,.4,8)+sag*.6,-4+i*2];const q=lerp3(from,to,t);return <group key={i} position={[q[0],q[1],q[2]]} rotation-y={-Math.PI/2}><Bird kind="muted" s={1.1} p={{wingOpen:t<.9?.5+.5*Math.sin(gf*.9+i):.1}}/></group>;})}
    {touch>.4&&touch<1&&<Ball r={1.1} p={[1.3,11.4+sag*.4,0]} c={K.spark} e={1} d={1}/>}
    <SmallWatcher gf={gf} iv={iv} at={[3.2,10.9+.6,0]}/>
  </group>;
}
function Fixes({gf,iv}:SP){
  const cv=ap(gf,'fixes','cover',100),sa=ap(gf,'fixes','space_arm',90),pg=ap(gf,'fixes','perch_guard',90),c=cv.on?smooth(cv.p):0,s=sa.on?smooth(sa.p):0,g=pg.on?smooth(pg.p):0;
  const xs=[-2.6-1.9*s,0,2.6+1.9*s];
  return <group><Plinth/><Pole x={0} h={11} w={8+3.8*s}/>
    {xs.map((x,i)=><Insul key={i} p={[x,10.9-.5,0]} cover={c}/>)}
    {xs.map((x,i)=><group key={i} position={[x,0,0]} rotation-y={Math.PI/2}><Wire y0={11.4} sag={.4} x0={-8} x1={8}/></group>)}
    {g>0&&[-1.3,1.3].map((x,i)=>Array.from({length:5}).map((_,j)=><Cone key={i+'-'+j} r={.12} h={1.1*g} p={[x+(j-2)*.28,10.65+.55*g,0]} c={'#C7CFD8'} seg={6}/>))}
    <SmallWatcher gf={gf} iv={iv} at={[0,10.9+.6,0]}/>
  </group>;
}
function Lineman({gf,iv}:SP){
  const bd=ap(gf,'lineman','bond',120),wk=ap(gf,'lineman','work',100),bp=bd.on?smooth(bd.p):0,wp=wk.on?smooth(wk.p):0,pot=bd.on?bd.p:0,suit=mixc(K.suit,K.violet,pot*.8);
  const S:V3=[-1.1,6.3,2],rest:V3=[-.6,5.9,2.4],tgt:V3=[.9,8.6,.5],H=lerp3(rest,tgt,Math.max(bp,wp)),P:V3=[1.3,top(1.3,9),0];
  return <group><Plinth/><Pole x={-8.6}/><Pole x={8.6}/>
    <Wire y0={9} c={mixc(K.wire,K.violet,pot)} e={pot*.3}/>
    <B s={[3.4,1.8,2.6]} p={[-7.6,1.7,3]} c={K.truck} rad={.3}/><Seg a={[-7.2,2.5,3]} b={[-1.5,3.7,2]} r={.35} c={'#8C96A3'}/>
    <B s={[3,1.4,2.4]} p={[-1.5,4.2,2]} c={K.hat} rad={.25}/>
    <mesh position={[-1.5,5.6,2]} castShadow><capsuleGeometry args={[.62,1.1,6,12]}/><meshStandardMaterial color={suit} roughness={.9}/></mesh>
    <Ball r={.5} p={[-1.5,6.9,2]} c={K.skin} d={2}/><Ball r={.56} p={[-1.5,7.1,2]} c={K.hat} s={[1,.6,1]} d={2}/>
    <Seg a={S} b={H} r={.26} c={suit}/><Seg a={[-1.9,6.3,2]} b={[-2.2,5.2,2.3]} r={.26} c={suit}/>
    {bd.on&&<Seg a={H} b={lerp3(H,P,bp)} r={.08} c={'#CFD6DE'}/>}
    {wp>0&&<Rings p={[P[0],P[1]+.1,0]} c={K.violet} s={wp*1.1}/>}
    <Subject gf={gf} iv={iv} at={[5,top(5,9),0]}/>
  </group>;
}
const STAGE:Record<string,React.FC<SP>>={difference:Difference,feet:Feet,path:Path,circuit:Circuit,bridge:Bridge,spacing:Spacing,pole:PoleStage,fixes:Fixes,lineman:Lineman};

// ---- the hero: a country road with a line of poles; the subject sits on the wire ---------------------------------------------------------------------------
const POLES=[-45,-27,-9,9,27,45];
function Hero({gf,iv}:SP){
  const po=ap(gf,'line','power_on',150),sw=ap(gf,'line','sway',110),pw=po.on&&po.age<150?po.p:-1,dy=sw.on&&sw.age<110?.55*Math.sin(sw.p*Math.PI*3)*Math.sin(Math.PI*sw.p):0;
  return <group>
    {POLES.map(x=><group key={x}><Pole x={x} z={-14} h={12} w={5}/>{[-1.4,1.4].map(o=><Insul key={o} p={[x+o,11.4-.5,-14]}/>)}</group>)}
    {POLES.slice(1).map((x,i)=><group key={x}><Wire y0={9.3} sag={.6} z={-14} x0={POLES[i]} x1={x} dy={x===9?dy:0} r={.15}/><Wire y0={6.6} sag={.6} z={-12.4} x0={POLES[i]} x1={x} r={.15}/></group>)}
    {pw>=0&&Array.from({length:9}).map((_,i)=>{const x=-48+96*frac(pw*2+i/9),span=Math.max(0,Math.min(4,Math.floor((x+45)/18))),a=POLES[span],b=POLES[span+1],mid=(a+b)/2;return <Pulse key={i} s={1.6} p={[x,wireY(x-mid,9.3,.6,9)+.02,-14]}/>;})}
    <Subject gf={gf} iv={iv} at={[0,top(0,9.3,.6,9)+dy,-14]} s={1.6}/>
  </group>;
}
function House({x,z,c}:{x:number,z:number,c:string}){return <group position={[x,0,z]}><B s={[6,4,5]} p={[0,2,0]} c={c} rad={.35}/><mesh position={[0,5.1,0]} rotation={[0,Math.PI/4,0]} castShadow><coneGeometry args={[4.6,2.4,4]}/><meshStandardMaterial color={K.roof} roughness={.9}/></mesh></group>;}
const Tree=({x,z,s=1}:{x:number,z:number,s?:number})=><group position={[x,0,z]} scale={s}><Cyl r={.3} h={2} p={[0,1,0]} c={'#8F6F55'} seg={8}/><Ball r={1.5} p={[0,3.1,0]} c={K.leafDark} s={[1,1.15,1]} d={1}/><Ball r={1.05} p={[.5,4.2,.2]} c={K.leaf} d={1}/></group>;
const Env=React.memo(function Env(){
  return <>
    <mesh position={[0,-.3,-60]} receiveShadow><boxGeometry args={[700,.6,420]}/><meshStandardMaterial color={K.grass} roughness={1}/></mesh>
    <mesh position={[0,-.28,30]} receiveShadow><boxGeometry args={[700,.6,100]}/><meshStandardMaterial color={K.grassDark} roughness={1}/></mesh>
    <B s={[260,.12,9]} p={[0,.06,-6]} c={K.road} rad={.05}/>
    {Array.from({length:22}).map((_,i)=><B key={i} s={[3,.02,.35]} p={[-62+i*6,.14,-6]} c={K.line} rad={.01}/>)}
    {[[-40,-34,'#F6C3C3'],[-8,-40,'#F8E8BE'],[30,-36,'#C8E8D6'],[58,-44,'#DDD5F5']].map(([x,z,c],i)=><House key={i} x={x as number} z={z as number} c={c as string}/>)}
    {Array.from({length:14}).map((_,i)=><Tree key={i} x={-76+i*11+((i*5)%4)} z={-24-((i*7)%3)*3} s={.9+(i%3)*.15}/>)}
    {[[-60,-90,40,9],[20,-100,60,12],[75,-85,38,8]].map(([x,z,w,h],i)=><Ball key={i} r={1} p={[x,0,z]} c={K.grassDark} s={[w,h,14]} d={1}/>)}
    <mesh position={[0,60,-170]}><boxGeometry args={[900,200,.5]}/><meshStandardMaterial color={K.sky}/></mesh>
    {[[-70,42],[20,50],[90,38],[-20,34]].map(([x,y],i)=><Ball key={i} r={4} p={[x,y,-150]} c={K.white} s={[3.4,1,1.2]} d={1}/>)}
  </>;
});
type Ev={kind:string,at:number,target:string};
const win=(gf:number,at:number,dur:number)=>{const t=gf-at;return t<0||t>dur?0:Math.min(1,t/6)*Math.min(1,(dur-t)/12);};
const act=(gf:number,kind:string,target:string,dur:number)=>Math.max(0,...script.events.filter((e:Ev)=>e.kind===kind&&e.target===target).map((e:Ev)=>win(gf,e.at,dur)));
// a stage is on the set only while the story is on it (from its beat to 30 frames after), merged when the camera comes right back; the hero is always there
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
function World({gf}:{gf:number}){
  const heroIv=INTERVALS.line.find(([s,e])=>gf>=s&&gf<=e+60)||INTERVALS.line[INTERVALS.line.length-1]||[0,1];
  return <>
    <Env/><Hero gf={gf} iv={INTERVALS.line[0]?[INTERVALS.line[0][0],INTERVALS.line[0][1]]:[0,1]}/>
    {STAGES.map(n=>{
      const iv=INTERVALS[n].find(([s,e])=>gf>=s&&gf<=e+30);if(!iv)return null;
      const a=arrive(gf,iv[0],[0,10,8]);if(!a)return null;
      const out=1-smooth(clip((gf-iv[1])/30)),Part=STAGE[n],base=POS[n],g=GLOW[n],gl=act(gf,'highlight',n,40),ar=act(gf,'arrow',n,50);
      return <group key={n} position={[base[0]+a.pos[0],base[1]+a.pos[1],base[2]+a.pos[2]]} scale={Math.max(.001,out)}>
        <Part gf={gf} iv={iv}/>
        {gl>0&&<mesh position={[0,g[1]/2+.8,0]} scale={[g[0]/2,g[1]/2,g[2]/2]} renderOrder={5}><sphereGeometry args={[1,24,16]}/><meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.5} transparent opacity={.2*gl*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>}
        {ar>0&&<Arrow from={[-6,9,0]} dir={[1,0,0]} len={3} s={ar}/>}
      </group>;
    })}
    {(()=>{const g=act(gf,'highlight','line',40),q=GLOW.line;return g>0?<mesh position={[HERO[0],q[1]/2+7,HERO[2]]} scale={[q[0]/2,q[1]/2,q[2]/2]} renderOrder={5}><sphereGeometry args={[1,24,16]}/><meshStandardMaterial color={K.hl} emissive={K.hl} emissiveIntensity={.5} transparent opacity={.2*g*(.75+.25*Math.sin(gf*.45))} depthWrite={false}/></mesh>:null;})()}
    {(()=>{const g=act(gf,'arrow','line',50);return g>0?<group position={[HERO[0],HERO[1],HERO[2]]}><Arrow from={[-8,10,0]} dir={[1,0,0]} len={4} s={g}/></group>:null;})()}
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

function Birds(){
  const f=useCurrentFrame();
  return <AbsoluteFill style={{background:K.sky}}>
    <ThreeCanvas width={W} height={H} shadows="percentage" flat camera={{fov:24,position:[0,30,60],near:.5,far:700}}>
      <color attach="background" args={[K.sky]}/><fog attach="fog" args={[K.sky,230,520]}/><Rig gf={f}/><Sun gf={f}/><World gf={f}/>
    </ThreeCanvas>
    {script.captions.map(c=><Caption key={c.id} c={c} f={f}/>)}
  </AbsoluteFill>;
}
  return Birds;
}
