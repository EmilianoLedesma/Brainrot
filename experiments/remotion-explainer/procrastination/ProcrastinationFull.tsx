import React from 'react';
import {AbsoluteFill,Audio,interpolate,spring,staticFile,useCurrentFrame} from 'remotion';
import {evolvePath,interpolatePath} from '@remotion/paths';
import {noise2D} from '@remotion/noise';
import {CameraMotionBlur} from '@remotion/motion-blur';
import tl from './timeline.json';
import {Dial,EZ,FPS,Glyphs,H,Halftone,W,camAt,ez,mono,pts,seg,toD,Tube} from '../coffee-sci/kit';

// Narrated full-length version of the recipe video for the saved story "Your Brain Is Cooked, Not Lazy".
// Every scene is timed from the measured word times in timeline.json (prepare.py). Same look as the silent sample:
// pastel scene colours, one hero (the task-mountain), skewed colour panels between scenes, no frame, no film filters.
export const PROCRASTINATION_FULL_FRAMES=Math.round(tl.duration*FPS);
const P={ink:'#2a2433',dim:'#7d7788',coral:'#ff6b5e',coralHi:'#ffc6bd',green:'#1f9d63',white:'#ffffff',mintG:'#6fd39a',
  cream:'#fdf7ee',butter:'#fff3c4',peach:'#ffe3d6',sky:'#d9ecff',mint:'#dcf5e6',lilac:'#e6defc',dot:'#f0b999',hi:'#8a8296',zoneA:'#ffd9cc',zoneB:'#cdeedd'};
const BG=[P.cream,P.butter,P.peach,P.sky,P.mint,P.lilac,P.cream,P.butter,P.peach,P.mint,P.lilac];
const S=tl.scenes;
const an=(id:string,name:string)=>(S.find(s=>s.id===id) as {a:Record<string,number>}).a[name];
const sceneStart=(id:string)=>S.find(s=>s.id===id)!.start;
const CX=540,CY=960,N=240;
const poly=(v:[number,number][],n:number)=>{const c=[...v,v[0]];
  return toD(pts(n,t=>{const f=t*(c.length-1),i=Math.min(c.length-2,Math.floor(f)),k=f-i;return [CX+c[i][0]+(c[i+1][0]-c[i][0])*k,CY+c[i][1]+(c[i+1][1]-c[i][1])*k];}));};
const MOUNT=poly([[-300,220],[-120,-80],[-60,-10],[0,-260],[130,-60],[190,-120],[300,220]],N);
const PILE=poly([[-300,220],[-220,140],[-150,95],[-70,110],[10,55],[120,95],[300,220]],N);
const POSE:Record<string,[number,number,number]>={title:[540,1000,1],email:[900,360,.3],rescue:[900,360,.3],alarm:[900,360,.28],bias:[900,360,.28],wiring:[900,360,.28],
  dread:[230,560,.3],step:[900,1270,.25],forgive:[930,1380,.25],dodging:[540,420,.4],close:[540,1030,.85]};
const K1=(t:number,a:number[],b:number[])=>interpolate(t,a,b,{easing:EZ.inout,extrapolateLeft:'clamp',extrapolateRight:'clamp'});
const card=(frame:number,at:number)=>spring({frame:frame-at*FPS,fps:FPS,config:{damping:14,stiffness:90}});

// dread chart: schematic, illustrative curve with its peak at "start"
const CHX0=130,CHX1=950,CHY=1230,CHK=4.2,START=540,CHT=800;
const dread=(u:number)=>u<.5?18+77*Math.pow(u/.5,1.6):95-60*(1-Math.pow(1-(u-.5)/.5,2));
const curveAt=(a:number,b:number)=>toD(pts(60,t=>{const u=a+(b-a)*t;return [CHX0+(CHX1-CHX0)*u,CHY-dread(u)*CHK];}));
const CURVE_A=curveAt(0,.5),CURVE_B=curveAt(.5,1),AXES=`M${CHX0} ${CHY}H${CHX1}M${CHX0} ${CHY}V${CHT}`;
const cursorU=(T:number)=>{const a0=an('dread','dread'),b=an('dread','begin'),q=an('dread','quiets');
  return T<a0?0:T<b-.3?.5*EZ.inout(seg(T,a0,b-.3-a0)):T<b?.5:.5+.5*EZ.inout(seg(T,b,q+1.4-b));};

