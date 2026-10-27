// Original character/props, drawn using the pinned Lemo mid-century cel engine.
import {shape,ink,spline,ellipse,rrect,plane,PAL,REG,setClock,ss,clamp,lerp,hash,TAU} from './toon.js';
export {setClock,ss,clamp,lerp,hash,TAU,PAL};
export const C={...PAL,paper:'#F3E6CC',task:'#689F9A',accent:'#458F91',worry:'#948497',
  wall:'#BDD0D4',floor:'#E1CDB1',shirt:'#CB7866',phone:'#C6A14F',skin:'#DFA77D'};
export let g,camK=1,labels=[];
export function begin(ctx,k=1){g=ctx;camK=k;labels=[];REG.dx=3;REG.dy=2;REG.jit=.8;}
export function cel(points,color,seed=1,width=3.5){
  shape(g,points,{fill:color,line:width/camK,grain:.12,breaks:.13,seed});
}
export function line(points,color=C.ink,width=3,draw=1){
  ink(g,spline(points,false,6),width/camK,{color,breaks:.08,wob:.15,upto:draw,seed:4});
}
export function disk(x,y,r,color,seed=1){cel(ellipse(x,y,r,r,32),color,seed);}
export function box(x,y,w,h,color,r=8,seed=1){cel(rrect(x,y,w,h,r),color,seed);}
export function label(id,text,x,y,size=32,color=C.ink,align='center'){
  g.font=`600 ${size}px "DM Sans"`;g.fillStyle=color;g.textAlign=align;g.textBaseline='middle';g.fillText(text,x,y);
  const w=g.measureText(text).width,dx=align==='center'?w/2:align==='right'?w:0;
  const matrix=g.getTransform(),pts=[[x-dx-3,y-size*.7],[x-dx+w+3,y-size*.7],
    [x-dx+w+3,y+size*.7],[x-dx-3,y+size*.7]].map(p=>new DOMPoint(...p).matrixTransform(matrix));
  labels.push({id,text,x0:Math.min(...pts.map(p=>p.x)),y0:Math.min(...pts.map(p=>p.y)),
    x1:Math.max(...pts.map(p=>p.x)),y1:Math.max(...pts.map(p=>p.y))});
}
export function room(t,camera,{pressure=0,relief=0}={}){
  const wall=pressure>.5?'#E5CCC0':relief>.4?'#D8E4D5':C.wall;
  g.fillStyle=C.paper;g.fillRect(-3000,-3000,9000,9000);
  // Abstract, separated color planes rather than a fully rendered room.
  plane(g,[[-1400,300],[1900,180],[2200,1280],[-1500,1410]],wall,{grain:.08});
  plane(g,[[-1800,1280],[2300,1280],[2300,2700],[-1800,2700]],C.floor,{grain:.06});
  line([[-1200,1280],[150,1280],[220,1280]],'#A39782',2);
  line([[1030,1280],[1800,1280]],'#A39782',2);
  // Far-plane shapes move less than the camera, providing genuine depth cues.
  const px=camera.x*.32,py=camera.y*.16;
  g.save();g.translate(px,py);
  box(-160,480,210,330,'#EDE5CF',12);line([[-140,590],[25,590]],'#A79B83',3);
  line([[-55,500],[-55,790]],'#A79B83',3);
  disk(1030,520,75,C.paperD,3);line([[1030,520],[1030,473]],C.inkSoft,4);
  line([[1030,520],[1060,535]],C.inkSoft,3);
  g.restore();
}
export function desk({tilt=0,pile=0}={}){
  g.save();g.translate(660,1140);g.rotate(-tilt*.16);
  box(-290,-20,620,34,C.task,8,10);
  cel([[-260,15],[-235,15],[-265,250],[-295,250]],'#B58F5E',11);
  cel([[265,15],[290,15],[330,250],[301,250]],'#B58F5E',12);
  for(let i=0;i<pile;i++)box(70,-48-i*16,135,12,C.paper,2,30+i);
  g.restore();
}
export function document(x=650,y=1075,{written=0,scale=1,angle=-.04,word='DRAFT',id='draft',showLabel=true}={}){
  g.save();g.translate(x,y);g.rotate(angle);g.scale(scale,scale);
  cel([[-105,-155],[78,-155],[115,-120],[115,68],[-105,68]],C.white,20);
  cel([[78,-155],[78,-120],[115,-120]],'#DBD5C2',21,2);
  if(showLabel)label(id,word,0,-106,25,C.inkSoft);
  for(let i=0;i<4;i++){
    const p=clamp(written*4-i),row=-45+i*30;
    if(p>0)line([[-70,row],[-25,row-3],[20,row+2],[65,row-1]],C.accent,3,p);
  }
  if(written===0){const blink=Math.floor(window.CURRENT_TIME*1.8)%2===0;
    if(blink)line([[-70,-42],[-70,-12]],C.inkSoft,2);}
  g.restore();
}
export function laptop(x=680,y=1100,{written=0,scale=1,labelId='draft',showLabel=true}={}){
  g.save();g.translate(x,y);g.scale(scale,scale);
  box(-174,-294,348,260,'#DDD8C7',14,23);
  box(-155,-275,310,220,C.white,6,24);
  if(showLabel)label(labelId,'DRAFT',-119,-244,20,C.inkSoft,'left');
  for(let i=0;i<4;i++){
    const p=clamp(written*4-i);if(p>0)line([[-120,-199+i*32],[-50,-202+i*32],[20,-198+i*32],[93,-200+i*32]],C.accent,3,p);
  }
  if(written===0&&Math.floor(window.CURRENT_TIME*1.8)%2===0)line([[-119,-206],[-119,-184]],C.inkSoft,2);
  cel([[-174,-35],[174,-35],[217,45],[-215,45]],'#CECDBE',25);
  for(let row=0;row<3;row++)for(let col=0;col<10;col++)
    box(-145+col*30-row*4,-19+row*15,23,9,'#A7B3AD',2,100+row*10+col);
  box(-39,28,79,13,C.paper,3,28);g.restore();
}
export function calendar(x,y,{scale=1,rest=false}={}){
  g.save();g.translate(x,y);g.scale(scale,scale);
  box(-69,-79,138,153,C.paper,5,81);box(-69,-79,138,30,C.coralD,3,82);
  for(let row=0;row<3;row++)for(let col=0;col<4;col++)disk(-40+col*27,-20+row*28,3,C.inkSoft,84);
  line(ellipse(14,9,16,17,28),rest?C.accent:C.coralD,3);g.restore();
}
export function phone(x,y,{scale=1,angle=.06,buzz=0,glow=0,word='',id='phone'}={}){
  g.save();g.translate(x+Math.sin(window.CURRENT_TIME*65)*buzz*3,y);g.rotate(angle);g.scale(scale,scale);
  box(-50,-110,100,190,C.phone,14,31);box(-39,-90,78,133,'#E1EBDD',5,32);
  for(let i=0;i<3;i++)box(-27,-75+i*39,54,23,i%2?C.mustardL:C.blueL,5,34+i);
  disk(0,61,6,C.paper,38);
  if(word)label(id,word,0,-126,23,C.inkSoft);
  if(glow>0){for(let i=0;i<3;i++){
    const r=85+i*20+Math.sin(window.CURRENT_TIME*2+i)*7;
    line([[r,-80],[r+10,-45],[r+3,-8]],C.mustard,3,glow);
    line([[-r,-80],[-r-10,-45],[-r-3,-8]],C.mustard,3,glow);
  }}g.restore();
}
export function cloud(x,y,{size=1,weight=1,t=0}={}){
  g.save();g.translate(x,y);g.scale(size,size);
  const pts=[];for(let i=0;i<50;i++){
    const a=i/50*TAU,r=1+Math.sin(a*7+t*.4)*.11;
    pts.push([Math.cos(a)*155*r,Math.sin(a)*100*r]);}
  cel(pts,weight>.5?C.worry:'#D6B6A8',50,3);
  // No literal anatomy: a scribble represents discomfort, not a brain scan.
  for(let i=0;i<3;i++)line([[-70+i*40,-22],[-40+i*40,17],[-13+i*40,-18]],'#744D4C',3);
  g.restore();
}
function joint(a,b,L1,L2,bend=1){
  const dx=b[0]-a[0],dy=b[1]-a[1],d=Math.min(L1+L2-.1,Math.max(Math.hypot(dx,dy),Math.abs(L1-L2)+.1));
  const theta=Math.atan2(dy,dx),off=Math.acos(clamp((L1*L1+d*d-L2*L2)/(2*L1*d),-1,1))*bend;
  return[a[0]+Math.cos(theta+off)*L1,a[1]+Math.sin(theta+off)*L1];
}
export function hand(x,y,angle=0,scale=1,kind='reach'){
  g.save();g.translate(x,y);g.rotate(angle);g.scale(scale,scale);
  const pts=kind==='point'?[[-20,15],[-22,-3],[-5,-12],[9,-50],[18,-50],[15,-12],[35,-25],[42,-18],[28,3],[33,15],[20,28],[0,25]]:
   [[-22,12],[-25,-4],[-12,-15],[-7,-37],[2,-39],[8,-16],[15,-40],[24,-37],[24,-12],[35,-30],[43,-25],[36,-2],[45,3],[43,14],[25,28],[1,25]];
  cel(spline(pts,true,4),C.skin,60,3);
  line([[3,-12],[8,4]],'#A2755A',1.8);line([[20,-10],[23,3]],'#A2755A',1.8);
  g.restore();
}
export function actor(x,y,{reach=0,look=0,mood=0,writing=0,lean=0,t=0,frontArm=true,target=null}={}){
  g.save();g.translate(x,y);g.rotate(lean*.05);
  // Held body and geometric chair; shoulders stay connected to the torso.
  box(-85,-160,160,160,C.accent,28,70);
  line([[-58,0],[-77,200]],C.inkSoft,10);line([[49,0],[86,200]],C.inkSoft,10);
  cel(spline([[-67,-235],[30,-240],[78,-55],[35,13],[-58,8],[-92,-100]],true,7),C.shirt,71);
  line([[-35,10],[50,90],[20,188]],'#3C4656',36);
  line([[15,4],[100,66],[93,181]],'#3C4656',36);
  cel([[-4,178],[35,177],[64,199],[60,211],[-8,210]],C.brown,72);
  cel([[75,174],[111,176],[143,197],[139,211],[75,209]],C.brown,73);
  // Neck and original egg-head outline, nose included in the same spline.
  box(-12,-297,43,67,C.skin,7,75);
  cel(spline([[-58,-359],[-38,-410],[20,-420],[57,-394],[63,-364],[84,-351],
    [65,-338],[61,-299],[24,-282],[-29,-298]],true,7),C.skin,76);
  cel(spline([[-58,-348],[-70,-377],[-51,-414],[-8,-432],[40,-420],[63,-392],
    [30,-389],[8,-405],[-20,-376],[-25,-339]],true,7),C.hair,77);
  const blink=(t%4.9)>.0&&(t%4.9)<.13;
  if(blink)line([[24,-351],[39,-350]],C.ink,3);
  else{disk(32+look*5,-353,4.5,C.ink,78);}
  line([[19,-370-mood*7],[42,-371+mood*6]],C.ink,3);
  line([[34,-318],[46,lerp(-312,-327,mood)],[57,-318]],C.ink,2.8);
  // Far arm rests; front hand reaches with bounded two-bone IK.
  line([[-64,-218],[-89,-104],[-27,-54]],C.shirt,33);
  hand(-24,-48,.3,.65);
  const a=[37,-215],b=target||[lerp(90,190,reach)+writing*Math.sin(t*8)*5,lerp(-54,-132,reach)];
  const e=joint(a,b,112,112,1);
  if(frontArm){line([a,e,b],C.ink,31);line([a,e,b],C.shirt,24);
    hand(b[0],b[1],writing?-.65:lerp(.5,-.3,reach),.72,writing?'point':'reach');}
  if(writing)line([[b[0]+7,b[1]-30],[b[0]+35,b[1]-89]],C.mustardD,8);
  g.restore();
}
export function foreground(t,camera){
  g.save();g.translate(-camera.x*.28,-camera.y*.14);
  box(50,1430,105,100,C.coralD,10,83);
  for(let i=0;i<4;i++){
    const a=-1.2+i*.5,dx=Math.cos(a)*90,dy=Math.sin(a)*90;
    line([[100,1430],[100+dx,1360+dy]],C.avocadoD,7);
    cel(ellipse(100+dx,1360+dy,32,65,25,0,TAU,a+.5),C.avocado,85+i);
  }
  g.restore();
}
