import {copyFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const here=path.dirname(fileURLToPath(import.meta.url));
const cached=path.resolve(here,'../../out/video-use-prototype/edit');
await mkdir(path.join(here,'public'),{recursive:true});
await mkdir(path.resolve(here,'../../out/remotion-explainer/edit'),{recursive:true});
for(const name of ['narration.mp3','words.json','scene-plan.json']){
  try {await copyFile(path.join(cached,name),path.join(here,'public',name));}
  catch {throw new Error(`Missing cached ${name}. Follow README preparation instructions; no paid API fallback is used.`);}
}
await copyFile(path.join(cached,'scene-plan.json'),path.resolve(here,'../../out/remotion-explainer/edit/scene-plan.json'));
console.log('Prepared cached narration and word-aligned scene plan. No new speech was generated.');