// loop diagram
const LC=[540,1030],LR=250;
const lp=(deg:number):[number,number]=>[LC[0]+LR*Math.cos(deg*Math.PI/180),LC[1]+LR*Math.sin(deg*Math.PI/180)];
const arc=(a:number,b:number)=>toD(pts(40,t=>lp(a+(b-a)*t)));
const LNODES=[{k:'guilt',t:'guilt',deg:-90},{k:'mood',t:'bad mood',deg:30},{k:'escape',t:'escape',deg:150}];
const ARCS=[arc(-62,2),arc(58,122),arc(178,242)];

const Txt=({T,a,b,children}:{T:number,a:number,b:number,children:React.ReactNode})=>{const v=(T>=a-.05&&T<b+.3)?1-seg(T,b,.25):0;return v>0?<div style={{position:'absolute',inset:0,opacity:v}}>{children}</div>:null;};
const Chip=({x,y,w,label,color,fg=P.ink,a,T,stroke=false}:{x:number,y:number,w:number,label:string,color:string,fg?:string,a:number,T:number,stroke?:boolean})=>{
  const k=ez(EZ.out,T,a,.5);return <g transform={`translate(${x} ${y}) scale(${k})`} opacity={k}>
    <rect x={-w/2} y={-31} width={w} height={62} rx={31} fill={stroke?'none':color} stroke={stroke?P.ink:'none'} strokeWidth={3}/>
    <text y={8} textAnchor="middle" fontSize={22} fontWeight={800} fill={fg} style={{...mono,letterSpacing:2}}>{label}</text></g>;};

