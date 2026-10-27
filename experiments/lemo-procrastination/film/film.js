// An original character film following the agent's selected style and shot plan.
// No progress bar, no persistent heading, no title/step cards.
import * as D from './drawing.js';
import {setClock,ss,clamp,lerp,hash,TAU,C} from './drawing.js';

const data=await(await fetch('./data.json')).json();
await document.fonts.load('600 48px "DM Sans"');
const canvas=document.querySelector('canvas'),W=innerWidth,H=innerHeight;
canvas.width=W;canvas.height=H;
const g=canvas.getContext('2d');
const layers=[new OffscreenCanvas(W,H),new OffscreenCanvas(W,H)];
let textBoxes=[];
const fade=(p,a,b)=>ss(clamp((p-a)/(b-a)));
const mixCam=(a,b,p)=>({x:lerp(a.x,b.x,p),y:lerp(a.y,b.y,p),k:Math.exp(lerp(Math.log(a.k),Math.log(b.k),p))});
const pose=(x,y,k)=>({x,y,k});

// Every shot is a new purposeful framing of the SAME room, rather than a slide.
const cameras=[
 [pose(430,1030,1.13),pose(550,1000,1.24)],
 [pose(600,1040,1.6),pose(820,1040,1.8)],
 [pose(600,1000,1.04),pose(620,970,1.12)],
 [pose(490,870,1.45),pose(440,850,1.8)],
 [pose(650,1030,1.08),pose(630,1000,1.18)],
 [pose(540,1000,1.0),pose(580,1040,1.14)],
 [pose(540,1110,1.65),pose(560,1090,1.9)],
 [pose(560,990,1.16),pose(790,1000,1.33)],
 [pose(510,920,1.44),pose(570,1020,.98)],
 [pose(810,1050,1.4),pose(560,1010,1.02)],
 [pose(470,1050,.94),pose(620,1020,1.26)],
 [pose(540,1110,1.45),pose(540,960,1.5)],
 [pose(430,1000,1.1),pose(540,1100,1.08)],
 [pose(560,975,1.08),pose(560,975,1.08)],
 [pose(440,820,1.8),pose(490,920,1.95)],
 [pose(540,1090,1.35),pose(560,1110,1.8)],
 [pose(670,1000,1.7),pose(555,990,1.08)],
 [pose(450,1030,.99),pose(550,1010,1.04)]
];

function overhead(index,t,p,length){
  // A genuine change of view: forearms enter from the bottom of an overhead
  // tabletop, rather than reusing the side view with a different zoom.
  D.box(35,385,1010,1120,C.task,30,230);
  D.box(57,407,966,1070,'#A6C3B5',20,231);
  D.laptop(550,1070,{scale:1.65,written:index===15?fade(p,1.4,length-1)*.24:0,
    showLabel:[5,12].includes(index),labelId:index+'-draft'});
  D.phone(905,1030,{scale:1,angle:.08});D.calendar(170,660,{scale:.93,rest:index===12});
  if(index===12){D.box(130,1170,110,108,C.white,15,234);D.line([[240,1190],[280,1222],[240,1260]],C.white,14);}
  const tap=index===15?fade(p,.7,1.5):index===6?Math.sin(p*1.1)*.4+.4:.5;
  const hx=lerp(395,510,tap),hy=lerp(1260,1125,tap)+Math.sin(t*5)*(index===15?4:0);
  // Sleeves remain attached to hands; no floating extra hands.
  D.line([[310,1650],[340,1440],[hx-10,hy+35]],C.shirt,94);
  D.hand(hx,hy,-.18,1.7,index===6?'reach':'point');
  D.line([[800,1650],[760,1430],[735,1260]],C.shirt,94);D.hand(735,1220,.15,1.55);
  if([6,15].includes(index))D.cloud(880,590,{size:.58,weight:.8,t});
  if(index===15&&p>1.45){
    const q=(p-1.45)%.7;if(q<.18){D.line([[hx-40,hy-65],[hx-64,hy-100]],C.mustardD,4);
      D.line([[hx+40,hy-65],[hx+64,hy-100]],C.mustardD,4);}
  }
}

