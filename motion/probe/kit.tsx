import React from 'react';
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
// The restricted builder API a model-written asset may use: nothing else is in scope.
export type V3=[number,number,number];
type Base={p?:V3,rot?:V3,c:string,e?:number,o?:number};
const mat=(c:string,e=0,o=1)=><meshStandardMaterial color={c} roughness={.88} emissive={e?c:'#000'} emissiveIntensity={e} transparent={o<1} opacity={o}/>;
export const Ball=({r=1,s=[1,1,1],p=[0,0,0],rot=[0,0,0],c,e,o}:Base&{r?:number,s?:V3})=><mesh position={p} rotation={rot} scale={s} castShadow><sphereGeometry args={[r,28,18]}/>{mat(c,e,o)}</mesh>;
export const RBox=({s,p=[0,0,0],rot=[0,0,0],c,rad=.08,e,o}:Base&{s:V3,rad?:number})=>{
  const g=React.useMemo(()=>new RoundedBoxGeometry(s[0],s[1],s[2],3,Math.max(.002,Math.min(rad,s[0]/2-.002,s[1]/2-.002,s[2]/2-.002))),[s[0],s[1],s[2],rad]);
  return <mesh geometry={g} position={p} rotation={rot} castShadow receiveShadow>{mat(c,e,o)}</mesh>;};
export const Cyl=({r,r2,h,p=[0,0,0],rot=[0,0,0],c,seg=28,e,o}:Base&{r:number,r2?:number,h:number,seg?:number})=><mesh position={p} rotation={rot} castShadow receiveShadow><cylinderGeometry args={[r,r2??r,h,seg]}/>{mat(c,e,o)}</mesh>;
export const Cone=({r,h,p=[0,0,0],rot=[0,0,0],c,seg=12,e,o}:Base&{r:number,h:number,seg?:number})=><mesh position={p} rotation={rot} castShadow><coneGeometry args={[r,h,seg]}/>{mat(c,e,o)}</mesh>;
export const Capsule=({r,h,p=[0,0,0],rot=[0,0,0],c}:Base&{r:number,h:number})=><mesh position={p} rotation={rot} castShadow><capsuleGeometry args={[r,h,6,16]}/>{mat(c)}</mesh>;
export const Torus=({R,r,p=[0,0,0],rot=[0,0,0],c,arc=Math.PI*2,e,o}:Base&{R:number,r:number,arc?:number})=><mesh position={p} rotation={rot} castShadow><torusGeometry args={[R,r,12,40,arc]}/>{mat(c,e,o)}</mesh>;
export const Lathe=({pts,p=[0,0,0],rot=[0,0,0],c,seg=32,phi0=0,phi=Math.PI*2}:Base&{pts:[number,number][],seg?:number,phi0?:number,phi?:number})=>{
  const g=React.useMemo(()=>new THREE.LatheGeometry(pts.map(([r,y])=>new THREE.Vector2(r,y)),seg,phi0,phi),[JSON.stringify(pts),phi0,phi]);
  return <mesh geometry={g} position={p} rotation={rot} castShadow receiveShadow><meshStandardMaterial color={c} roughness={.8} side={THREE.DoubleSide}/></mesh>;};
// closed half cylinder (the back half, z<=0), base at y=0: liquids and fills inside a cutaway
export const HalfCyl=({r,h,p=[0,0,0],c,o=1}:{r:number,h:number,p?:V3,c:string,o?:number})=>{
  const g=React.useMemo(()=>{const sh=new THREE.Shape();sh.absarc(0,0,r,Math.PI,2*Math.PI,false);sh.closePath();
    const e=new THREE.ExtrudeGeometry(sh,{depth:h,bevelEnabled:false,curveSegments:40});e.rotateX(Math.PI/2);e.translate(0,h,0);return e;},[r,h]);
  return <mesh geometry={g} position={p} receiveShadow>{mat(c,0,o)}</mesh>;};
export const Tube=({pts,r,c,closed=false}:{pts:V3[],r:number,c:string,closed?:boolean})=>{
  const g=React.useMemo(()=>new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(v=>new THREE.Vector3(...v)),closed),48,r,8,closed),[JSON.stringify(pts),r]);
  return <mesh geometry={g} castShadow>{mat(c)}</mesh>;};
export const G=({p=[0,0,0],rot=[0,0,0],s=1,children}:{p?:V3,rot?:V3,s?:number,children?:React.ReactNode})=><group position={p} rotation={rot} scale={s}>{children}</group>;

