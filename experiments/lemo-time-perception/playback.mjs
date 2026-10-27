import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import fs from 'node:fs';import path from 'node:path';
const require=createRequire(new URL('../coffee-comparison/package.json',import.meta.url));
const {chromium}=require('playwright-core'),folder=path.resolve(process.argv[2]);
const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROME||undefined,args:['--autoplay-policy=no-user-gesture-required']});
try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(folder,'watch.html')).href);
 await page.waitForFunction(()=>document.querySelector('video').readyState>=2);
 await page.evaluate(()=>document.querySelector('video').play());
 await page.waitForFunction(()=>document.querySelector('video').ended,null,{timeout:180000});
 const result=await page.evaluate(()=>{const v=document.querySelector('video');return{duration:v.duration,time:v.currentTime,
  ended:v.ended,error:v.error?.message||null,frames:v.getVideoPlaybackQuality().totalVideoFrames,dropped:v.getVideoPlaybackQuality().droppedVideoFrames}});
 if(errors.length||result.error||!result.ended||result.time<90)throw new Error(JSON.stringify({errors,result}));
 fs.writeFileSync(path.join(folder,'playback.json'),JSON.stringify({check:'Normal-speed headless playback, not sensory assessment',errors,result},null,2));
 console.log('Final film played to the end without page/media errors.');
}finally{await browser.close()}
