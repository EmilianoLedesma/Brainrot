import React from 'react';
import {registerRoot,Composition,AbsoluteFill,useCurrentFrame,useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
// designed.tsx is written by scripts/asset_probe.py (model-authored scene built only from ./kit). Nothing else is imported by it.
import * as D from './designed';
import {TimeCtx} from './kit';
const {Scene,SHOTS}=D;
const GROUND:string|null=(D as any).GROUND===undefined?'#DCE6EE':(D as any).GROUND;
const SKY:[string,string]=(D as any).SKY??['#9ED0F2','#E6F3FB'];
const FOV=26,ASPECT=1080/1920,N=SHOTS.length;
function gradient(a:string,b:string){const c=document.createElement('canvas');c.width=2;c.height=256;const g=c.getContext('2d')!;const gr=g.createLinearGradient(0,0,0,256);gr.addColorStop(0,a);gr.addColorStop(1,b);g.fillStyle=gr;g.fillRect(0,0,2,256);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;}
type Props={mode:'stills'|'video',seconds:number};
const smooth=(t:number)=>t*t*(3-2*t);
type Shot={focus:string,az:number,el:number,zoom?:number,dy?:number};
// Automatic framing: the camera is computed from the bounding box of the named group, never from hand-typed distances.
function aim(scene:THREE.Scene,shot:Shot,push=0,daz=0){
  const root=shot.focus==='all'?scene.getObjectByName('__world'):scene.getObjectByName(shot.focus);
  if(!root)throw new Error(`SHOTS focus "${shot.focus}" has no <group name="${shot.focus}"> in Scene`);
  const box=new THREE.Box3().setFromObject(root),size=box.getSize(new THREE.Vector3()),c=box.getCenter(new THREE.Vector3());
  if(!isFinite(size.x+size.y+size.z)||size.length()<=0)throw new Error(`group "${shot.focus}" is empty`);
  const t=Math.tan(THREE.MathUtils.degToRad(FOV/2)),halfW=Math.max(size.x,size.z)/2,halfH=size.y/2;
  const d=(Math.max(halfH/t,halfW/(t*ASPECT))*1.12+Math.max(size.x,size.z)*.35)*(1-.14*push)*(shot.zoom??1);const az=shot.az+daz;c.y+=shot.dy??0;
  return {pos:new THREE.Vector3(c.x+d*Math.sin(az)*Math.cos(shot.el),c.y+d*Math.sin(shot.el),c.z+d*Math.cos(az)*Math.cos(shot.el)),target:c};
}
function Rig({mode}:{mode:Props['mode']}){
  const f=useCurrentFrame(),{durationInFrames}=useVideoConfig(),{camera,scene,invalidate}=useThree();
  React.useLayoutEffect(()=>{
    let a=Math.min(f,N-1),b=a,k=0;
    if(mode==='video'){const seg=durationInFrames/N;a=Math.min(N-1,Math.floor(f/seg));b=Math.min(N-1,a+1);const u=(f-a*seg)/seg;k=a===N-1||u<=.7?0:smooth((u-.7)/.3);}
    // video: every shot slowly pushes in and drifts sideways, so the camera is never still
    const lu=mode==='video'?Math.min(1,Math.max(0,(f-a*(durationInFrames/N))/(durationInFrames/N))):0;
    const A=aim(scene,SHOTS[a],lu,(lu-.5)*.3),B=aim(scene,SHOTS[b],0,-.15);
    camera.position.lerpVectors(A.pos,B.pos,k);const tg=new THREE.Vector3().lerpVectors(A.target,B.target,k);
    const cam=camera as THREE.PerspectiveCamera;cam.fov=FOV;cam.near=.5;cam.far=900;cam.updateProjectionMatrix();camera.lookAt(tg);camera.updateMatrixWorld();
    invalidate();
  });
  return null;
}
function Clock({mode,children}:{mode:Props['mode'],children:React.ReactNode}){
  const f=useCurrentFrame(),{durationInFrames}=useVideoConfig();
  const u=mode==='video'?f/durationInFrames:(Math.min(f,N-1)+.5)/N;
  return <TimeCtx.Provider value={u}>{children}</TimeCtx.Provider>;
}
function Root({mode}:Props){
  return <AbsoluteFill style={{background:SKY[1]}}>
    <ThreeCanvas width={1080} height={1920} shadows="percentage" flat camera={{fov:FOV,position:[0,16,58],near:.5,far:900}}>
      <primitive object={React.useMemo(()=>gradient(SKY[0],SKY[1]),[])} attach="background"/><fog attach="fog" args={[SKY[1],160,520]}/>
      <hemisphereLight args={['#F4F8FF','#DCE6EE',.7*Math.PI]}/>
      <directionalLight position={[14,26,20]} intensity={.8*Math.PI} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048} shadow-camera-left={-38} shadow-camera-right={38} shadow-camera-top={38} shadow-camera-bottom={-38} shadow-bias={-.0004}/>
      {GROUND&&<mesh name="__ground" position={[0,-.3,0]} receiveShadow><boxGeometry args={[400,.6,400]}/><meshStandardMaterial color={GROUND} roughness={1}/></mesh>}
      <group name="__world"><Clock mode={mode}><Scene/></Clock></group>
      <Rig mode={mode}/>
    </ThreeCanvas>
  </AbsoluteFill>;
}
registerRoot(()=><Composition id="Probe" component={Root} width={1080} height={1920} fps={30} durationInFrames={N} defaultProps={{mode:'stills',seconds:10} as Props}
  calculateMetadata={({props}:{props:Props})=>({durationInFrames:props.mode==='video'?Math.round(props.seconds*30):N})}/>);
