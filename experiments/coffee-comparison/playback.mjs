// End-to-end playback smoke on the actual comparison artifacts. This verifies
// decoding/controls at real speed; it is not a claim of sensory editorial review.
import {chromium} from 'playwright-core';
import {pathToFileURL} from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
const folder=path.resolve(process.argv[2]);
const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROME||undefined,
 args:['--autoplay-policy=no-user-gesture-required']});
try{
 const page=await browser.newPage();const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(folder,'comparison.html')).href);
 await page.waitForFunction(()=>[...document.querySelectorAll('video')].every(v=>v.readyState>=2));
 await page.locator('#play').click();
 await page.waitForFunction(()=>document.querySelector('#a').currentTime>2);
 await page.locator('#audio').selectOption('control');
 await page.waitForFunction(()=>document.querySelector('#b').getAttribute('src').endsWith('voice-only.mp4')&&document.querySelector('#b').currentTime>2);
 await page.locator('#audio').selectOption('b');
 await page.waitForFunction(()=>document.querySelector('#b').getAttribute('src').endsWith('lemo/final.mp4')&&document.querySelector('#b').currentTime>2);
 await page.locator('#audio').selectOption('a');
 await page.locator('#restart').click();
 await page.waitForFunction(()=>[...document.querySelectorAll('video')].every(v=>v.ended),null,{timeout:180000});
 const result=await page.evaluate(()=>[...document.querySelectorAll('video')].map(v=>({
  id:v.id,duration:v.duration,currentTime:v.currentTime,ended:v.ended,error:v.error?.message||null,
  frames:v.getVideoPlaybackQuality().totalVideoFrames,dropped:v.getVideoPlaybackQuality().droppedVideoFrames})));
 if(errors.length||result.some(x=>x.error||!x.ended||x.currentTime<128))throw new Error(JSON.stringify({errors,result}));
 fs.writeFileSync(path.join(folder,'playback.json'),JSON.stringify({
  check:'Full-speed headless browser playback, controls and both audio choices; no sensory assessment',errors,result},null,2));
 console.log('Both actual films played to the end at normal speed; audio switch and restart passed.');
}finally{await browser.close()}
