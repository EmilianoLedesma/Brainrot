// Original coffee film. Projection, solids and color helpers are the pinned MIT
// Lemo Isometric Infographic engine; story/timing/audio come from Brainrot.
import {Iso, tri, PAL, shape, ss, clamp, lerp, hash, ring} from '/styles/iso-infographic/demo/engine.js';

const data = await (await fetch('./data.json')).json();
await document.fonts.load('600 60px "DM Sans"');
const canvas = document.querySelector('canvas');
const W = innerWidth, H = innerHeight;
canvas.width=W; canvas.height=H;
const g = canvas.getContext('2d');
const X=W/1080,Y=H/1920;
const C={paper:'#f4eddf',ink:'#302b27',muted:'#776f63',water:'#3d93ae',bean:'#935937',
  green:'#79975b',heat:'#ce7044',gold:'#d1a546',pore:'#3f3028',ceramic:'#faf7ef'};
let texts=[];
const iso = new Iso(g,1080,1920);
const ease=(t,a,b)=>ss(clamp((t-a)/(b-a)));
const poly=(pts,color)=>{g.fillStyle=color;g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();g.fill();};

function text(id,str,x,y,size=38,color=C.ink,align='center',weight=600,register=true){
  g.font=`${weight} ${size}px "DM Sans"`;g.textAlign=align;g.textBaseline='middle';
  g.fillStyle=color;g.fillText(str,x,y);
  if(register){const m=g.measureText(str).width, a=align==='center'?m/2:align==='right'?m:0;
    texts.push({id,text:str,x0:(x-a-2)*X,y0:(y-size*.65)*Y,x1:(x-a+m+2)*X,y1:(y+size*.65)*Y});}
}
function stroke(points,color,width=3,dash=[]){
  g.strokeStyle=color;g.lineWidth=width;g.setLineDash(dash);g.lineCap='round';
  g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.stroke();g.setLineDash([]);
}
function circle(x,y,r,color){g.fillStyle=color;g.beginPath();g.arc(x,y,r,0,Math.PI*2);g.fill();}
function arrow(x,y,dx,dy,color=C.water){
  stroke([[x,y],[x+dx,y+dy]],color,6);const a=Math.atan2(dy,dx),s=16;
  poly([[x+dx,y+dy],[x+dx-s*Math.cos(a-.5),y+dy-s*Math.sin(a-.5)],
    [x+dx-s*Math.cos(a+.5),y+dy-s*Math.sin(a+.5)]],color);
}
function badge(id,str,x,y,color=C.ink){
  g.font='600 33px "DM Sans"';const w=g.measureText(str).width+42;
  g.fillStyle='#fffaf0';g.strokeStyle='#d7cbb9';g.lineWidth=2;
  g.beginPath();g.roundRect(x-w/2,y-30,w,60,10);g.fill();g.stroke();
  text(id,str,x,y,33,color);
}
function leader(id,str,from,x,y,color=C.ink){
  stroke([from,[x,y-45],[x,y-28]],color,2.5);circle(...from,5,color);badge(id,str,x,y,color);
}
function bean(x,y,z,s=1,color=C.bean,rot=0){
  const p=[];for(let i=0;i<40;i++){const a=i/40*Math.PI*2;p.push([Math.cos(a)*1.45,Math.sin(a)*.91]);}
  iso.push(x,y,z,rot,s);
  shape(iso,p,[0,0,0],{color,depth:.44,plane:'xy'});
  iso.line3(Array.from({length:14},(_,i)=>{const f=i/13;return[-1.04+f*2.08,Math.sin(f*Math.PI*2)*.12,.47];}),'#473427',.07*iso.cam.k);
  iso.pop();
}
function cup(x,y,fill=1,scale=1,color=C.ceramic){
  iso.push(x,y,0,0,scale);
  iso.cyl(0,0,-.1,1.42,.12,tri('#ded3be'),{n:40});
  iso.cyl(0,0,.02,1.12,2.1,tri(color),{n:40});
  iso.cyl(0,0,2.12,1.13,.08,tri('#fffdf8'),{n:40});
  iso.cyl(0,0,2.20,.97,.02,tri(fill>.55?'#63412e':'#ae8960'),{n:40});
  const h=[];for(let i=0;i<24;i++){let a=-Math.PI/2+i/23*Math.PI*2;h.push([1.2+Math.cos(a)*.56,0,1.12+Math.sin(a)*.70]);}
  iso.line3(h,color,.16*iso.cam.k);iso.pop();
}
function plinth(w=8,d=7){
  // The whole platform is a background layer: depth-sorting it with separate
  // cup components would erase the body of a cup at the back of the board.
  iso.box(-w/2,-d/2,-.85,w,d,.65,tri('#e5d8bf'),{layer:0});
  iso.box(-w/2,-d/2,-.21,w,d,.15,tri('#f9f5e9'),{layer:0});
}
function steam(x,y,t){
  for(let j=0;j<3;j++){
    const pts=[];for(let i=0;i<=20;i++){const a=i/20;pts.push([x+(j-1)*40+Math.sin(a*7+t*1.2+j)*12,y-a*130]);}
    stroke(pts,'rgba(143,126,108,.32)',4);
  }
}
function grainField(x,y,z,rows=7,cols=7,size=.23,t=0){
  for(let i=0;i<rows;i++)for(let j=0;j<cols;j++){
    const h=hash(i*19+j*3);bean(x+j*.6,y+i*.6,z+Math.sin(t*2+h*8)*.025,size,C.bean,h*4);
  }
}
function route(points,t,speed=1,color=C.water,count=15){
  iso.line3(points,color,2.8,{dash:[7,9]});
  for(let i=0;i<count;i++){
    const p=(t*speed*.12+i/count)%1, at=p*(points.length-1),k=Math.floor(at),f=at-k;
    const a=points[k],b=points[Math.min(k+1,points.length-1)];
    iso.sphere(lerp(a[0],b[0],f),lerp(a[1],b[1],f),lerp(a[2],b[2],f),.075,tri(color));
  }
}
function sceneCups(t,p,kind){
  iso.cam.k=lerp(77,87,ease(p,0,.85));iso.cam.z=1.5;
  plinth(8,6);cup(-2.1,0,1);cup(2.0,0,.35);
  if(kind==='payoff'){
    grainField(-1.2,-2.2,.1,2,5,.17,t);
    route([[-1,-2,2.8],[-1,-2,.6],[0,-1.6,.3],[1,0,2.5]],t,.6,C.water,12);
  }else{bean(0,-1.6,.1,.45);}
  iso.flush();
  const a=iso.P(-2.1,0,2.3),b=iso.P(2,0,2.3);steam(a[0],a[1]-15,t);steam(b[0],b[1]-15,t+.8);
  if(p>.8){
    leader('cup-a','SAME BEANS',iso.P(-2.1,0,.7),260,1320);
    leader('cup-b',kind==='payoff'?'DIFFERENT PATHS':'DIFFERENT CUPS',iso.P(2,0,.7),780,1420);
  }
  if(kind==='payoff'){
    const r=140+Math.sin(t)*5;ring(g,540,920,r,1,t,null,{color:C.water});
  }
}
function sceneRoast(t,p){
  iso.cam.k=105;iso.cam.z=.8;plinth(6,5);
  const cooking=ease(p,1,7),clr=tri(C.green).map((a,i)=>{
    const from=a.match(/\w\w/g).map(x=>parseInt(x,16)),to=tri(C.bean)[i].match(/\w\w/g).map(x=>parseInt(x,16));
    return '#'+from.map((v,j)=>Math.round(lerp(v,to[j],cooking)).toString(16).padStart(2,'0')).join('');});
  bean(0,0,.3,1.75,clr,Math.sin(t*.15)*.04);iso.flush();
  for(let i=0;i<7;i++){
    const x=240+i*100,a=(t*.5+i*.13)%1;
    stroke([[x,1370],[x+Math.sin(t+i)*12,1320-a*110],[x,1270-a*110]],`rgba(206,112,68,${.25+a*.3})`,5);
  }
  if(p>1){badge('heat','HEAT',540,1450,C.heat);}
  if(p>3){leader('roast-aroma','AROMA COMPOUNDS',iso.P(.4,0,.8),540,530,C.heat);
    for(let i=0;i<13;i++){let a=(t*.25+i/13)%1;circle(380+i*28+Math.sin(i+t)*17,780-a*210,5+4*a,C.heat);}}
  if(p>5)badge('maillard','MAILLARD REACTIONS',540,1550);
}
function sceneParticle(t,p){
  iso.cam.k=137+ease(p,0,4)*14;iso.cam.z=1.2;plinth(4.8,4);
  bean(0,0,.2,1.6);iso.flush();
  // Schematic cutaway: the same grain opens to a porous cross-section.
  const a=ease(p,.6,2);g.save();g.translate(540,990);g.scale(a,a);
  g.fillStyle='#ab7954';g.beginPath();g.ellipse(0,0,240,310,-.2,0,Math.PI*2);g.fill();
  for(let i=0;i<38;i++){
    const q=i*2.399,r=Math.sqrt(hash(i+80))*.83;
    circle(Math.cos(q)*205*r,Math.sin(q)*270*r,13+hash(i)*12,C.pore);
  }
  for(let i=0;i<21;i++){
    let v=(t*.14+i/21)%1;
    const x=lerp(-380,380,v),y=Math.sin(i*2.1)*140;
    circle(x,y,6.5,v<.56?C.water:C.gold);
  }
  g.restore();
  if(p>1){leader('water-in','WATER IN', [320,930],230,590,C.water);
    leader('soluble-out','SOLUBLES OUT',[750,1060],770,1400,C.gold);}
}
function sceneGrind(t,p){
  iso.cam.k=92;iso.cam.z=1.1;plinth(7,6);
  const split=ease(p,1,4);
  bean(-1.7,0,.25,lerp(1.4,.9,split));
  for(let i=0;i<16;i++){
    const col=i%4,row=Math.floor(i/4),h=hash(i+30),x=lerp(1.4, .5+col*.7,split),y=lerp(0,-1.5+row*.7,split);
    bean(x,y,.25+(1-split)*2,lerp(.13,.27,split),C.bean,h*3);
  }
  iso.flush();
  if(p>1){leader('whole','LARGER PARTICLES',iso.P(-1.7,0,.7),270,620);
    leader('ground','MORE SURFACE',iso.P(1.8,0,.6),790,1430,C.heat);}
  if(p>2){arrow(340,1510,390,0,C.heat);}
}
function sceneControls(t,p){
  iso.cam.k=80;iso.cam.z=1.7;plinth(7,7);cup(0,0,1,1.55);iso.flush();
  const [x,y]=iso.P(0,0,3.5);steam(x,y,t);
  if(p>.6){
    badge('temperature','TEMPERATURE',265,570,C.heat);
    badge('contact','CONTACT TIME',810,700,C.water);
    badge('ratio','COFFEE / WATER',580,1460);
    const f=(t*.15)%1;g.strokeStyle=C.water;g.lineWidth=7;g.beginPath();g.arc(810,800,48,-Math.PI/2,-Math.PI/2+f*Math.PI*2);g.stroke();
    stroke([[810,800],[810+Math.sin(t)*33,800-Math.cos(t)*33]],C.ink,4);
  }
}
function sceneFlow(t,p,uneven){
  iso.cam.k=80;iso.cam.z=1.8;plinth(7,6);
  // Glass-sided schematic bed; grains stay in place while flow takes paths.
  iso.box(-2.7,-2.1,0,5.4,4.2,.22,tri('#6d5541'));
  for(let z=0;z<3;z++)grainField(-2.2,-1.7,.35+z*.55,6,8,.19,t);
  iso.box(-2.9,1.95,0,.12,.2,3.3,tri('#cadadd'));
  iso.box(2.7,1.95,0,.12,.2,3.3,tri('#cadadd'));
  const n=uneven?4:7;
  for(let i=0;i<n;i++){
    const x=uneven?1+i*.18:-2.1+i*.7;
    route([[x,-.9,4.5],[x,-.7,3],[x+Math.sin(i)*.15,-.4,1.4],[x,.2,-.6]],t,uneven?1.4:.8,C.water,9);
  }
  iso.flush();
  if(p>1){
    leader('flow',uneven?'EASIER ROUTE':'CONNECTED SPACES',iso.P(uneven?1.3:0,-.5,2),690,540,C.water);
    leader('bed',uneven?'LESS CONTACT':'COFFEE BED',iso.P(-1.7,.2,1),300,1450,C.bean);
  }
  if(uneven&&p>2){
    const [x,y]=iso.P(1.4,-.1,1.1);ring(g,x,y,120+Math.sin(t)*3,1,t,null,{color:C.water});
  }
}
function sceneStrength(t,p,dilute){
  iso.cam.k=80;iso.cam.z=1.7;plinth(7,6);
  if(dilute)cup(-1.8,0,1);
  else{bean(-1.7,0,.3,1.15);route([[-1.2,0,.8],[-.3,0,1.6],[1.5,0,2.5]],t,.6,C.gold,9);}
  cup(1.8,0,.3);iso.flush();
  const a=iso.P(-1.8,0,2.4),b=iso.P(1.8,0,2.4);
  if(dilute){
    for(let i=0;i<14;i++){const q=(t*.6+i/14)%1;circle(b[0]+Math.sin(i*4)*27,b[1]-260+q*240,6,C.water);}
    arrow(410,740,240,90,C.water);
  }
  if(p>1){badge('strength-a',dilute?'BEFORE':'FROM THE GROUNDS',300,555,C.bean);
    badge('strength-b',dilute?'ADD WATER':'IN THE WATER',780,1470,C.water);}
  // Qualitative particle symbols, explicitly schematic; never a numeric yield.
  for(let side=0;side<2;side++){
    const cx=side?760:300,cy=side?1260:780;
    g.strokeStyle='#c8bda8';g.lineWidth=2;g.strokeRect(cx-95,cy-80,190,160);
    for(let i=0;i<12;i++){
      const x=cx-70+(i%4)*45,y=cy-48+Math.floor(i/4)*48;
      circle(x+Math.sin(t+i)*3,y,7,C.gold);
    }
    if(dilute&&side){g.strokeStyle=C.water;g.strokeRect(cx-130,cy-105,260,210);}
  }
}

