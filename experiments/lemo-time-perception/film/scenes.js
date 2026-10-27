const INK='#2B2723',BLUE='#2F5F9E',RED='#B23A32',GREY='#8F8880';
const cl=v=>Math.max(0,Math.min(1,v)),ez=v=>v*v*(3-2*v);
const CX=c=>-330+c*110+55,RY=340,TOP=260;
const arc=(x,y,r,a0,a1,n=24)=>Array.from({length:n+1},(_,k)=>{const a=a0+(a1-a0)*k/n;return[x+r*Math.cos(a),y+r*Math.sin(a)];});
function ruler(h,k){
  h.line([[-330,RY],[330,RY]],INK,3,cl(k*2));
  for(let c=0;c<=6;c++){const x=-330+c*110;h.line([[x,TOP],[x,RY]],INK,2,cl(k*8-c-1));}
  h.line([[-330,TOP],[330,TOP]],INK,2,cl(k*2-0.6));
  return [-330+660*cl(k*2),RY];
}
function band(h,cx,w,col,pr=1,y=225){
  const x0=cx-w/2,n=Math.max(2,Math.round(w/22));
  for(let s=0;s<n;s++){const a=x0+w*s/n,b=a+w/n*0.6;h.line([[a,y],[b,y]],col,3,cl(pr*n-s));}
  h.line([[x0,y-14],[x0,y+14]],col,2,pr);h.line([[x0+w,y-14],[x0+w,y+14]],col,2,pr);
  return [x0+w*pr,y];
}
function icon(h,kind,x,y,col,pr){
  if(kind===0)h.line([[x-26,y+24],...arc(x,y+24,26,Math.PI,2*Math.PI,14),[x+26,y+24]],col,3,pr);
  else if(kind===1)h.line([[x-30,y],...arc(x,y,30,0,Math.PI,14).reverse().reverse(),[x-30,y]],col,3,pr);
  else h.line([[x-28,y+26],[x-10,y+4],[x+4,y+16],[x+28,y-24]],col,3,pr);
  return [x,y];
}
const ring=(h,x,y,pr)=>h.line(arc(x,y+6,46,-1.2,-1.2+5.4*pr),BLUE,2.5,1);
function box(h,x0,x1,pr,col=INK){h.line([[x0,-320],[x1,-320],[x1,-40],[x0,-40],[x0,-320]],col,2,pr);}
function lanes(h){h.label('lv','time as lived',-330,400,32,INK);h.label('lb','time looking back',-330,170,32,BLUE);}
function memScene(h,i,t){
  box(h,-340,-20,1);h.label('il1','ILLUSTRATION',-330,-280,32,RED);h.label('nd','not data',-330,-245,30,RED);
  let tip=[-180,-180];
  if(i>=6){const sp=i>=7?ez(cl(t*1.3)):0;
    for(let k=0;k<3;k++){const pr=i===6?cl(t*3-k):1,x=-260+k*80,y=-140;
      const xx=x+(CX(2)-150+k*150-x)*sp,yy=y+(225-50-y)*sp;
      icon(h,k,xx,yy,BLUE,pr);ring(h,xx,yy,pr);if(i===6&&pr>0&&pr<1)tip=[xx,yy];}}
  if(i>=8){box(h,20,340,1);h.label('il2','ILLUSTRATION',30,-280,32,RED);h.label('rp','repeats',30,-245,30,GREY);
    const col=i>=9?ez(cl(t*1.3)):0;
    for(let k=0;k<6;k++){const pr=i===8?cl(t*6-k):1,x=70+(k%3)*95,y=-170+Math.floor(k/3)*80;
      const xx=x+(180-x)*col,yy=y+(-130-y)*col;icon(h,k%3,xx,yy,GREY,pr);if(i===8&&pr>0&&pr<1)tip=[xx,yy];}}
  if(i===5)tip=[-180+20*Math.sin(t*6),-160];
  return tip;
}
export function draw(g,i,p,len,d,h){
  const t=cl(p/Math.max(len,0.001)),ds=d.dataset;
  if(i===0){h.label('a0','equal weeks',-330,420,32,INK);return ruler(h,t);}
  ruler(h,1);
  if(i<=10){
    if(i>=1){h.line([[CX(2)-55,TOP],[CX(2)+55,TOP],[CX(2)+55,RY],[CX(2)-55,RY],[CX(2)-55,TOP]],BLUE,3,i===1?cl(t*3):1);
      h.label('tw','TRIP WEEK',CX(2)-50,300,30,BLUE);}
    let w=i===1?110+220*ez(cl(t*1.5-0.4)):i>=7?330+(i===7?0:0):330;
    if(i>=7)w=Math.min(600,330+(i===7?ez(cl(t*1.3))*120:120));
    const bt=band(h,Math.min(CX(2),360-w/2),w,BLUE,i===1?cl(t*2-0.3):1);
    if(i===1){h.label('rc','remembered ≠ clock span',-330,110,30,INK);return t<0.6?[CX(2)+55,TOP]:bt;}
    if(i===2){for(const [x,k] of [[CX(2)-55,0],[CX(2)+55,1],[CX(4)-55,2],[CX(4)+55,3]])h.line([[x,RY+10],[x,RY+40]],RED,3,cl(t*4-k));
      h.line([[CX(2)-55,RY+30],[CX(4)+55,RY+30]],RED,1.5,cl(t*2-1));h.label('sh','same hours',CX(4)-60,450,32,RED);
      return [CX(2)-55+(t<0.5?110*cl(t*4):220+110*cl(t*4-2)),RY+40];}
    lanes(h);
    if(i===3){h.line([[-340,190],[-340+680*t,190]],BLUE,2,1);h.line([[-340,365],[-340+680*t,365]],INK,2,1);return [-340+680*t,190];}
    if(i>=4&&i!==10){h.line([[-330,180],[-80,180]],RED,3,i===4?cl(t*3):1);
      if(i===4){h.label('jd','memory judgment',-330,60,30,RED);return [-330+250*cl(t*3),180];}}
    if(i===9)band(h,CX(4),330-310*ez(cl(t*1.3)),GREY,1,205);
    if(i===10){band(h,CX(4),20,GREY,1,205);
      h.line([[-330,-270],[-120,-270]],RED,3,cl(t*3));h.line([[30,-270],[240,-270]],RED,3,cl(t*3-1));
      h.label('nm','not measured data',-330,20,32,RED);return [t<0.33?-330+630*t:240,-270];}
    return memScene(h,i,t);
  }
  if(i===11){const s=ds.survey2005,n=s.n,sh=Math.floor(n*ez(cl(t*1.4)));
    for(let k=0;k<sh;k++)h.dot(-330+(k%25)*13,-440+Math.floor(k/25)*14,4,RED);
    h.label('pn',n+' participants',-330,-120,32,RED);h.label('ag','ages '+s.min_age+'–'+s.max_age,-330,-80,30,INK);
    h.label('pm','people, not memories',-330,-40,30,INK);h.label('mv','modest share of variance',-330,60,30,GREY);
    const k=Math.max(0,sh-1);return [-330+(k%25)*13,-440+Math.floor(k/25)*14];}
  if(i===12){const v=ds.samples2021,mx=Math.max(...v);h.line([[-330,0],[330,0]],INK,2,1);
    let tip=[-330,0];v.forEach((n,k)=>{const x=-280+k*200,ht=380*n/mx*ez(cl(t*3-k));
      h.shape([[x,0],[x+120,0],[x+120,-ht],[x,-ht]],'rgba(178,58,50,0.25)');h.line([[x,0],[x,-ht],[x+120,-ht],[x+120,0]],RED,2.5,1);
      if(ht>0)h.label('s'+k,String(n),x+20,-ht-14,30,RED);if(ht>0)tip=[x+120,-ht];});
    h.label('ss','SAMPLE SIZES',-330,60,34,RED);h.label('nt','not memories',-330,100,30,INK);
    h.label('dp','no link found',60,60,30,GREY);return tip;}
  if(i===13){const z=ds.design2026;let tip=[-330,-100];
    z.groups.forEach((gname,k)=>{const x=-330+k*110,pr=cl(p*4-k*.08);
      for(let s=0;s<6;s++)h.line([[x+5,-260+s*40],[x+5,-240+s*40]],RED,2,pr);
      h.line([[x+5,-260],[x+105,-260],[x+105,-20],[x+5,-20]],RED,2,pr);
      if(pr>0){h.label('g'+k,gname,x+8,20,30,INK);tip=[x+105,-20];}});
    h.label('ds','DESIGN',-330,-300,34,RED);h.label('pg',z.per_group+' per group',-330,80,30,INK);
    h.label('np','not preregistered',-330,120,30,GREY);return tip;}
  if(i===14){for(let s=0;s<12;s++){const a=s/12;h.line(arc(0,-160,110,a*6.28,(a+0.05)*6.28,4),RED,2.5,cl(t*12-s));}
    h.label('mq','mechanism?',-90,-150,32,RED);
    h.label('at','attention',-330,-320,30,INK);h.label('em','emotion',150,-320,30,INK);h.label('tp','time pressure',-120,30,30,INK);
    return [110*Math.cos(t*6.28),-160+110*Math.sin(t*6.28)];}
  h.line([[-330,RY+20],[330,RY+20]],INK,1.5,cl(t*3));band(h,CX(3),110+50*ez(cl(t*2-1)),BLUE,1);
  const m=cl(t*2.5-1.2);h.line([[CX(3)-20,300],[CX(3),280],[CX(3)+20,300],[CX(3),318]],BLUE,4,m);
  h.line(arc(CX(3),298,34,-1.2,-1.2+5.4*cl(t*2.5-1.6)),BLUE,2.5,1);h.label('ol','one landmark',-330,440,32,BLUE);
  return [CX(3),298];
}