function drawStage(ctx,index,t,p){
  const shot=data.beats[index],length=shot.end-shot.start;
  const pair=cameras[Math.min(index,cameras.length-1)];
  const fraction=fade(p,.2,Math.max(1,length-1.3));
  const camera=mixCam(pair[0],pair[1],fraction);
  const slow=Math.floor(t*12)/12;
  ctx.setTransform(W/1080,0,0,H/1920,0,0);
  ctx.fillStyle=C.paper;ctx.fillRect(0,0,1080,1920);
  ctx.save();ctx.translate(540,960);ctx.scale(camera.k,camera.k);ctx.translate(-camera.x,-camera.y);
  D.begin(ctx,camera.k);setClock(t);
  const pressure=[0,1,2,3,6,9,10,11,13,14].includes(index)?1:0;
  const relief=[4,7,8].includes(index)?1:0;
  D.room(t,camera,{pressure,relief});
  if([5,6,11,12,15].includes(index)){
    overhead(index,slow,p,length);const boxes=[...D.labels];ctx.restore();return boxes;
  }
  if(index===4){
    // Phone foreground and waiting task background, both in the same room.
    D.desk();D.laptop(370,1060,{scale:.75,showLabel:false});
    D.line([[570,1650],[620,1360],[625,1200]],C.shirt,100);
    D.phone(665,1030,{scale:2.05,angle:-.1,glow:.8});D.hand(605,1190,-.6,2.0);
    const boxes=[...D.labels];ctx.restore();return boxes;
  }
  // The calendar remains in the same place across views.
  D.calendar(1040,1005,{scale:.68,rest:index===12});
  let reach=.18,look=.3,mood=.65,tilt=0,writing=0;
  if(index===0){reach=.35+.35*Math.sin(clamp(p/2)*Math.PI);}
  if([1,2,4,7,8].includes(index)){look=.8;reach=.65;mood=.05;}
  if(index===3){reach=.25;mood=.9;}
  if(index===5){reach=.85;}
  if(index===6){reach=.5+.35*Math.sin(p*1.2);mood=.95;}
  if(index===9){reach=lerp(.3,.76,fade(p,0,2));mood=.85;}
  if(index===10){reach=.85;tilt=fade(p,0,1.5);mood=.85;}
  if(index===11){reach=.9;mood=.6;}
  if(index===12){reach=.22;mood=.05;}
  if(index===13){reach=.4;mood=.5;}
  if(index===14){reach=lerp(.3,.8,fade(p,0,2));mood=.45;}
  if(index>=15){reach=.94;writing=fade(p,index===15?1.1:0,index===15?2:.3);mood=.35;}

  // Character held on twos; camera remains smooth at output frame rate.
  const holdsPhone=[2,7,8].includes(index);
  D.actor(365,1190,{reach,look,mood,writing,lean:relief*.4,t:slow,
    frontArm:index!==1,target:holdsPhone?[210,-200]:null});
  D.desk({tilt,pile:index===9?2:0});
  const content=index>=15?clamp((index-15)*.15+fade(p,1,Math.max(2,length-1))*.23,0,.52):0;
  D.laptop(690,1100,{written:content,labelId:index+'-draft',showLabel:![1,4,6,11,15,16].includes(index)});

  const lifted=[1,2,4,7,8].includes(index);
  let phoneX=930,phoneY=1070,phoneScale=.68;
  if(index===1){phoneX=lerp(900,790,fade(p,.1,2));phoneY=lerp(1070,980,fade(p,.1,2));phoneScale=.9;}
  if([2,4,7,8].includes(index)){
    phoneX=index===7?lerp(930,600,fade(p,0,2)):600;
    phoneY=index===7?lerp(1070,945,fade(p,0,2)):945;
    phoneScale=.8;
  }
  if(index===9){phoneX=lerp(600,930,fade(p,0,2));phoneY=lerp(945,1070,fade(p,0,2));}
  D.phone(phoneX,phoneY,{scale:phoneScale,angle:lifted?-.12:.12,
    buzz:[2,6,7].includes(index)?1-fade(p,1.2,2):0,glow:[2,4,7].includes(index)?1:0});
  if(index===1){D.line([[phoneX-160,phoneY+310],[phoneX-70,phoneY+180],[phoneX-25,phoneY+80]],C.shirt,50);D.hand(phoneX-25,phoneY+45,-.8,.85);}

  // The cloud is a visual metaphor; it persists when the first action begins.
  let cloudSize=[4,7,8].includes(index)?.35:index===12?.35:1;
  if(index===8)cloudSize=lerp(.6,.22,fade(p,0,3));
  if([3,6,9,10,13,14,15,16,17].includes(index)){
    D.cloud(445,600+Math.sin(t*.5)*8,{size:index>=15?.57:cloudSize,weight:.8,t:slow});
    D.line([[435,740],[420,770]],C.worry,2);D.disk(427,751,9,C.worry);
  }

  if(index===12){
    // A cup and an open palm make deliberate rest/rescheduling concrete.
    D.box(800,1210,83,82,C.white,13,220);D.line([[883,1228],[911,1247],[883,1272]],C.white,10);
    D.hand(900,1115,.45,1.1);
  }
  if(index===13){
    // Balanced hold: no misleading brain diagrams or research charts.
    D.line([[535,760],[600,780]],C.worry,2,.7);
  }
  // Native-width detail inserts: hands and keys are drawn directly, not a
  // magnified bitmap. Their line width is compensated for the camera scale.
  if([5,6,11,15].includes(index)){
    const tapping=index===15?fade(p,.7,1.4):0;
    const hx=lerp(610,647,tapping),hy=1085+Math.sin(slow*6)*4*(index===15?1:0);
    D.hand(hx,hy,-.3,1.15,index===6?'reach':'point');
    if(index===15&&p>1.35){
      const pulse=(p-1.35)%1.1;
      if(pulse<.32){
        const r=18+pulse*110;
        D.line([[hx-r,hy-r],[hx-r-11,hy-r-19]],C.mustardD,3);
        D.line([[hx+r,hy-r],[hx+r+11,hy-r-19]],C.mustardD,3);
      }
    }
  }
  D.foreground(t,camera);
  const boxes=[...D.labels];ctx.restore();
  return boxes;
}