export const ProcrastinationFull=()=>{
  const frame=useCurrentFrame(),T=frame/FPS;
  const si=Math.max(0,S.findIndex((s,i)=>T>=s.start&&(i===S.length-1||T<S[i+1].start)));
  const id=S[si].id,BOUNDS=S.slice(1).map(s=>s.start);
  const cam=S.flatMap(s=>[{at:s.start,zoom:1,cy:960},{at:(s.start+s.end)/2,zoom:1.045,cy:970}]);
  const {zoom,cy}=camAt(T,cam),roll=noise2D('r',T*.3,0)*.5;
  // hero
  const prev=POSE[S[Math.max(0,si-1)].id],cur=POSE[id],pp=si===0?1:ez(EZ.inout,T,S[si].start-.15,.9);
  const gx=prev[0]+(cur[0]-prev[0])*pp,gy=prev[1]+(cur[1]-prev[1])*pp,gs=prev[2]+(cur[2]-prev[2])*pp;
  const morph=ez(EZ.inout,T,an('dread','begin'),1.4);
  const heroD=interpolatePath(morph,MOUNT,PILE),heroDash=evolvePath(ez(EZ.inout,T,.2,1.0),MOUNT);
  const badge=ez(EZ.out,T,an('rescue','rescue'),.4)*(1-seg(T,an('dread','begin'),.9));
  const check=evolvePath(ez(EZ.inout,T,an('close','laundry'),.6),'M-55 10L-15 50L60 -40');
  // dread chart cursor
  const u=cursorU(T),cx=CHX0+(CHX1-CHX0)*u,cyy=CHY-dread(u)*CHK,dv=dread(u);
  const curveA=evolvePath(Math.max(.0001,Math.min(1,u/.5)),CURVE_A),curveB=evolvePath(Math.max(.0001,(u-.5)/.5),CURVE_B);
  // caption: four spoken words at a time, active word in coral
  const wi=Math.max(0,tl.words.findIndex(w=>T<w[2]));
  const chunk=Math.floor(wi/4)*4,cap=tl.words.slice(chunk,chunk+4);

  const content=<AbsoluteFill style={{background:BG[si]}}>
    {BOUNDS.map((b,i)=>{const p=(T-(b-.25))/.5;if(p<0||p>1)return null;const w=W*1.5;
      return <div key={i} style={{position:'absolute',top:-50,height:H+100,width:w,left:W-ez(EZ.inout,p,0,1)*(W+w),background:BG[i+1],transform:'skewX(-12deg)'}}/>;})}
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{position:'absolute',inset:0}}>
      <g transform={`translate(540 960) rotate(${roll}) scale(${zoom}) translate(-540 ${-cy})`}>

        {/* email: one tiny task, an hour passes, the brain calls it a win */}
        {id==='email'&&(()=>{const a=an('email','email'),h=an('email','hour'),w=an('email','win'),k=ez(EZ.out,T,a-.2,.6),hand=ez(EZ.inout,T,h,1.1)*360,st=spring({frame:frame-w*FPS,fps:FPS,config:{damping:9,stiffness:140}});
          const mark=evolvePath(ez(EZ.inout,T,w+.15,.4),'M0 22L16 38L44 0');
          return <g>
            <g transform={`translate(0 ${(1-k)*500})`} opacity={k}>
              <rect x={110} y={560} width={860} height={420} rx={32} fill={P.white} stroke={P.ink} strokeOpacity={.15} strokeWidth={3}/>
              <circle cx={190} cy={640} r={34} fill={P.coralHi}/><text x={250} y={632} fontSize={20} fill={P.dim} style={mono}>inbox · 1 new</text>
              <text x={250} y={680} fontSize={40} fontWeight={800} fill={P.ink}>Re: one tiny task</text>
              <path d="M150 730H930" stroke={P.ink} strokeOpacity={.15} strokeWidth={3}/>
              <rect x={150} y={770} width={780} height={150} rx={18} fill={P.cream}/>
              <text x={180} y={830} fontSize={28} fill={P.dim}>Reply…</text>
              <rect x={182} y={850} width={4} height={40} fill={P.ink} opacity={Math.sin(T*8)>0?1:0}/>
            </g>
            <g transform="translate(540 1290)" opacity={ez(EZ.out,T,h-.3,.5)}>
              <circle r={120} fill={P.white} stroke={P.ink} strokeWidth={8}/>
              {Array.from({length:12}).map((_,i)=><line key={i} x1={0} y1={-100} x2={0} y2={-112} stroke={P.ink} strokeWidth={5} transform={`rotate(${i*30})`}/>)}
              <line x1={0} y1={0} x2={0} y2={-88} stroke={P.coral} strokeWidth={9} strokeLinecap="round" transform={`rotate(${hand})`}/>
              <circle r={10} fill={P.ink}/>
              <text y={165} textAnchor="middle" fontSize={26} fill={P.coral} style={mono} opacity={seg(T,h+1,.3)}>1 hour later</text>
            </g>
            <g transform={`translate(790 1290) rotate(-8) scale(${st})`} opacity={st>.02?1:0}>
              <rect x={-130} y={-62} width={260} height={124} rx={22} fill={P.white} stroke={P.green} strokeWidth={9}/>
              <text x={-100} y={22} fontSize={78} fontWeight={900} fill={P.green}>WIN</text>
              <g transform="translate(40 -22)"><path d="M0 22L16 38L44 0" fill="none" stroke={P.green} strokeWidth={10} strokeLinecap="round" strokeLinejoin="round" {...mark}/></g>
            </g>
          </g>;})()}

        {/* rescue: not laziness, an emotional rescue mission */}
        {id==='rescue'&&(()=>{const l=an('rescue','lazy'),r=an('rescue','rescue'),k=ez(EZ.out,T,sceneStart('rescue')+.2,.6),x1=evolvePath(ez(EZ.inout,T,l+.2,.35),'M0 0L60 60M60 0L0 60'),strike=ez(EZ.inout,T,l+.1,.4),ring=spring({frame:frame-r*FPS,fps:FPS,config:{damping:11,stiffness:120}});
          return <g>
            <g transform={`translate(0 ${(1-k)*400})`} opacity={k}>
              <rect x={190} y={560} width={700} height={170} rx={32} fill={P.white} stroke={P.ink} strokeOpacity={.15} strokeWidth={3}/>
              <text x={240} y={620} fontSize={20} fill={P.dim} style={mono}>the label</text>
              <text x={240} y={690} fontSize={64} fontWeight={800} fill={P.ink} opacity={1-.45*strike}>laziness</text>
              <path d={`M232 668H${232+330*strike}`} stroke={P.coral} strokeWidth={8} strokeLinecap="round" opacity={strike>0?1:0}/>
              <g transform="translate(770 598)"><path d="M0 0L60 60M60 0L0 60" fill="none" stroke={P.coral} strokeWidth={11} strokeLinecap="round" {...x1}/></g>
            </g>
            <g transform={`translate(540 1010) scale(${ring}) rotate(${T*20})`} opacity={ring>.02?1:0}>
              <circle r={150} fill="none" stroke={P.white} strokeWidth={70}/>
              {[0,90,180,270].map(a=><path key={a} d={`M0 -185A185 185 0 0 1 130.8 -130.8`} stroke={P.coral} strokeWidth={70} fill="none" transform={`rotate(${a})`} strokeLinecap="butt"/>)}
              <circle r={186} fill="none" stroke={P.ink} strokeWidth={6}/><circle r={114} fill="none" stroke={P.ink} strokeWidth={6}/>
            </g>
          </g>;})()}

        {/* alarm: three triggers, three quick reliefs, then the researchers' summary */}
        {id==='alarm'&&(()=>{const A=(n:string)=>an('alarm',n),rs=A('researchers'),out=1-seg(T,rs-.2,.5),k=card(frame,rs+.1);
          return <g>
            <g opacity={out}>
              {['boring','scary','confusing'].map((name,i)=>{const a=ez(EZ.out,T,A(name)-.1,.5),dim=1-.45*ez(EZ.out,T,A('relief'),.4);
                return <g key={name} transform={`translate(90 ${520+i*150+(1-a)*60})`} opacity={a*dim}>
                  <rect width={900} height={124} rx={26} fill={P.white} stroke={P.ink} strokeOpacity={.12} strokeWidth={3}/>
                  <text x={34} y={42} fontSize={16} fill={P.dim} style={{...mono,letterSpacing:2}}>the task feels</text>
                  <text x={34} y={96} fontSize={48} fontWeight={800} fill={P.ink}>{name}</text>
                  <rect x={470} y={44} width={380} height={32} rx={16} fill="rgba(42,36,51,.1)"/>
                  <rect x={470} y={44} width={380*ez(EZ.out,T,A('threat'),.9)*(.55+.1*i)+(i===0?0:0)} height={32} rx={16} fill={P.coral}/>
                  <text x={470} y={106} fontSize={15} fill={P.coral} style={{...mono,letterSpacing:2}}>small threat</text>
                </g>;})}
              {['your phone','a snack','cleaning the kitchen'].map((name,i)=>{const key=['phone','snack','kitchen'][i],a=ez(EZ.out,T,A(key)-.1,.5),mark=evolvePath(ez(EZ.inout,T,A(key)+.1,.35),'M0 22L16 38L44 0');
                return <g key={name} transform={`translate(90 ${1010+i*150+(1-a)*60})`} opacity={a}>
                  <rect width={900} height={124} rx={26} fill={P.white} stroke={P.ink} strokeOpacity={.12} strokeWidth={3}/>
                  <text x={34} y={42} fontSize={16} fill={P.dim} style={{...mono,letterSpacing:2}}>fastest relief</text>
                  <text x={34} y={96} fontSize={48} fontWeight={800} fill={P.ink}>{name}</text>
                  <rect x={560} y={34} width={270} height={54} rx={27} fill={P.mintG}/><text x={584} y={69} fontSize={20} fontWeight={800} fill={P.ink} style={{...mono,letterSpacing:2}}>relief now</text>
                  <g transform="translate(776 34)"><path d="M0 22L16 38L44 0" fill="none" stroke={P.green} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" {...mark}/></g>
                </g>;})}
            </g>
            <g transform={`translate(0 ${(1-k)*2300}) rotate(${-4*(1-k)} 540 900)`}>
              <rect x={90} y={528} width={900} height={760} rx={32} fill="#c9bdf0"/><rect x={90} y={510} width={900} height={760} rx={32} fill={P.white}/>
              <text x={140} y={575} fontSize={20} fill={P.dim} style={mono}>researchers: pychyl &amp; sirois</text><path d="M140 600H940" stroke={P.ink} strokeWidth={3}/>
              <text x={136} y={760} fontSize={118} fontWeight={900} fill={P.ink} letterSpacing={-2}>MANAGING</text>
              <text x={136} y={890} fontSize={118} fontWeight={900} fill={P.coral} letterSpacing={-2}>MOOD</text>
              <text x={136} y={1000} fontSize={52} fontWeight={800} fill={P.ink}>not managing time</text>
              <Chip x={290} y={1120} w={400} label="a mood problem" color={P.mintG} a={A('mood')} T={T}/>
              <Chip x={730} y={1120} w={360} label="not a time problem" color={P.ink} a={A('mood')+.4} T={T} stroke/>
            </g>
          </g>;})()}

        {/* bias: right-now relief feels close and real, next week's reward feels far; future you gets the work */}
        {id==='bias'&&(()=>{const A=(n:string)=>an('bias',n),near=ez(EZ.out,T,A('now')-.1,.7),far=ez(EZ.out,T,A('fuzzy')-.2,.6),cd=Math.max(0,10-10*seg(T,A('real'),1.4)),np=ez(EZ.out,T,A('npc')-.1,.5);
          const boxes=[0,1,2,3,4].map(i=>{const s=A('dumps')+i*.15,q=seg(T,s,.5);return {i,q,x:330+(790-330)*q,y:880+(930-880)*q-170*Math.sin(Math.PI*q)};});
          const landed=boxes.filter(b=>b.q>=1).length;
          return <g>
            <text x={540} y={500} textAnchor="middle" fontSize={22} fill={P.coral} style={mono} opacity={ez(EZ.out,T,A('trap'),.4)}>the trap: present bias</text>
            <g opacity={near} transform={`translate(330 880) scale(${near})`}>
              <Halftone cx={0} cy={0} rx={190} ry={190} appear={1} t={0} color={P.coral}/>
              <circle r={190} fill="none" stroke={P.ink} strokeWidth={8}/>
              <text y={20} textAnchor="middle" fontSize={96} fontWeight={900} fill={P.ink}>{cd.toFixed(0)}<tspan fontSize={36}> s</tspan></text>
              <text y={270} textAnchor="middle" fontSize={22} fill={P.ink} style={mono}>relief right now</text>
            </g>
            <g opacity={far*.9}>
              <circle cx={800} cy={620} r={60*far} fill="none" stroke={P.ink} strokeWidth={5} strokeDasharray="12 14"/>
              <text x={800} y={730} textAnchor="middle" fontSize={22} fill={P.dim} style={mono}>reward next week</text>
              <text x={800} y={630} textAnchor="middle" fontSize={30} fill={P.dim} style={mono}>?</text>
            </g>
            <g transform={`translate(790 ${1120+landed*12}) scale(${np})`} opacity={np}>
              <rect x={-52} y={0} width={104} height={150} rx={30} fill={P.lilac} stroke={P.ink} strokeWidth={6}/>
              <circle cy={-34} r={42} fill={P.lilac} stroke={P.ink} strokeWidth={6}/>
              <rect x={-52} y={-130} width={104} height={40} rx={20} fill={P.ink}/><text y={-102} textAnchor="middle" fontSize={22} fontWeight={800} fill={P.white} style={mono}>NPC</text>
              <text y={200} textAnchor="middle" fontSize={22} fill={P.ink} style={mono}>future you</text>
            </g>
            {boxes.map(b=>b.q>0?<g key={b.i} transform={`translate(${b.x} ${b.q>=1?930-(b.i%3)*44:b.y})`}>
              <rect x={-34} y={-22} width={68} height={44} rx={10} fill={P.coralHi} stroke={P.ink} strokeWidth={5}/><text y={8} textAnchor="middle" fontSize={20} fontWeight={800} fill={P.ink}>task</text></g>:null)}
            <Chip x={330} y={1250} w={300} label="present bias" color={P.mintG} a={A('bias')} T={T}/>
          </g>;})()}

        {/* wiring: a larger alarm center and weaker links to action; a correlation, not a diagnosis */}
        {id==='wiring'&&(()=>{const A=(n:string)=>an('wiring',n),r=95+40*ez(EZ.out,T,A('larger'),.8),link=ez(EZ.inout,T,A('weaker'),.7),stamp=spring({frame:frame-A('corr')*FPS,fps:FPS,config:{damping:9,stiffness:140}}),ap=ez(EZ.out,T,A('wiring')-.1,.6);
          const lw=16-12*link;
          return <g opacity={ap}>
            <text x={540} y={500} textAnchor="middle" fontSize={22} fill={P.coral} style={mono}>2018 german brain-imaging study</text>
            <circle cx={290} cy={900} r={r} fill={P.coralHi} stroke={P.ink} strokeWidth={8}/>
            <text x={290} y={915} textAnchor="middle" fontSize={34} fontWeight={800} fill={P.ink}>amygdala</text>
            <text x={290} y={900+r+46} textAnchor="middle" fontSize={20} fill={P.coral} style={mono} opacity={seg(T,A('alarm'),.3)}>your alarm center</text>
            <g transform={`translate(290 ${900-r-46}) scale(${1+.08*Math.sin(T*9)})`}><circle r={34} fill={P.coral} stroke={P.ink} strokeWidth={5}/><text y={16} textAnchor="middle" fontSize={46} fontWeight={900} fill={P.white}>!</text></g>
            <rect x={680} y={800} width={250} height={200} rx={34} fill={P.mint} stroke={P.ink} strokeWidth={8}/>
            <text x={805} y={880} textAnchor="middle" fontSize={26} fontWeight={800} fill={P.ink}>turns feelings</text><text x={805} y={918} textAnchor="middle" fontSize={26} fontWeight={800} fill={P.ink}>into action</text>
            <path d={`M${290+r+14} 900H666`} stroke={P.ink} strokeWidth={lw+10} strokeLinecap="round" fill="none" opacity={.9}/>
            <path d={`M${290+r+14} 900H666`} stroke={P.coral} strokeWidth={lw} strokeLinecap="round" fill="none" strokeDasharray={link>.5?'18 16':undefined}/>
            <circle cx={290+r+14+((T*160)%(666-290-r-14))} cy={900} r={7+5*(1-link)} fill={P.white} stroke={P.ink} strokeWidth={3}/>
            <text x={480} y={850} textAnchor="middle" fontSize={20} fill={link>.5?P.coral:P.dim} style={mono}>{link>.5?'weaker link':'link'}</text>
            <g transform={`translate(540 1250) rotate(-6) scale(${stamp})`} opacity={stamp>.02?1:0}>
              <rect x={-340} y={-60} width={680} height={120} rx={20} fill={P.white} stroke={P.ink} strokeWidth={7}/>
              <text y={-6} textAnchor="middle" fontSize={44} fontWeight={900} fill={P.ink}>CORRELATION,</text><text y={40} textAnchor="middle" fontSize={44} fontWeight={900} fill={P.coral}>NOT A DIAGNOSIS</text>
            </g>
            <text x={540} y={1430} textAnchor="middle" fontSize={17} fill={P.dim} style={mono}>schematic, not a brain scan</text>
          </g>;})()}

        {/* dread: the chart, the start marker, boss fight vs side quest */}
        {id==='dread'&&(()=>{const A=(n:string)=>an('dread',n),b=ez(EZ.out,T,A('boss')-.1,.5),sq=ez(EZ.out,T,A('side')-.1,.5);
          return <g>
            <rect x={CHX0} y={CHT} width={START-CHX0} height={CHY-CHT} fill={P.zoneA} opacity={.8}/><rect x={START} y={CHT} width={CHX1-START} height={CHY-CHT} fill={P.zoneB} opacity={.9}/>
            <text x={CHX0+20} y={CHT+38} fontSize={20} fill={P.coral} style={{...mono,letterSpacing:2}}>imagining it</text>
            <text x={CHX1-20} y={CHT+38} textAnchor="end" fontSize={20} fill={P.green} style={{...mono,letterSpacing:2}}>doing it</text>
            <path d={AXES} fill="none" stroke={P.ink} strokeWidth={5} strokeLinecap="round" {...evolvePath(ez(EZ.inout,T,sceneStart('dread')+.3,.8),AXES)}/>
            <path d={`M${START} ${CHT}V${CHY}`} stroke={P.ink} strokeWidth={3} strokeDasharray="10 12" opacity={.35}/>
            <Tube d={CURVE_A} w={14} color={P.coral} light={P.coralHi} outline={P.ink} dash={curveA}/>
            {u>.5&&<Tube d={CURVE_B} w={14} color={P.green} light="#b8ecd0" outline={P.ink} dash={curveB}/>}
            {T>A('dread')&&[3,2,1].map(k=>{const uu=cursorU(T-k*.06);return <circle key={k} cx={CHX0+(CHX1-CHX0)*uu} cy={CHY-dread(uu)*CHK} r={16-k*3} fill={uu<.5?P.coral:P.green} opacity={.35-k*.07}/>;})}
            <circle cx={cx} cy={cyy} r={20} fill={u<.5?P.coral:P.green} stroke={P.ink} strokeWidth={5}/>
            <Chip x={START} y={CHY+44} w={150} label="start" color={P.ink} fg={P.white} a={A('begin')-.5} T={T}/>
            <g transform={`translate(${START-150} ${CHT-30}) scale(${b})`} opacity={b}><rect x={-110} y={-28} width={220} height={56} rx={28} fill={P.coral}/><text y={8} textAnchor="middle" fontSize={22} fontWeight={800} fill={P.white} style={{...mono,letterSpacing:2}}>boss fight</text></g>
            <g transform={`translate(${START+200} ${CHT+110}) scale(${sq})`} opacity={sq}><rect x={-110} y={-28} width={220} height={56} rx={28} fill={P.mintG}/><text y={8} textAnchor="middle" fontSize={22} fontWeight={800} fill={P.ink} style={{...mono,letterSpacing:2}}>side quest</text></g>
            <Dial x={540} y={1400} label="dread" unit="/100" value={dv} max={100} decimals={0} appear={ez(EZ.out,T,A('dread'),.5)} color={u<.5?P.coral:P.green} fg={P.ink} track="rgba(42,36,51,.15)"/>
          </g>;})()}

        {/* step: make the first step so small the alarm never fires */}
        {id==='step'&&(()=>{const A=(n:string)=>an('step',n),mins=5*seg(T,A('five'),Math.max(1,A('stop')-A('five')+.5));
          return <g>
            {['open the document','write one ugly sentence','five minutes, no cap'].map((t,i)=>{const key=['open','write','five'][i],a=ez(EZ.out,T,A(key)-.1,.5),mark=evolvePath(ez(EZ.inout,T,A(key)+.15,.35),'M0 22L16 38L44 0');
              return <g key={t} transform={`translate(90 ${560+i*160+(1-a)*60})`} opacity={a}>
                <rect width={900} height={130} rx={26} fill={P.white} stroke={P.ink} strokeOpacity={.12} strokeWidth={3}/>
                <circle cx={72} cy={65} r={34} fill={P.coral}/><text x={72} y={80} textAnchor="middle" fontSize={40} fontWeight={900} fill={P.white}>{i+1}</text>
                <text x={140} y={80} fontSize={46} fontWeight={800} fill={P.ink}>{t}</text>
                <g transform="translate(810 42)"><path d="M0 22L16 38L44 0" fill="none" stroke={P.green} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" {...mark}/></g>
              </g>;})}
            <Dial x={540} y={1250} label="timer" unit="min" value={mins} max={5} decimals={1} appear={ez(EZ.out,T,A('five'),.5)} color={P.coral} fg={P.ink} track="rgba(42,36,51,.15)"/>
            <Chip x={540} y={1470} w={600} label="you can stop after that" color={P.mintG} a={A('stop')-.1} T={T}/>
          </g>;})()}

        {/* forgive: guilt feeds the bad mood, the bad mood feeds the escape; cut the guilt and the loop loses fuel */}
        {id==='forgive'&&(()=>{const A=(n:string)=>an('forgive',n),k=ez(EZ.out,T,A('study')-.1,.6),cut=ez(EZ.inout,T,A('cut'),.5),dim=1-.7*ez(EZ.out,T,A('cut')+.4,.5),slash=evolvePath(cut,'M270 840L390 950');
          const times=[A('guilt'),A('mood'),A('escape')];
          return <g>
            <g transform={`translate(0 ${(1-k)*300})`} opacity={k}><rect x={90} y={370} width={900} height={190} rx={28} fill={P.white} stroke={P.ink} strokeOpacity={.12} strokeWidth={3}/>
              <text x={130} y={420} fontSize={18} fill={P.dim} style={mono}>one study</text>
              <text x={130} y={475} fontSize={36} fontWeight={800} fill={P.ink}>students who forgave themselves</text><text x={130} y={522} fontSize={36} fontWeight={800} fill={P.ink}>procrastinated less before the next exam</text></g>
            <g opacity={dim}>
              {ARCS.map((d,i)=>{const p=ez(EZ.inout,T,times[i]-.1,.7);return p>0?<Tube key={i} d={d} w={10} color={P.coral} light={P.coralHi} outline={P.ink} dash={evolvePath(p,d)}/>:null;})}
              {LNODES.map((n,i)=>{const [x,y]=lp(n.deg),a=ez(EZ.out,T,times[i]-.2,.5);
                return <g key={n.k} transform={`translate(${x} ${y}) scale(${a})`} opacity={a}><rect x={-120} y={-44} width={240} height={88} rx={30} fill={P.white} stroke={P.ink} strokeWidth={6}/><text y={14} textAnchor="middle" fontSize={40} fontWeight={800} fill={n.k==='guilt'?P.coral:P.ink}>{n.t}</text></g>;})}
            </g>
            <path d="M270 840L390 950" stroke={P.coral} strokeWidth={16} strokeLinecap="round" fill="none" {...slash}/>
            <Chip x={540} y={1400} w={520} label="loop loses fuel" color={P.mintG} a={A('fuel')-.1} T={T}/>
          </g>;})()}
        {/* hero: the task-mountain; shrinks and becomes a small pile once work starts */}
        <g transform={`translate(${gx} ${gy}) scale(${gs}) translate(${-CX} ${-CY})`}>
          {id==='title'&&<Halftone cx={CX} cy={CY-20} rx={330} ry={430} appear={ez(EZ.out,T,.1,1)} t={0} color={P.dot}/>}
          <path d={heroD} fill={P.coralHi} opacity={seg(T,.7,.6)}/>
          <Tube d={heroD} w={18} color={P.ink} light={P.hi} outline={P.ink} dash={heroDash}/>
          <text x={CX} y={CY+140} textAnchor="middle" fontSize={44} fontWeight={700} fill={P.ink} style={mono} opacity={seg(T,.9,.4)*(1-seg(T,2.6,.4))}>the task</text>
          <g transform={`translate(${CX} ${CY-345}) scale(${badge*(1+.08*Math.sin(T*9))})`} opacity={badge}><circle r={52} fill={P.coral} stroke={P.ink} strokeWidth={6}/><text y={22} textAnchor="middle" fontSize={68} fontWeight={900} fill={P.white}>!</text></g>
          <path d="M-55 10L-15 50L60 -40" transform={`translate(${CX} ${CY+130})`} fill="none" stroke={P.green} strokeWidth={22} strokeLinecap="round" strokeLinejoin="round" {...check}/>
        </g>
      </g>
    </svg>

    {/* kinetic headlines */}
    <Txt T={T} a={.2} b={sceneStart('email')-.3}><Glyphs text="WHY DOES YOUR BRAIN MAKE YOU" frame={frame} startS={.2} size={54} color={P.ink} y={260} ca={false}/></Txt>
    <Txt T={T} a={.9} b={sceneStart('email')-.3}><Glyphs text="PROCRASTINATE?" frame={frame} startS={.9} size={108} color={P.coral} y={1480} ca={false} wave={10}/></Txt>
    <Txt T={T} a={an('rescue','rescue')} b={sceneStart('alarm')-.3}><Glyphs text="RESCUE MISSION" frame={frame} startS={an('rescue','rescue')} size={96} color={P.coral} y={1330} ca={false} wave={8}/></Txt>
    <Txt T={T} a={an('forgive','forgive')} b={sceneStart('dodging')-.3}><Glyphs text="FORGIVE YOURSELF" frame={frame} startS={an('forgive','forgive')} size={84} color={P.green} y={230} ca={false}/></Txt>
    <Txt T={T} a={an('step','small')} b={sceneStart('forgive')-.3}><Glyphs text="START TINY" frame={frame} startS={an('step','small')} size={110} color={P.coral} y={330} ca={false} wave={8}/></Txt>
    <Txt T={T} a={an('dodging','never')} b={sceneStart('close')-.3}><Glyphs text="LAZINESS" frame={frame} startS={an('dodging','never')} size={120} color={P.dim} y={700} ca={false}/></Txt>
    {id==='dodging'&&<div style={{position:'absolute',left:540-290*ez(EZ.inout,T,an('dodging','never')+.8,.4),top:775,height:12,width:580*ez(EZ.inout,T,an('dodging','never')+.8,.4),background:P.coral,borderRadius:6}}/>}
    <Txt T={T} a={an('dodging','dodging')} b={sceneStart('close')-.3}><Glyphs text="DODGING" frame={frame} startS={an('dodging','dodging')} size={150} color={P.ink} y={940} ca={false} wave={6}/></Txt>
    <Txt T={T} a={an('dodging','dodging')+.3} b={sceneStart('close')-.3}><Glyphs text="A FEELING" frame={frame} startS={an('dodging','dodging')+.3} size={150} color={P.coral} y={1110} ca={false} wave={6}/></Txt>
    <Txt T={T} a={an('close','name')} b={tl.duration+1}><Glyphs text="NAME THE FEELING" frame={frame} startS={an('close','name')} size={78} color={P.ink} y={300} ca={false}/></Txt>
    <Txt T={T} a={an('close','step')} b={tl.duration+1}><Glyphs text="TAKE THE TINY STEP" frame={frame} startS={an('close','step')} size={78} color={P.coral} y={410} ca={false}/></Txt>
    {id==='close'&&<div style={{...mono,position:'absolute',top:1330,width:W,textAlign:'center',fontSize:30,color:P.ink,letterSpacing:3,opacity:seg(T,an('close','laundry'),.4)}}>a pile of laundry</div>}
    {id==='close'&&<div style={{...mono,position:'absolute',top:1590,width:W,textAlign:'center',fontSize:15,color:P.dim,letterSpacing:1,opacity:seg(T,an('close','step'),.6)}}>as stated in the script: pychyl &amp; sirois · 2018 german imaging study · self-forgiveness study</div>}
    {(id==='alarm'||id==='dread'||id==='bias'||id==='wiring')&&<div style={{...mono,position:'absolute',top:1620,width:W,textAlign:'center',fontSize:16,color:P.dim,letterSpacing:3}}>bars, values and diagrams are illustrative</div>}
    {/* spoken-word captions */}
    <div style={{position:'absolute',top:1690,width:W,textAlign:'center',fontSize:52,fontWeight:900,letterSpacing:-1,color:P.ink,textShadow:'0 0 0 #fff'}}>
      {cap.map((w,i)=><span key={chunk+i} style={{margin:'0 10px',color:chunk+i===wi?P.coral:P.ink,opacity:T>=w[1]-.05?1:.25}}>{w[0]}</span>)}
    </div>
  </AbsoluteFill>;
  return <AbsoluteFill style={{background:BG[0],fontFamily:'DM Sans, Arial, sans-serif'}}>
    <style>{`@font-face{font-family:'DM Sans';src:url('${staticFile('DMSans.ttf')}')}`}</style>
    <CameraMotionBlur shutterAngle={140} samples={4}>{content}</CameraMotionBlur>
  </AbsoluteFill>;
};