// Time (0..1 across the clip; in stills, the middle of each shot) is provided by the harness. The model never touches hooks or clocks: it only wraps things in <Move>.
export const TimeCtx=React.createContext(0);
const ease=(t:number)=>t*t*(3-2*t);
const clamp=(t:number)=>Math.min(1,Math.max(0,t));
// Deterministic motion: travel from->to between t0..t1 (eased), spin (rad/s about y), bob (vertical amplitude), sway (z tilt amplitude), pop (appears, scaling up, at that time), loop (moves from->to repeatedly, `loop` times per clip: rising bubbles, steam)
export const Move=({from,to,t0=0,t1=1,spin=0,bob=0,sway=0,pop,loop,rot=[0,0,0],s=1,children}:{from?:V3,to?:V3,t0?:number,t1?:number,spin?:number,bob?:number,sway?:number,pop?:number,loop?:number,rot?:V3,s?:number,children?:React.ReactNode})=>{
  const u=React.useContext(TimeCtx);
  const k=loop?((u*loop)%1):ease(clamp((u-t0)/Math.max(.001,t1-t0)));
  const a=from??[0,0,0],b=to??a;
  const p:V3=[a[0]+(b[0]-a[0])*k,a[1]+(b[1]-a[1])*k+bob*Math.sin(u*40),a[2]+(b[2]-a[2])*k];
  const sc=Math.max(.0001,(pop!==undefined?ease(clamp((u-pop)/.06)):1)*s*(loop?Math.sin(Math.PI*k)*.9+.1:1));
  return <group position={p} rotation={[rot[0],rot[1]+spin*u*10,rot[2]+sway*Math.sin(u*30)]} scale={sc}>{children}</group>;
};

// ---- environment kit: every video lives in a diorama (a ground block with a visible cross-section, a surface, a sky), never on an empty plane ----
const rng=(seed:number)=>{let a=seed>>>0;return()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};};
// ground block whose top is at y=0; `layers` are the visible strata of the cut sides, top to bottom (soil, clay, rock...)
export const Slab=({w=26,d=26,top,layers,p=[0,0,0]}:{w?:number,d?:number,top:string,layers:{h:number,c:string}[],p?:V3})=>{
  let y=-.3;
  return <group position={p}>
    <RBox s={[w,.3,d]} p={[0,-.15,0]} c={top} rad={.08}/>
    {layers.map((l,i)=>{const cy=y-l.h/2;y-=l.h;return <RBox key={i} s={[w-.02*(i+1),l.h,d-.02*(i+1)]} p={[0,cy,0]} c={l.c} rad={.04}/>;})}
  </group>;
};
// wooden boards / tiles laid flat on a surface (top at y)
export const Planks=({w,d,n=8,c1,c2,p=[0,0,0]}:{w:number,d:number,n?:number,c1:string,c2:string,p?:V3})=><group position={p}>{Array.from({length:n},(_,i)=><RBox key={i} s={[w,.14+(i%3)*.01,d/n-.04]} p={[0,.07,-d/2+(i+.5)*d/n]} c={i%2?c1:c2} rad={.03}/>)}</group>;
export const Tiles=({w,d,nx=6,nz=6,c1,c2,p=[0,0,0]}:{w:number,d:number,nx?:number,nz?:number,c1:string,c2:string,p?:V3})=><group position={p}>{Array.from({length:nx*nz},(_,i)=>{const x=i%nx,z=Math.floor(i/nx);return <RBox key={i} s={[w/nx-.06,.1,d/nz-.06]} p={[-w/2+(x+.5)*w/nx,.05,-d/2+(z+.5)*d/nz]} c={(x+z)%2?c1:c2} rad={.02}/>;})}</group>;
export const Cloud=({p=[0,0,0],s=1,c='#FFFFFF'}:{p?:V3,s?:number,c?:string})=><group position={p} scale={s}>{[[0,0,0,1.6],[1.8,-.2,.2,1.2],[-1.7,-.25,-.1,1.1],[.5,.7,-.2,1.1]].map(([x,y,z,r],i)=><Ball key={i} r={r} s={[1.2,.8,.9]} p={[x,y,z]} c={c} o={.96}/>)}</group>;
export const Pine=({h=5,p=[0,0,0],c='#2F7D58',c2='#3E9468'}:{h?:number,p?:V3,c?:string,c2?:string})=><group position={p}>
  <Cyl r={h*.05} h={h*.25} p={[0,h*.125,0]} c='#7A5638'/>
  {[0,1,2].map(i=><Cone key={i} r={h*(.3-i*.07)} h={h*.4} p={[0,h*(.3+i*.2),0]} c={i%2?c2:c} seg={9}/>)}</group>;
