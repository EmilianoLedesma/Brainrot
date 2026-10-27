// Local film shell around the actual Opus-authored chart layer and Lemo engine.
import * as E from './engine.js';
import {draw} from './scenes.js';
import {ss,clamp,lerp,hash} from '/core/lib.js';
const data=await(await fetch('./data.json')).json();
await Promise.all(['46px Newsreader','42px Caveat','30px "IBM Plex Mono"'].map(f=>document.fonts.load(f)));
const canvas=document.querySelector('canvas'),W=innerWidth,H=innerHeight;
canvas.width=W;canvas.height=H;const g=canvas.getContext('2d');
const pen=new OffscreenCanvas(1920,1080),pg=pen.getContext('2d');
const centers=data.beats.map((_,i)=>({x:(i%4)*1100,y:Math.floor(i/4)*1300}));
let boxes=[];
const zooms=[1.05,1.13,1.10,1.00,1.14,1.0,1.12,1.08,1.10,1.13,1.0,1.0,1.00,1.0,1.0,1.20];
function caption(t){
 const c=data.captions.find(s=>t>=s.start&&t<s.end);if(!c)return;
 g.setTransform(W/1080,0,0,H/1920,0,0);g.font='500 46px Newsreader';
 let lines=[],row=[];for(const w of c.words){if(row.length&&g.measureText([...row,w].map(q=>q.text).join(' ')).width>870){lines.push(row);row=[]}row.push(w)}if(row.length)lines.push(row);
 const h=lines.length*62+38,y=1830-h;g.fillStyle='rgba(246,243,236,.98)';g.fillRect(55,y-16,970,h+24);
 g.strokeStyle='#BDB4A5';g.lineWidth=1;g.beginPath();g.moveTo(75,y-9);g.lineTo(1005,y-9);g.stroke();
 lines.forEach((line,j)=>{let x=80;g.textAlign='left';g.textBaseline='alphabetic';for(const w of line){g.fillStyle=t>=w.start&&t<w.end+.05?E.P.blue:E.P.ink;g.fillText(w.text,x,y+43+j*62);x+=g.measureText(w.text+' ').width}});
}
window.DUR=data.duration;
window.EV=data.beats.flatMap((b,i)=>[{t:b.start+.2,type:'pencil'},
 {t:b.start+Math.min(1.2,(b.end-b.start)/2),type:i>=11&&i<=13?'record':'sweep',
 value:i===11?data.dataset.survey2005.n:i===12?data.dataset.samples2021[0]:i===13?data.dataset.design2026.n:undefined}]);
window.render=t=>{
 let i=data.beats.findIndex(b=>t>=b.start&&t<b.end);if(i<0)i=data.beats.length-1;
 const p=t-data.beats[i].start,len=data.beats[i].end-data.beats[i].start;
 const c=centers[i],prev=centers[Math.max(0,i-1)],f=i?ss(clamp(p/.95)):1;
 const z=lerp(i?zooms[i-1]:zooms[0],zooms[i],f)*(1+ss(clamp(p/Math.max(1,len)))*.045);
 const cx=lerp(prev.x,c.x,f),cy=lerp(prev.y,c.y,f),roll=Math.sin(t*.13)*.008;
 g.setTransform(W/1080,0,0,H/1920,0,0);g.fillStyle=E.P.paper;g.fillRect(0,0,1080,1920);boxes=[];
 g.save();g.translate(540,910);g.rotate(roll);g.scale(z,z);g.translate(-cx,-cy);
 // One world-anchored grid/paper, continuously panned rather than crossfaded.
 g.fillStyle='#e3ddcf';for(let x=Math.floor((cx-900)/45)*45;x<cx+900;x+=45)
  for(let y=Math.floor((cy-1050)/45)*45;y<cy+1050;y+=45){g.beginPath();g.arc(x,y,.85+hash(x+y)*.35,0,Math.PI*2);g.fill()}
 let penTip=null;
 for(let j=0;j<=i;j++){
  const pos=centers[j];if(Math.abs(pos.x-cx)>1250||Math.abs(pos.y-cy)>1400)continue;
  g.save();g.translate(pos.x,pos.y);
  const h={
   label:(id,text,x,y,size=38,color=E.P.ink,font='Newsreader')=>{
    // Omit optional labels that cannot remain readable through this short move.
    if(data.beats[j].end-data.beats[j].start<text.replace(/\s/g,'').length/15+2.6)return;
    g.font=`500 ${size}px "${font}"`;g.textAlign='left';g.textBaseline='alphabetic';g.fillStyle=color;g.fillText(text,x,y);
    const width=g.measureText(text).width,m=g.getTransform();
    const q=[[x-3,y-size],[x+width+3,y-size],[x+width+3,y+size*.25],[x-3,y+size*.25]].map(a=>new DOMPoint(...a).matrixTransform(m));
    boxes.push({id:j+'-'+id,text,x0:Math.min(...q.map(a=>a.x)),x1:Math.max(...q.map(a=>a.x)),y0:Math.min(...q.map(a=>a.y)),y1:Math.max(...q.map(a=>a.y))});},
   line:(pts,color=E.P.graphite,width=3,progress=1)=>E.pencilStroke(g,pts,{color,width,progress,seed:7,wobble:.4,grain:.08}),
   dot:(x,y,r,color)=>E.dataDot(g,x,y,r,color,{fresh:2,ripple:false}),
   shape:(pts,fill)=>E.inkShape(g,pts,{fill,hatch:false})
  };
  const bp=clamp(t-data.beats[j].start,0,data.beats[j].end-data.beats[j].start);
  const tip=draw(g,j,bp,data.beats[j].end-data.beats[j].start,data,h);
  if(j===i&&Array.isArray(tip)){const a=new DOMPoint(...tip).matrixTransform(g.getTransform());penTip=[a.x,a.y]}
  g.restore();
 }
 g.restore();
 if(penTip&&penTip[0]>40&&penTip[0]<W-40&&penTip[1]>200&&penTip[1]<H*.79){
  pg.setTransform(1,0,0,1,0,0);pg.clearRect(0,0,1920,1080);
  E.drawPencil(pg,{tip:[960,540],s:.63,lift:.08+Math.sin(t*3)**2*.12,flip:i>=11&&i<=14?1:0,ang:.65,blur:0});
  g.setTransform(1,0,0,1,0,0);g.drawImage(pen,penTip[0]-960,penTip[1]-540);
 }
 if(i>=1&&i<=10){
  g.setTransform(W/1080,0,0,H/1920,0,0);g.font='500 30px "IBM Plex Mono"';g.fillStyle=E.P.red;
  g.textAlign='left';g.fillText('ILLUSTRATION',80,1500);
  boxes.push({id:'illustration',text:'ILLUSTRATION',x0:80*W/1080,y0:1465*H/1920,x1:330*W/1080,y1:1510*H/1920});
 }
 caption(t);
};
window.TEXTS=()=>boxes;
window.READY=true;window.render(0);
// Local repair rendering can seek an exact frame interval without regenerating
// the entire film. Normal renders omit these query parameters.
const query=new URLSearchParams(location.search);
if(query.has('from')){
 const from=Number(query.get('from')),to=Number(query.get('to'));
 const fullRender=window.render;window.DUR=to-from;window.render=t=>fullRender(t+from);
}
