// Real normal-speed media playback. Does not claim a sensory editorial watch.
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
const require=createRequire(new URL('../coffee-comparison/package.json',import.meta.url));
const {chromium}=require('playwright-core');
const folder=path.resolve(process.argv[2]);
const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROME||undefined,
 args:['--autoplay-policy=no-user-gesture-required']});
try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(folder,'watch.html')).href);
 await page.waitForFunction(()=>document.querySelector('video').readyState>=2);
 await page.evaluate(()=>document.querySelector('video').play());
 await page.waitForFunction(()=>document.querySelector('video').ended,null,{timeout:180000});
 const result=await page.evaluate(()=>{const v=document.querySelector('video');return {
  duration:v.duration,time:v.currentTime,ended:v.ended,error:v.error?.message||null,
  frames:v.getVideoPlaybackQuality().totalVideoFrames,dropped:v.getVideoPlaybackQuality().droppedVideoFrames}});
 if(errors.length||result.error||!result.ended||result.time<120)throw new Error(JSON.stringify({errors,result}));
 fs.writeFileSync(path.join(folder,'playback.json'),JSON.stringify({check:'Complete normal-speed headless playback; not sensory assessment',errors,result},null,2));
 console.log('Final film played to the end at normal speed without page or media errors.');
}finally{await browser.close()}