function captions(t){
  const cues=data.captions;
  const s=cues.find(c=>t>=c.start&&t<c.end);if(!s)return;
  const words=s.words;
  g.font='600 46px "DM Sans"';
  const lines=[];let current=[];
  for(const w of words){const candidate=[...current,w].map(q=>q.text).join(' ');
    if(g.measureText(candidate).width>850&&current.length){lines.push(current);current=[];}current.push(w);}
  if(current.length)lines.push(current);
  const height=lines.length*64+50,top=1835-height;
  g.fillStyle='#fffaf1';g.strokeStyle='#d5c9b5';g.lineWidth=2;
  g.beginPath();g.roundRect(60,top,960,height,18);g.fill();g.stroke();
  lines.forEach((line,j)=>{
    const total=g.measureText(line.map(w=>w.text).join(' ')).width;let x=540-total/2;
    for(const w of line){const color=t>=w.start&&t<=w.end+.08?C.water:C.ink;
      g.fillStyle=color;g.textAlign='left';g.fillText(w.text,x,top+45+j*64);
      x+=g.measureText(w.text+' ').width;}
  });
}

window.DUR=data.duration;
window.EV=data.shots.map(s=>({t:s.start+.45,type:s.kind==='roast'?'heat':s.kind==='flow'||s.kind==='dilution'?'pour':s.kind==='grind'?'grind':'accent'}));
window.render=(t)=>{
  g.setTransform(X,0,0,Y,0,0);g.clearRect(0,0,1080,1920);texts=[];
  g.fillStyle=C.paper;g.fillRect(0,0,1080,1920);
  // A fixed world grid gives continuity without introducing decorative drift.
  g.fillStyle='#ddd4c4';for(let x=45;x<1080;x+=60)for(let y=400;y<1600;y+=60)circle(x,y,1.5,'#ddd4c4');
  let idx=data.shots.findIndex(s=>t>=s.start&&t<s.end);if(idx<0)idx=data.shots.length-1;
  const shot=data.shots[idx],p=t-shot.start,len=shot.end-shot.start;
  text('series','THE SCIENCE OF COFFEE',70,95,29,C.muted,'left',600);
  stroke([[70,145],[1010,145]],'#cec3b0',2);
  text('heading-'+idx,shot.heading.toUpperCase(),540,260,54,C.ink,'center',700);
  text('schematic','SCHEMATIC · NOT TO SCALE',540,1575,22,C.muted,'center',500);
  iso.items=[];iso.seq=0;iso.T=null;iso.stack=[];iso.cam={x:0,y:0,z:1,k:80};
  const scale=shot.camera==='push'?lerp(.94,1.03,ease(p,0,len)):shot.camera==='pull'?lerp(1.04,.95,ease(p,0,len)):1;
  g.save();g.translate(540,1000);g.scale(scale,scale);g.translate(-540,-1000);
  if(shot.camera==='track')iso.cam.x=Math.sin(t*.13)*.14;
  if(shot.kind==='cups'||shot.kind==='payoff')sceneCups(t,p,shot.kind);
  else if(shot.kind==='roast')sceneRoast(t,p);
  else if(shot.kind==='particle')sceneParticle(t,p);
  else if(shot.kind==='grind')sceneGrind(t,p);
  else if(shot.kind==='controls')sceneControls(t,p);
  else if(shot.kind==='flow'||shot.kind==='uneven')sceneFlow(t,p,shot.kind==='uneven');
  else sceneStrength(t,p,shot.kind==='dilution');
  g.restore();
  // Scene labels above are transformed with the camera; correct their metadata.
  for(const b of texts){if(['series','schematic','heading-'+idx].includes(b.id))continue;
    b.x0=(540+(b.x0/X-540)*scale)*X;b.x1=(540+(b.x1/X-540)*scale)*X;
    b.y0=(1000+(b.y0/Y-1000)*scale)*Y;b.y1=(1000+(b.y1/Y-1000)*scale)*Y;
    b.id=idx+'-'+b.id;}
  captions(t);
  g.fillStyle=C.water;g.fillRect(70,1890,940*clamp(t/data.duration),4);
};
window.TEXTS=()=>texts;
window.READY=true;
window.render(0);