function caption(t){
  const cue=data.captions.find(s=>t>=s.start&&t<s.end);if(!cue)return;
  const words=cue.words;g.setTransform(W/1080,0,0,H/1920,0,0);
  g.font='600 47px "DM Sans"';const lines=[];let row=[];
  for(const w of words){
    const candidate=[...row,w].map(x=>x.text).join(' ');
    if(g.measureText(candidate).width>840&&row.length){lines.push(row);row=[];}row.push(w);
  }if(row.length)lines.push(row);
  const height=lines.length*64+46,top=1830-height;
  // Bottom spoken captions only; their panel is not a chapter/slide header.
  g.fillStyle='rgba(251,246,234,.96)';g.strokeStyle='#B7A78D';g.lineWidth=2;
  g.beginPath();g.roundRect(64,top,952,height,14);g.fill();g.stroke();
  lines.forEach((line,i)=>{
    g.font='600 47px "DM Sans"';let x=540-g.measureText(line.map(w=>w.text).join(' ')).width/2;
    g.textAlign='left';g.textBaseline='middle';
    for(const w of line){g.fillStyle=t>=w.start&&t<w.end+.06?C.accent:C.ink;g.fillText(w.text,x,top+43+i*64);x+=g.measureText(w.text+' ').width;}
  });
}

window.DUR=data.duration;
window.EV=data.events;
window.render=t=>{
  window.CURRENT_TIME=t;
  let index=data.beats.findIndex(b=>t>=b.start&&t<b.end);if(index<0)index=data.beats.length-1;
  const p=t-data.beats[index].start;
  const current=layers[1].getContext('2d');
  const currentLabels=drawStage(current,index,t,p);
  g.setTransform(1,0,0,1,0,0);
  if(index>0&&p<.65){
    const previous=layers[0].getContext('2d');
    drawStage(previous,index-1,t,data.beats[index-1].end-data.beats[index-1].start-.02);
    g.drawImage(layers[0],0,0);
    const f=ss(clamp(p/.65));g.save();g.beginPath();
    if([4,5,6,11,15].includes(index)){
      // Circular match/reveal through the phone lens, cursor or keypress.
      const cx=W*.57,cy=H*.54,r=Math.hypot(W,H)*f;g.arc(cx,cy,r,0,TAU);
    }else{
      // Printed color-plane/object wipe follows the hand's travel direction.
      const left=index%2===0?W*(1-f):0;g.rect(left,0,W*f,H);
    }
    g.clip();g.drawImage(layers[1],0,0);g.restore();textBoxes=[];
  }else{g.drawImage(layers[1],0,0);textBoxes=currentLabels;}
  caption(t);
};
window.TEXTS=()=>textBoxes;
window.READY=true;
window.render(0);
