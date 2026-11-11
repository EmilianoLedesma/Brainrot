import {Easing} from 'remotion';

// Shared helpers and the script contract between brainrot/world/script.py and the pack renderers.
export const FPS=30,W=1080,H=1920;
export const clip=(v:number)=>Math.max(0,Math.min(1,v));
export const seg=(t:number,a:number,d:number)=>clip((t-a)/d);
export const EZ={out:Easing.bezier(.16,1,.3,1),inout:Easing.bezier(.65,0,.35,1)};
export const ez=(f:(x:number)=>number,t:number,a:number,d:number)=>f(seg(t,a,d));

export type Wp={id:string,at:number,start:number,end:number,focus:string,dist:string,nature:string,shot:{dist:string,angle:string,height:string,move:string},show:string};
export type Cap={id:string,at:number,until:number,style:string,text:string};
export type Ev={id:string,kind:string,at:number,term:string,target:string};
export type Act={id:string,target:string,name:string,at:number};
export type SAct={id:string,name:string,at:number};
export type Script={title:string,fps:number,durationFrames:number,flight:number,subject:string|null,waypoints:Wp[],actions:Act[],subjectActions:SAct[],events:Ev[],captions:Cap[]};
export type Pack=()=>React.ReactElement;