export const Tree=({h=5,p=[0,0,0],c='#4FAE4A',c2='#66C25B'}:{h?:number,p?:V3,c?:string,c2?:string})=><group position={p}>
  <Cyl r={h*.06} r2={h*.08} h={h*.5} p={[0,h*.25,0]} c='#7A5638'/>
  <Ball r={h*.3} p={[0,h*.62,0]} c={c}/><Ball r={h*.2} p={[h*.17,h*.5,.1*h]} c={c2}/><Ball r={h*.2} p={[-h*.16,h*.54,-.08*h]} c={c2}/></group>;
export const Rock=({r=1,p=[0,0,0],c='#9AA3AD',seed=1}:{r?:number,p?:V3,c?:string,seed?:number})=>{const q=rng(seed);return <group position={p}><Ball r={r} s={[1+q()*.3,.65,.9+q()*.3]} p={[0,r*.4,0]} rot={[0,q()*6,0]} c={c}/><Ball r={r*.5} s={[1,.7,1]} p={[r*.7,r*.2,r*.2]} c={c}/></group>;};
export const Mound=({r=2,p=[0,0,0],c='#F4F8FB'}:{r?:number,p?:V3,c?:string})=><Ball r={r} s={[1.3,.42,1.1]} p={p} c={c}/>;
// deterministic scattering inside box [x0,z0,x1,z1], skipping circles [x,z,radius]; render(i, rand) returns one item
export const Scatter=({n,seed=1,box,avoid=[],render}:{n:number,seed?:number,box:[number,number,number,number],avoid?:[number,number,number][],render:(i:number,r:()=>number)=>React.ReactNode})=>{
  const out:React.ReactNode[]=[];const r=rng(seed);let tries=0;
  while(out.length<n&&tries<n*40){tries++;const x=box[0]+r()*(box[2]-box[0]),z=box[1]+r()*(box[3]-box[1]);if(avoid.some(([ax,az,ar])=>Math.hypot(x-ax,z-az)<ar))continue;
    const rr=rng(Math.floor(r()*1e9));out.push(<group key={out.length} position={[x,0,z]} rotation={[0,r()*6.283,0]}>{render(out.length,rr)}</group>);}
  return <>{out}</>;
};
// keyframed action: keys [{t,p?,rot?,s?}] with t in 0..1 over the clip (match the narration); eased between keys, holds before the first and after the last
export const Act=({keys,children}:{keys:{t:number,p?:V3,rot?:V3,s?:number}[],children?:React.ReactNode})=>{
  const u=React.useContext(TimeCtx);
  const ks=[...keys].sort((x,y)=>x.t-y.t);let i=0;while(i<ks.length-1&&u>ks[i+1].t)i++;
  const A=ks[i],B=ks[Math.min(i+1,ks.length-1)];const k=A===B||u<=A.t?0:ease(clamp((u-A.t)/Math.max(.001,B.t-A.t)));
  const mix=(a:V3|undefined,b:V3|undefined,d:V3):V3=>{const x=a??d,y=b??a??d;return [x[0]+(y[0]-x[0])*k,x[1]+(y[1]-x[1])*k,x[2]+(y[2]-x[2])*k];};
  const sa=A.s??1,sb=B.s??A.s??1;
  return <group position={mix(A.p,B.p,[0,0,0])} rotation={mix(A.rot,B.rot,[0,0,0])} scale={Math.max(.0001,sa+(sb-sa)*k)}>{children}</group>;
};

// Time-based change for gradual transformations: `const k=ramp(useTime(),.4,.5)` then `c={mix('#E8704F','#8C8C7A',k)}` on every part that changes. This is the only hook an asset may use.
export const useTime=()=>React.useContext(TimeCtx);
export const ramp=(u:number,a:number,b:number)=>ease(clamp((u-a)/Math.max(.001,b-a)));
export const mix=(c1:string,c2:string,k:number)=>'#'+new THREE.Color(c1).lerp(new THREE.Color(c2),clamp(k)).getHexString();
